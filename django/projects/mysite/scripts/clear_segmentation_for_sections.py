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

direct_block_z = frozenset([math.floor(z/block_size['z']) for z in MARKED_SECTIONS])

indirect_block_z = direct_block_z | \
		set([z - 1 for z in direct_block_z]) | \
		set([z + 1 for z in direct_block_z])

indirect_core_z = frozenset([math.floor(z/bi.core_dim_z) for z in indirect_block_z])

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

# Delete any segments and related records if not related to a block.
def clear_orphan_segments():
	cursor = connection.cursor()
	cursor.execute('''
		SELECT s.id FROM segstack_%(segstack_id)s.segment s
		WHERE NOT EXISTS (
		  SELECT 1 FROM segstack_%(segstack_id)s.segment_block_relation sbr
		  WHERE sbr.segment_id = s.id);
		''' % {'segstack_id': segstack.id,})
	segment_ids = [row[0] for row in cursor.fetchall()]

	cursor.execute('''
		DELETE FROM segstack_%(segstack_id)s.segment_features
		WHERE segment_id = ANY(ARRAY[%(segment_ids)s]::bigint[]);

		DELETE FROM segstack_%(segstack_id)s.segment_slice
		WHERE segment_id = ANY(ARRAY[%(segment_ids)s]::bigint[]);

		DELETE FROM segstack_%(segstack_id)s.segment
		WHERE id = ANY(ARRAY[%(segment_ids)s]::bigint[]);
		''' % {'segstack_id': segstack.id,
				'segment_ids': ','.join(map(str, segment_ids))})

print 'Clearing orphan segments'
clear_orphan_segments()


# Delete slice-block-relations for all blocks in a z-index.
def clear_block_slices(z):
	cursor = connection.cursor()
	cursor.execute('''
		SELECT id FROM segstack_%s.block
		WHERE coordinate_z = %s
		''' % (segstack.id, z))
	block_ids = [row[0] for row in cursor.fetchall()]

	cursor.execute('''
		DELETE FROM segstack_%(segstack_id)s.slice_block_relation
		WHERE block_id = ANY(ARRAY[%(block_ids)s]::integer[]);

		DELETE FROM segstack_%(segstack_id)s.block_conflict_relation
		WHERE block_id = ANY(ARRAY[%(block_ids)s]::integer[]);

		UPDATE segstack_%(segstack_id)s.block
		SET slices_flag = FALSE
		WHERE id = ANY(ARRAY[%(block_ids)s]::integer[]);
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
def clear_orphan_conflicts():
	cursor = connection.cursor()
	cursor.execute('''
		SELECT sc.id FROM segstack_%(segstack_id)s.slice_conflict sc
		WHERE NOT EXISTS (
		  SELECT 1 FROM segstack_%(segstack_id)s.block_conflict_relation bcr
		  WHERE bcr.slice_conflict_id = sc.id);
		''' % {'segstack_id': segstack.id,})
	conflict_ids = [row[0] for row in cursor.fetchall()]

	cursor.execute('''
		DELETE FROM segstack_%(segstack_id)s.conflict_clique_edge
		WHERE slice_conflict_id = ANY(ARRAY[%(conflict_ids)s]::bigint[]);

		DELETE FROM segstack_%(segstack_id)s.slice_conflict
		WHERE id = ANY(ARRAY[%(conflict_ids)s]::bigint[]);
		''' % {'segstack_id': segstack.id,
				'conflict_ids': ','.join(map(str, conflict_ids))})

	cursor.execute('''
		SELECT cc.id FROM segstack_%(segstack_id)s.conflict_clique cc
		WHERE NOT EXISTS (
		  SELECT 1 FROM segstack_%(segstack_id)s.conflict_clique_edge cce
		  WHERE cce.conflict_clique_id = cc.id);
		''' % {'segstack_id': segstack.id,})
	clique_ids = [row[0] for row in cursor.fetchall()]

	cursor.execute('''
		DELETE FROM segstack_%(segstack_id)s.conflict_clique
		WHERE id = ANY(ARRAY[%(clique_ids)s]::bigint[]);
		''' % {'segstack_id': segstack.id,
				'clique_ids': ','.join(map(str, clique_ids))})

print 'Clearing orphan conflicts...'
clear_orphan_conflicts()

# Delete any slice and related records if not related to a block.
def clear_orphan_slices():
	cursor = connection.cursor()
	cursor.execute('''
		SELECT s.id FROM segstack_%(segstack_id)s.slice s
		WHERE NOT EXISTS (
		  SELECT 1 FROM segstack_%(segstack_id)s.slice_block_relation sbr
		  WHERE sbr.slice_id = s.id);
		''' % {'segstack_id': segstack.id,})
	slice_ids = [row[0] for row in cursor.fetchall()]

	cursor.execute('''
		DELETE FROM segstack_%(segstack_id)s.treenode_slice
		WHERE slice_id = ANY(ARRAY[%(slice_ids)s]::bigint[]);

		DELETE FROM segstack_%(segstack_id)s.slice_component
		WHERE slice_id = ANY(ARRAY[%(slice_ids)s]::bigint[]);

		DELETE FROM segstack_%(segstack_id)s.slice
		WHERE id = ANY(ARRAY[%(slice_ids)s]::bigint[]);
		''' % {'segstack_id': segstack.id,
				'slice_ids': ','.join(map(str, slice_ids))})

print 'Clearing orphan slices...'
clear_orphan_slices()
