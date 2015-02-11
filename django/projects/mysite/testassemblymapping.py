import sys, os
sys.path.append(os.getcwd())
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from django.conf import settings

from django.contrib.auth.models import User
from djsopnet.control.assembly import *
from djsopnet.control.assembly import \
	_generate_assemblies_for_core, \
	_map_assembly_equivalence_to_skeleton
from djsopnet.models import AssemblyEquivalence, BlockInfo, Core
from tests.testsopnet import SopnetTest

from collections import namedtuple

st = SopnetTest()
Reqfake = namedtuple('Reqfake', ['user', 'project_id'])
u = User.objects.get(username='drew')
r = Reqfake(user=u, project_id=st.project_id)

# Generate assemblies for all solved cores.
print 'Generating assemblies...'
core_ids = Core.objects.filter(stack_id=st.raw_stack_id, solution_set_flag=True).values_list('id', flat=True)
for core_id in core_ids:
	_generate_assemblies_for_core(core_id)

# Generate assembly compatibility edges for all (6-)neighboring, solved cores.
bi = BlockInfo.objects.get(stack_id=st.raw_stack_id)
for i in xrange(0, bi.num_x/bi.core_dim_x):
	for j in xrange(0, bi.num_y/bi.core_dim_y):
		for k in xrange(0, bi.num_z/bi.core_dim_z):
			c = Core.objects.get(stack_id=st.raw_stack_id,
					coordinate_x=i, coordinate_y=j, coordinate_z=k)
			if c.solution_set_flag:
				print 'Generating compatibility for core %s (%s, %s, %s)' % (c.id, i, j, k)
				for (di, dj, dk) in [(1, 0, 0), (0, 1, 0), (0, 0, 1)]:
					if i+di < bi.num_x/bi.core_dim_x and \
					   j+dj < bi.num_y/bi.core_dim_y and \
					   k+dk < bi.num_z/bi.core_dim_z:
						nbr = Core.objects.get(stack_id=st.raw_stack_id,
								coordinate_x=i+di, coordinate_y=j+dj, coordinate_z=k+dk)
						if nbr.solution_set_flag:
							generate_compatible_assemblies_between_cores(c.id, nbr.id)

# Generate assembly equivalences.
print 'Generating assembly equivalences...'
generate_assembly_equivalences(st.raw_stack_id)

# For each assembly equivalence, map to a skeleton.
equivalence_ids = AssemblyEquivalence.objects.filter(skeleton=None).values_list('id', flat=True)
for equivalence_id in equivalence_ids:
	print 'Mapping assembly equivalence %s' % equivalence_id
	try:
		_map_assembly_equivalence_to_skeleton(r, st.project_id, equivalence_id)
	except:
		print '...error'
		pass
