import os

os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

from collections import namedtuple

from django.conf import settings
from django.contrib.auth.models import User
from django.db import connection

from djsopnet.control.assembly import \
	generate_assembly_equivalences, \
	generate_compatible_assemblies_between_cores, \
	_map_assembly_equivalence_to_skeleton
from djsopnet.models import SegmentationConfiguration
from djsopnet.control.block import _blockcursor_to_namedtuple
from tests.testsopnet import SopnetTest

PARALLEL_JOBS = getattr(settings, 'SOPNET_TEST_PARALLEL_JOBS', {'ASSEMBLY': False})['ASSEMBLY']

if PARALLEL_JOBS:
	from joblib import Parallel, delayed

# Threshold for number of segments an assembly equivalence must have to be
# mapped to a skeleton.
MAPPING_SEGMENTS_THRESHOLD = 20

st = SopnetTest()
sc = SegmentationConfiguration.objects.get(pk=st.segmentation_configuration_id)
segstack = sc.segmentationstack_set.get(type='Membrane')
segstack.clear_schema(delete_slices=False,
					  delete_segments=False,
					  delete_solutions=False,
					  delete_assembly_relationships=True)
bi = sc.block_info
block_size = bi.size_for_unit('block')

jobs = []

# Generate assembly compatibility edges for all (6-)neighboring, solved cores.
def core_compatibility(i, j, k):
	cursor = connection.cursor()
	cursor.execute('''
		SELECT * FROM segstack_%s.core
		WHERE coordinate_x = %s
		  AND coordinate_y = %s
		  AND coordinate_z = %s
		''' % (segstack.id, i, j, k))
	c = _blockcursor_to_namedtuple(cursor, block_size)[0]
	if c.solution_set_flag:
		print 'Generating compatibility for core %s (%s, %s, %s)' % (c.id, i, j, k)
		for (di, dj, dk) in [(1, 0, 0), (0, 1, 0), (0, 0, 1)]:
			if i+di < bi.num_x/bi.core_dim_x and \
			   j+dj < bi.num_y/bi.core_dim_y and \
			   k+dk < bi.num_z/bi.core_dim_z:
				cursor.execute('''
					SELECT * FROM segstack_%s.core
					WHERE coordinate_x = %s
					  AND coordinate_y = %s
					  AND coordinate_z = %s
					''' % (segstack.id, i+di, j+dj, k+dk))
				nbr = _blockcursor_to_namedtuple(cursor, block_size)[0]
				if nbr.solution_set_flag:
					generate_compatible_assemblies_between_cores(segstack.id, c.id, nbr.id)

for core_coord in bi.core_range():
	if PARALLEL_JOBS:
		connection.close()
		jobs.append(delayed(core_compatibility)(*core_coord))
	else:
		core_compatibility(*core_coord)

if PARALLEL_JOBS:
	Parallel(n_jobs=PARALLEL_JOBS)(jobs)


# Generate assembly equivalences.
print 'Generating assembly equivalences...'
generate_assembly_equivalences(segstack.id)


# For each assembly equivalence, map to a skeleton.
Reqfake = namedtuple('Reqfake', ['user', 'project_id'])
u = User.objects.get(username='drew')
request = Reqfake(user=u, project_id=sc.project_id)

def map_skeleton(equivalence_id):
	print 'Mapping assembly equivalence %s' % equivalence_id
	try:
		_map_assembly_equivalence_to_skeleton(request, segstack.id, equivalence_id)
	except Exception as e:
		print '...error'
		print str(e)

global_cursor = connection.cursor()
global_cursor.execute('''
		SELECT
		  e.id,
		  COUNT(aseg.segment_id)
		FROM segstack_%(segstack_id)s.assembly_equivalence e
		JOIN segstack_%(segstack_id)s.assembly a
		  ON a.equivalence_id = e.id
		JOIN segstack_%(segstack_id)s.assembly_segment aseg
		  ON aseg.assembly_id = a.id
		WHERE e.skeleton_id IS NULL
		GROUP BY e.id
		HAVING COUNT(aseg.segment_id) > %(segments_threshold)s
	''' % {'segstack_id': segstack.id, 'segments_threshold': MAPPING_SEGMENTS_THRESHOLD})
equivalence_ids = [r[0] for r in global_cursor.fetchall()]

jobs = []
for equivalence_id in equivalence_ids:
	if PARALLEL_JOBS:
		connection.close()
		jobs.append(delayed(map_skeleton)(equivalence_id))
	else:
		map_skeleton(equivalence_id)

if PARALLEL_JOBS:
	Parallel(n_jobs=PARALLEL_JOBS)(jobs)
