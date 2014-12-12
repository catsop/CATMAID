import os

os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

from catmaid.models import Project, ProjectStack, Stack
from catmaid.fields import Double3D, Integer3D

from django.conf import settings

from djsopnet.models import BlockInfo, FeatureName, FeatureInfo
from djsopnet.views import create_project_config, _clear_djsopnet
from djsopnet.views import _setup_blocks
import pysopnet as ps


def print_locations(locations):
	def l_to_str(l):
		return "(%s, %s, %s)" % (l.x, l.y, l.z)
	print([l_to_str(l) for l in locations])

def create_testdata():
	# Create test stack for raw data
	sr, created = Stack.objects.get_or_create(title="Catsop Test Raw",
		defaults={'image_base':'http://neurocity.janelia.org/catsop/data/catsop_test_raw/',
			'resolution':Double3D(4.0, 4.0, 4.0),
			'dimension':Integer3D(1024, 1024, 20),
			'tile_height':1024,
			'tile_width':1024,
			'file_extension':'png'})

	# Create test stack for membrane data
	sm, created = Stack.objects.get_or_create(title="Catsop Test Membrane",
		defaults={'image_base':'http://neurocity.janelia.org/catsop/data/catsop_test_raw/',
			'resolution':Double3D(4.0, 4.0, 4.0),
			'dimension':Integer3D(1024, 1024, 20),
			'tile_height':1024,
			'tile_width':1024,
			'file_extension':'png'})

	# Create new test project
	p, created = Project.objects.get_or_create(title="Catsop Test")

	# Link both stacks to project
	psr, created = ProjectStack.objects.get_or_create(project=p, stack=sr)
	psm, created = ProjectStack.objects.get_or_create(project=p, stack=sm)

	featureWeights = \
		[0.00558637,-1.6678e-05,0.00204453,0.0711393,-0.00135737,3.35817,
		-0.000916876,-0.000957261,-0.00193582,-1.48732,-0.000234868,-4.21938,
		0.501363,0.0665533,-0.292248,0.0361189,0.0844144,-0.0316035,0.0127795,
		-0.00765338,-0.00558571,-0.0172858,0.00562492,-0.0109868,-0.00136111,
		-0.0227562,-0.0825309,-0.131062,-0.442795,0.354401,0.266398,1.46761,
		-0.743354,-0.281164,0.169887,0.262849,-0.0505789,0.00516085,0.0138543,
		-0.0102862,0.0080712,0.00012668,-0.0031432,0.00186596,0.00371999,
		-0.0688746,0.324525,0.79521,1.88847,2.09861,1.51523,0.394032,0.477188,
		-0.0952926,0.374847,0.253683,0.840265,-2.89614,4.2625e-10]
	fi, created = FeatureInfo.objects.get_or_create(stack=sr,
		defaults={'size':len(featureWeights), 'name_ids':[0], 'weights':featureWeights})
	if created:
		unnamedFeature = FeatureName(name='Unnamed Feature')
		unnamedFeature.save()
		featureNames = [unnamedFeature.id for i in range(len(featureWeights))]
		fi.name_ids = featureNames
		fi.save()

	print("SOPNET_PROJECT_ID = %s" % p.id)
	print("SOPNET_RAW_STACK_ID = %s" % sr.id)
	print("SOPNET_MEMBRANE_STACK_ID = %s" % sm.id)

class SopnetTest(object):
	def param(self, name, override):
		if override:
			return override
		elif hasattr(settings, name):
			return getattr(settings, name)
		else:
			raise ValueError("Please specify either %s in your "
					"settings or initialize SopnetTest "
					"with the appropriate parameters." % name)

	def __init__(self, **kwargs):
		required_params = ['project_id', 'raw_stack_id', 'membrane_stack_id',
			'stack_scale',
			'block_width', 'block_height', 'block_depth',
			'core_width', 'core_height', 'core_depth',
			'catmaid_host', 'component_dir', 'loglevel',
			'postgresql_database', 'postgresql_host', 'postgresql_port',
			'postgresql_user', 'postgresql_password']
		for param_name in required_params:
			setattr(self, param_name,
				self.param('SOPNET_%s' % param_name.upper(), kwargs.get(param_name, None)))

	def log(self, msg):
		print("[Test script] %s" % msg)

	def clear_database(self, clear_slices=True, clear_segments=True):
		if clear_slices and clear_segments:
			self.log("Clearing complete database")
		elif clear_slices:
			self.log("Clearing database, segments are kept")
		elif clear_segments:
			self.log("Clearing database, slices are kept")
		else:
			self.log("Clearing database, slices and segments are kept")

		for s_id in (self.raw_stack_id, self.membrane_stack_id):
			_clear_djsopnet(self.project_id, s_id,
				clear_slices, clear_segments)

	def setup_sopnet(self, loglevel=None):
		self.log("Setting up Sopnet parameters")
		for s_id in (self.raw_stack_id, self.membrane_stack_id):
			try:
				_setup_blocks(s_id, self.stack_scale,
						self.block_width, self.block_height,
						self.block_depth, self.core_width,
						self.core_height, self.core_depth)
			except ValueError as e:
				print(e)
		ps.setLogLevel(self.loglevel)

	def get_configuration(self):
		bi = BlockInfo.objects.get(stack_id=self.raw_stack_id)
		conf = ps.ProjectConfiguration()
		conf.setBackendType(ps.BackendType.PostgreSql)
		conf.setCatmaidProjectId(self.project_id)
		conf.setCatmaidRawStackId(self.raw_stack_id)
		conf.setCatmaidMembraneStackId(self.membrane_stack_id)
		conf.setCatmaidHost(self.catmaid_host)
		conf.setCatmaidStackScale(self.stack_scale)
		conf.setComponentDirectory(self.component_dir)
		conf.setBlockSize(ps.point3(self.block_width, self.block_height, self.block_depth))
		conf.setVolumeSize(ps.point3(bi.block_dim_x*bi.num_x,
				bi.block_dim_y*bi.num_y,
				bi.block_dim_z*bi.num_z))
		conf.setCoreSize(ps.point3(self.core_width, self.core_height, self.core_depth))
		conf.setPostgreSqlDatabase(self.postgresql_database)
		conf.setPostgreSqlHost(self.postgresql_host)
		conf.setPostgreSqlPort(self.postgresql_port)
		conf.setPostgreSqlUser(self.postgresql_user)
		conf.setPostgreSqlPassword(self.postgresql_password)

		return conf
