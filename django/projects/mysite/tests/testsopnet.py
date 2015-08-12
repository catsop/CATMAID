import os

os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

from catmaid.models import Project, ProjectStack, Stack
from catmaid.fields import Double3D, Integer3D

from django.conf import settings
from django.db import connection

import djsopnet
from djsopnet.models import SegmentationConfiguration, SegmentationStack, \
		BlockInfo, FeatureName, FeatureInfo
from djsopnet.views import _clear_djsopnet
import pysopnet as ps


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
		defaults={'image_base':'http://neurocity.janelia.org/catsop/data/catsop_test_membrane/',
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
			'component_dir', 'log_level',
			'database']
		for param_name in required_params:
			setattr(self, param_name,
				self.param('SOPNET_%s' % param_name.upper(), kwargs.get(param_name, None)))

	def log(self, msg):
		print("[Test script] %s" % msg)

	def clear_database(self, clear_slices=True, clear_segments=True, clear_solutions=True):
		if clear_slices:
			self.log("Clearing slices")
		if clear_segments:
			self.log("Clearing segments")
		if clear_solutions:
			self.log("Clearing solution")

		for ss_id in SegmentationStack.objects.filter(configuration_id=self.segmentation_configuration_id).values_list('id', flat=True):
			_clear_djsopnet(ss_id, clear_slices, clear_segments, clear_solutions)

	def setup_sopnet(self, log_level=None):
		self.log("Setting up blocks for segmentation stacks")
		BlockInfo.update_or_create(self.segmentation_configuration_id, self.stack_scale,
				self.block_width, self.block_height,
				self.block_depth, self.core_width,
				self.core_height, self.core_depth)
		ps.setLogLevel(log_level if log_level else self.log_level)

	def get_configuration(self):
		sc = SegmentationConfiguration.objects.get(pk=self.segmentation_configuration_id)
		return sc.to_pysopnet_configuration()

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
