import math
import os

os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

from django.conf import settings
from django.db import connection

from djsopnet.models import SegmentationConfiguration
from tests.testsopnet import SopnetTest

# PARALLEL_JOBS = getattr(settings, 'SOPNET_TEST_PARALLEL_JOBS', {'SECTION_CLEAR': False})['SECTION_CLEAR']
PARALLEL_JOBS = 8

if PARALLEL_JOBS:
	from joblib import Parallel, delayed


st = SopnetTest()
sc = SegmentationConfiguration.objects.get(pk=st.segmentation_configuration_id)
segstack = sc.segmentationstack_set.get(type='Membrane')
segstack.clear_schema(delete_slices=False,
					  delete_segments=False,
					  delete_solutions=False,
					  delete_assembly_relationships=True)
bi = sc.block_info
block_size = bi.size_for_unit('block')

MARKED_SECTIONS = frozenset([
	116, 118, 119, 120, 121, 123, 124, 127, 128, 129, 132, 134, 135, 138, 141,
	142, 143, 145, 146, 148, 149, 151, 152, 159, 160, 161, 162, 163, 164, 165,
	166, 167, 401, 405, 407, 409, 410, 412, 416, 417, 420, 423, 425, 426, 427,
	429, 430, 432, 433, 435, 438, 439, 440, 441, 444, 445, 448, 449, 451, 452,
	453, 454, 455, 456,])
	# 11, 13])

def get_block_zs_for_section(z):
	if z == 0:
		return [0]
	if (z % bi.block_dim_z) == 0:
		return [int(z / bi.block_dim_z) - 1, int(z / bi.block_dim_z)]
	return [int(math.floor(z/bi.block_dim_z))]

direct_block_z = frozenset([int(math.floor(z/block_size['z'])) for z in MARKED_SECTIONS])

indirect_block_z = direct_block_z | \
		set([z - 1 for z in direct_block_z]) | \
		set([z + 1 for z in direct_block_z])

CORE_PADDING = 1
pad_indirect_block_z = indirect_block_z | \
		set([z - CORE_PADDING for z in indirect_block_z]) | \
		set([z + CORE_PADDING for z in indirect_block_z])

indirect_core_z = frozenset([int(math.floor(z/bi.core_dim_z)) for z in pad_indirect_block_z])

jobs = []

print 'This will clear %s%% indirect blocks, %s%% direct blocks, and %s%% cores' % (
		100*len(indirect_block_z)/bi.num_z,
		100*len(direct_block_z)/bi.num_z,
		100*len(indirect_core_z)/(bi.core_extents()[2]))

response = raw_input('Type "acknowledge" to continue: ').lower()
if not response == 'acknowledge':
	quit()


# Delete solutions and assemblies for all cores in a z-index.
def clear_core_solutions(z):
	cursor = connection.cursor()
	cursor.execute('''
		SELECT id FROM segstack_%s.core
		WHERE coordinate_z = %s
		''' % (segstack.id, z))
	core_ids = [row[0] for row in cursor.fetchall()]

	cursor.execute('''
		SELECT id FROM segstack_%(segstack_id)s.solution
		WHERE core_id = ANY(ARRAY[%(core_ids)s]::integer[]);
		''' % {'segstack_id': segstack.id,
				'core_ids': ','.join(map(str, core_ids)),})
	solution_ids = [row[0] for row in cursor.fetchall()]

	cursor.execute('''
		SELECT id FROM segstack_%(segstack_id)s.assembly
		WHERE core_id = ANY(ARRAY[%(core_ids)s]::integer[]);
		''' % {'segstack_id': segstack.id,
				'core_ids': ','.join(map(str, core_ids)),})
	assembly_ids = [row[0] for row in cursor.fetchall()]

	cursor.execute('''
		BEGIN;
		SET CONSTRAINTS ALL DEFERRED;

		DELETE FROM segstack_%(segstack_id)s.solution_assembly
		WHERE solution_id = ANY(ARRAY[%(solution_ids)s]::integer[]);

		DELETE FROM segstack_%(segstack_id)s.solution_precedence
		WHERE core_id = ANY(ARRAY[%(core_ids)s]::integer[]);

		DELETE FROM segstack_%(segstack_id)s.solution
		WHERE core_id = ANY(ARRAY[%(core_ids)s]::integer[]);

		DELETE FROM segstack_%(segstack_id)s.assembly_segment
		WHERE assembly_id = ANY(ARRAY[%(assembly_ids)s]::integer[]);

		DELETE FROM segstack_%(segstack_id)s.assembly
		WHERE id = ANY(ARRAY[%(assembly_ids)s]::integer[]);

		UPDATE segstack_%(segstack_id)s.core
		SET solution_set_flag = FALSE
		WHERE id = ANY(ARRAY[%(core_ids)s]::integer[]);

		COMMIT;
		''' % {'segstack_id': segstack.id,
				'core_ids': ','.join(map(str, core_ids)),
				'solution_ids': ','.join(map(str, solution_ids)),
				'assembly_ids': ','.join(map(str, assembly_ids))})

print 'Clearing solutions...'
for core_z in indirect_core_z:
	if PARALLEL_JOBS:
		connection.close()
		jobs.append(delayed(clear_core_solutions)(core_z,))
	else:
		clear_core_solutions(core_z)

if PARALLEL_JOBS:
	Parallel(n_jobs=PARALLEL_JOBS)(jobs)

	jobs = []


# Delete segment-block-relations for all blocks in a z-index.
def clear_block_segments(z):
	cursor = connection.cursor()
	cursor.execute('''
		SELECT id FROM segstack_%s.block
		WHERE coordinate_z = %s
		''' % (segstack.id, z))
	block_ids = [row[0] for row in cursor.fetchall()]

	cursor.execute('''
		DELETE FROM segstack_%(segstack_id)s.segment_block_relation
		WHERE block_id = ANY(ARRAY[%(block_ids)s]::integer[]);

		UPDATE segstack_%(segstack_id)s.block
		SET segments_flag = FALSE
		WHERE id = ANY(ARRAY[%(block_ids)s]::integer[]);
		''' % {'segstack_id': segstack.id,
				'block_ids': ','.join(map(str, block_ids))})

print 'Clearing segment-block relationships...'
for block_z in indirect_block_z:
	if PARALLEL_JOBS:
		connection.close()
		jobs.append(delayed(clear_block_segments)(block_z,))
	else:
		clear_block_segments(block_z)

if PARALLEL_JOBS:
	Parallel(n_jobs=PARALLEL_JOBS)(jobs)

	jobs = []

# Delete any segments and related records in a z-section if not related to a block.
def clear_orphan_segments(z):
	cursor = connection.cursor()

	block_zs = get_block_zs_for_section(z)
	cursor.execute('''
		BEGIN;
		SET CONSTRAINTS ALL DEFERRED;

		CREATE TEMP TABLE orphan_segments_%(z)s ON COMMIT DROP AS
		WITH candidate_segments AS (
			SELECT DISTINCT s.id AS id FROM segstack_%(segstack_id)s.segment s
			WHERE s.section_sup = %(z)s),
		candidate_sbr AS (
			SELECT DISTINCT sbr.segment_id
			FROM segstack_%(segstack_id)s.segment_block_relation sbr,
				segstack_%(segstack_id)s.block b
			WHERE sbr.block_id = b.id AND b.coordinate_z IN (%(block_zs)s))
		SELECT cs.id AS id FROM candidate_segments cs
		WHERE NOT EXISTS (
			SELECT 1 FROM candidate_sbr sbr
			WHERE sbr.segment_id = cs.id);
		CREATE UNIQUE INDEX orphan_segments_%(z)s_idx ON orphan_segments_%(z)s (id);

		DELETE FROM segstack_%(segstack_id)s.segment_features sf
		USING orphan_segments_%(z)s os
		WHERE sf.segment_id = os.id;

		DELETE FROM segstack_%(segstack_id)s.segment_slice ss
		USING orphan_segments_%(z)s os
		WHERE ss.segment_id = os.id;

		DELETE FROM segstack_%(segstack_id)s.segment s
		USING orphan_segments_%(z)s os
		WHERE s.id = os.id;

		COMMIT;
		''' % {'segstack_id': segstack.id, 'z': z, 'block_zs': ','.join(map(str, block_zs))})

print 'Clearing orphan segments...'
indirect_section_z = set([])
for block_z in indirect_block_z:
	indirect_section_z |= set(xrange(block_z*bi.block_dim_z, (block_z + 1)*bi.block_dim_z + 1))

for section_z in indirect_section_z:
	if PARALLEL_JOBS:
		connection.close()
		jobs.append(delayed(clear_orphan_segments)(section_z,))
	else:
		clear_orphan_segments(section_z)

if PARALLEL_JOBS:
	Parallel(n_jobs=PARALLEL_JOBS)(jobs)

	jobs = []


# Delete slice-block-relations for all blocks in a z-index.
def clear_block_slices(z):
	cursor = connection.cursor()
	cursor.execute('''
		SELECT id FROM segstack_%s.block
		WHERE coordinate_z = %s
		''' % (segstack.id, z))
	block_ids = [row[0] for row in cursor.fetchall()]

	cursor.execute('''
		BEGIN;
		SET CONSTRAINTS ALL DEFERRED;

		DELETE FROM segstack_%(segstack_id)s.slice_block_relation
		WHERE block_id = ANY(ARRAY[%(block_ids)s]::integer[]);

		DELETE FROM segstack_%(segstack_id)s.block_conflict_relation
		WHERE block_id = ANY(ARRAY[%(block_ids)s]::integer[]);

		UPDATE segstack_%(segstack_id)s.block
		SET slices_flag = FALSE
		WHERE id = ANY(ARRAY[%(block_ids)s]::integer[]);

		COMMIT;
		''' % {'segstack_id': segstack.id,
				'block_ids': ','.join(map(str, block_ids))})

print 'Clearing slice-block relationships...'
for block_z in direct_block_z:
	if PARALLEL_JOBS:
		connection.close()
		jobs.append(delayed(clear_block_slices)(block_z,))
	else:
		clear_block_slices(block_z)

if PARALLEL_JOBS:
	Parallel(n_jobs=PARALLEL_JOBS)(jobs)

	jobs = []

# Delete any conflicts and related records if not related to a block.
def clear_orphan_conflicts(z):
	cursor = connection.cursor()

	block_zs = get_block_zs_for_section(z)
	cursor.execute('''
		BEGIN;
		SET CONSTRAINTS ALL DEFERRED;

		CREATE TEMP TABLE orphan_conflicts_%(z)s ON COMMIT DROP AS
		WITH candidate_conflicts AS (
			SELECT DISTINCT sc.id AS id
			FROM segstack_%(segstack_id)s.slice_conflict sc,
				segstack_%(segstack_id)s.slice s
			WHERE sc.slice_a_id = s.id AND s.section = %(z)s),
		candidate_bcr AS (
			SELECT DISTINCT bcr.slice_conflict_id
			FROM segstack_%(segstack_id)s.block_conflict_relation bcr,
				segstack_%(segstack_id)s.block b
			WHERE bcr.block_id = b.id AND b.coordinate_z IN (%(block_zs)s))
		SELECT DISTINCT cc.id AS id FROM candidate_conflicts cc
		WHERE NOT EXISTS (
			SELECT 1 FROM candidate_bcr bcr
			WHERE bcr.slice_conflict_id = cc.id);
		CREATE UNIQUE INDEX orphan_conflicts_%(z)s_idx ON orphan_conflicts_%(z)s (id);

		CREATE TEMP TABLE orphan_clique_%(z)s ON COMMIT DROP AS
		SELECT DISTINCT cce.conflict_clique_id AS id
		FROM segstack_%(segstack_id)s.conflict_clique_edge cce,
			orphan_conflicts_%(z)s oc
		WHERE cce.slice_conflict_id = oc.id;
		CREATE UNIQUE INDEX orphan_clique_%(z)s_idx ON orphan_clique_%(z)s (id);

		DELETE FROM segstack_%(segstack_id)s.conflict_clique_edge cce
		USING orphan_clique_%(z)s oc
		WHERE cce.conflict_clique_id = oc.id;

		DELETE FROM segstack_%(segstack_id)s.conflict_clique cc
		USING orphan_clique_%(z)s oc
		WHERE cc.id = oc.id;

		DELETE FROM segstack_%(segstack_id)s.slice_conflict sc
		USING orphan_conflicts_%(z)s oc
		WHERE sc.id = oc.id;

		COMMIT;
		''' % {'segstack_id': segstack.id, 'z': z, 'block_zs': ','.join(map(str, block_zs))})

print 'Clearing orphan conflicts...'
direct_section_z = set([])
for block_z in direct_block_z:
	direct_section_z |= set(xrange(block_z*bi.block_dim_z, (block_z + 1)*bi.block_dim_z + 1))

for section_z in direct_section_z:
	if PARALLEL_JOBS:
		connection.close()
		jobs.append(delayed(clear_orphan_conflicts)(section_z,))
	else:
		clear_orphan_conflicts(section_z)

if PARALLEL_JOBS:
	Parallel(n_jobs=PARALLEL_JOBS)(jobs)

	jobs = []

# Delete any slice and related records if not related to a block.
def clear_orphan_slices(z):
	cursor = connection.cursor()

	block_zs = get_block_zs_for_section(z)
	cursor.execute('''
		BEGIN;
		SET CONSTRAINTS ALL DEFERRED;

		CREATE TEMP TABLE orphan_slices_%(z)s ON COMMIT DROP AS
		WITH candidate_slices AS (
			SELECT DISTINCT s.id AS id FROM segstack_%(segstack_id)s.slice s
			WHERE s.section = %(z)s),
		candidate_sbr AS (
			SELECT DISTINCT sbr.slice_id
			FROM segstack_%(segstack_id)s.slice_block_relation sbr,
				segstack_%(segstack_id)s.block b
			WHERE sbr.block_id = b.id AND b.coordinate_z IN (%(block_zs)s))
		SELECT cs.id AS id FROM candidate_slices cs
		WHERE NOT EXISTS (
			SELECT 1 FROM candidate_sbr sbr
			WHERE sbr.slice_id = cs.id);
		CREATE UNIQUE INDEX orphan_slices_%(z)s_idx ON orphan_slices_%(z)s (id);

		DELETE FROM segstack_%(segstack_id)s.treenode_slice ts
		USING orphan_slices_%(z)s os
		WHERE ts.slice_id = os.id;

		DELETE FROM segstack_%(segstack_id)s.slice_component sc
		USING orphan_slices_%(z)s os
		WHERE sc.slice_id = os.id;

		DELETE FROM segstack_%(segstack_id)s.slice s
		USING orphan_slices_%(z)s os
		WHERE s.id = os.id;

		COMMIT;
		''' % {'segstack_id': segstack.id, 'z': z, 'block_zs': ','.join(map(str, block_zs))})

print 'Clearing orphan slices...'
for section_z in direct_section_z:
	if PARALLEL_JOBS:
		connection.close()
		jobs.append(delayed(clear_orphan_slices)(section_z,))
	else:
		clear_orphan_slices(section_z)

if PARALLEL_JOBS:
	Parallel(n_jobs=PARALLEL_JOBS)(jobs)

	jobs = []
