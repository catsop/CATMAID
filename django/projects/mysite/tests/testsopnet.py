import os

os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

from catmaid.models import Project, ProjectStack, Stack
from catmaid.fields import Double3D, Integer3D

from django.conf import settings
from django.db import connection

import djsopnet
from djsopnet.models import SegmentationConfiguration, SegmentationStack, \
		BlockInfo, FeatureName, FeatureInfo
from djsopnet.views import create_project_config, _clear_djsopnet
from djsopnet.control.block import _setup_blocks
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

	sc, created = SegmentationConfiguration.objects.get_or_create(project=p)
	ssr, create = SegmentationStack.objects.get_or_create(
			configuration=sc, project_stack=psr, type='Raw')
	ssm, create = SegmentationStack.objects.get_or_create(
			configuration=sc, project_stack=psm, type='Membrane')

	fo = open(os.path.join(os.path.dirname(djsopnet.__file__), 'fixtures', 'feature_weights.dat'), 'r')
	featureWeights = map(float, fo.readlines())
	fi, created = FeatureInfo.objects.get_or_create(segmentation_stack=ssm,
		defaults={'size':len(featureWeights), 'name_ids':[0], 'weights':featureWeights})
	if created:
		unnamedFeature = FeatureName(name='Unnamed Feature')
		unnamedFeature.save()
		featureNames = [unnamedFeature.id for i in range(len(featureWeights))]
		fi.name_ids = featureNames
		fi.save()

	print("SOPNET_SEGMENTATION_CONFIGURATION_ID = %s" % sc.id)

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
		required_params = ['segmentation_configuration_id',
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

		for ss_id in SegmentationStack.objects.filter(configuration_id=self.segmentation_configuration_id).values_list('id', flat=True):
			_clear_djsopnet(ss_id, clear_slices, clear_segments)

	def setup_sopnet(self, loglevel=None):
		self.log("Setting up blocks for segmentation stacks")
		for ss_id in SegmentationStack.objects.filter(configuration_id=self.segmentation_configuration_id).values_list('id', flat=True):
			try:
				_setup_blocks(ss_id, self.stack_scale,
						self.block_width, self.block_height,
						self.block_depth, self.core_width,
						self.core_height, self.core_depth)
			except ValueError as e:
				print(e)
		ps.setLogLevel(self.loglevel)

	def get_configuration(self):
		sc = SegmentationConfiguration.objects.get(pk=self.segmentation_configuration_id)
		bi = BlockInfo.objects.get(configuration=sc)
		conf = ps.ProjectConfiguration()
		conf.setBackendType(ps.BackendType.PostgreSql)
		conf.setCatmaidProjectId(sc.project_id)
		for segstack in SegmentationStack.objects.filter(configuration=sc):
			stackIds = ps.StackIds()
			stackIds.id = segstack.project_stack.stack.id
			stackIds.segmentation_id = segstack.id
			stackType = ps.StackType.Raw if segstack.type == 'Raw' else ps.StackType.Membrane
			conf.setCatmaidStackIds(stackType, stackIds)
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

	def import_weights(self, stack_type, dat_file):
		segstack = SegmentationStack.objects.get(
			configuration=self.segmentation_configuration_id, type=stack_type)
		fi = FeatureInfo.objects.get(segmentation_stack_id=segstack.id)
		fo = open(dat_file, 'r')

		weights = map(float, fo.readlines())
		if len(weights) != fi.size:
			raise ValueError('Expected %s weights but found %s.' % (fi.size, len(weights)))

		fi.weights = weights
		fi.save()

		# Clear existing cached costs for segstack
		cursor = connection.cursor()
		cursor.execute('''
			UPDATE segstack_%s.segment SET cost = NULL
			''' % segstack.id)
