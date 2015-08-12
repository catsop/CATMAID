import sys, os
sys.path.append(os.getcwd())
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from django.conf import settings

from django.contrib.auth.models import User
from djsopnet.control.assembly import *
from djsopnet.control.assembly import \
	_map_assembly_equivalence_to_skeleton
from djsopnet.models import BlockInfo, SegmentationConfiguration, SegmentationStack
from djsopnet.control.block import _blockcursor_to_namedtuple
from tests.testsopnet import SopnetTest

from collections import namedtuple

st = SopnetTest()
Reqfake = namedtuple('Reqfake', ['user', 'project_id'])
u = User.objects.get(username='drew')
sc = SegmentationConfiguration.objects.get(pk=st.segmentation_configuration_id)
request = Reqfake(user=u, project_id=sc.project_id)
segstack = sc.segmentationstack_set.get(type='Membrane')

cursor = connection.cursor()

# Generate assembly compatibility edges for all (6-)neighboring, solved cores.
bi = sc.block_info
block_size = bi.size_for_unit('block')
for (i, j, k) in bi.core_range():
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

# Generate assembly equivalences.
print 'Generating assembly equivalences...'
generate_assembly_equivalences(segstack.id)

# For each assembly equivalence, map to a skeleton.
cursor.execute('''
	SELECT id FROM segstack_%s.assembly_equivalence WHERE skeleton_id IS NULL
	''' % segstack.id)
equivalence_ids = [r[0] for r in cursor.fetchall()]
for equivalence_id in equivalence_ids:
	print 'Mapping assembly equivalence %s' % equivalence_id
	try:
		_map_assembly_equivalence_to_skeleton(request, segstack.id, equivalence_id)
	except Exception as e:
		print '...error'
		print str(e)
