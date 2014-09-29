import os

os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

from catmaid.models import Project, ProjectStack, Stack
from catmaid.fields import Double3D, Integer3D

from django.conf import settings

from djsopnet.views import create_project_config, _clear_djsopnet
from djsopnet.views import _setup_blocks
import pysopnet as ps


def print_locations(locations):
	def l_to_str(l):
		return "(%s, %s, %s)" % (l.x, l.y, l.z)
	print([l_to_str(l) for l in locations])

def create_testdata():
	# Create test stack for raw data
	sr = Stack(title="Catsop Test Raw",
		image_base='http://neurocity.janelia.org/catsop/data/catsop_test_raw/',
		resolution=Double3D(4.0, 4.0, 4.0),
		dimension=Integer3D(1024, 1024, 20),
		tile_height=1024,
		tile_width=1024,
		file_extension='png')
	sr.save()

	# Create test stack for membrane data
	sm = Stack(title="Catsop Test Membrane",
		resolution=Double3D(4.0, 4.0, 4.0),
		dimension=Integer3D(1024, 1024, 20),
		image_base='http://neurocity.janelia.org/catsop/data/catsop_test_membrane/',
		tile_height=1024,
		tile_width=1024,		
		file_extension='png')
	sm.save()

	# Create new test project
	p = Project(title="Catsop Test")
	p.save()

	# Link both stacks to project
	psr = ProjectStack(project=p, stack=sr)
	psr.save()
	psm = ProjectStack(project=p, stack=sm)
	psm.save()

	print("SOPNET_PROJECT_ID = %s" % p.id)
	print("SOPNET_RAW_STACK_ID = %s" % sr.id)
	print("SOPNET_MEMBRANE_STACK_ID = %s" % m.id)

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

	def __init__(self, project_id=None, raw_stack_id=None, membrane_stack_id=None,
			block_width=None, block_height=None, block_depth=None,
			core_width=None, core_height=None, core_depth=None,
			catmaid_host=None, component_dir=None, loglevel=None):
		self.project_id = self.param("SOPNET_PROJECT_ID", project_id)
		self.membrane_stack_id = self.param("SOPNET_MEMBRANE_STACK_ID",
				membrane_stack_id)
		self.raw_stack_id = self.param("SOPNET_RAW_STACK_ID", raw_stack_id)
		self.block_width = self.param("SOPNET_BLOCK_WIDTH", block_width)
		self.block_height = self.param("SOPNET_BLOCK_HEIGHT", block_height)
		self.block_depth = self.param("SOPNET_BLOCK_DEPTH", block_depth)
		self.core_width = self.param("SOPNET_CORE_WIDTH", core_width)
		self.core_height = self.param("SOPNET_CORE_HEIGHT", core_height)
		self.core_depth = self.param("SOPNET_CORE_DEPTH", core_depth)
		self.catmaid_host = self.param("SOPNET_CATMAID_HOST", catmaid_host)
		self.component_dir = self.param("SOPNET_COMPONENT_DIR", component_dir)
		self.loglevel = self.param("SOPNET_LOGLEVEL", loglevel)

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
				_setup_blocks(s_id,
						self.block_width, self.block_height,
						self.block_depth, self.core_width,
						self.core_height, self.core_depth)
			except ValueError as e:
				print(e)
		ps.setLogLevel(self.loglevel)

	def get_configuration(self):
		conf = ps.ProjectConfiguration()
		conf.setBackendType(ps.BackendType.Django)
		conf.setCatmaidProjectId(self.project_id)
		conf.setCatmaidRawStackId(self.raw_stack_id)
		conf.setCatmaidMembraneStackId(self.membrane_stack_id)
		conf.setCatmaidHost(self.catmaid_host)
		conf.setComponentDirectory(self.component_dir)

		return conf
