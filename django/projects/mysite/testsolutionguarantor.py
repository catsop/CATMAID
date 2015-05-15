import os

os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

from djsopnet.models import BlockInfo
from djsopnet.views import create_project_config, _clear_djsopnet
from djsopnet.control.block import _setup_blocks
from tests.testsopnet import SopnetTest, print_locations
import pysopnet as ps

USE_PARALLEL = False

if USE_PARALLEL:
	from joblib import Parallel, delayed

# Setup Sopnet environment
st = SopnetTest()
st.clear_database(clear_slices=False, clear_segments=False, clear_solutions=True)
st.setup_sopnet(loglevel=4)
st.log("Starting blockwise Sopnet")

ps.setLogLevel(3)

config = st.get_configuration()

solutionGuarantorParameters = ps.SolutionGuarantorParameters()
solutionGuarantorParameters.setCorePadding(1)
solutionGuarantorParameters.setForceExplanation(True)

solutionGuarantor = ps.SolutionGuarantor()

jobs = []

def fill_core(x, y, z):
	request = ps.point3(x, y, z)
	print "Issuing first request for core (%s,%s,%s)" % (x, y, z)
	missing = solutionGuarantor.fill(request, solutionGuarantorParameters, config)

	if len(missing) > 0:
		raise "There are (at least) the following segments missing: " + str(missing)

bi = BlockInfo.objects.get(configuration_id=st.segmentation_configuration_id)
for i in range(0, bi.num_x/bi.core_dim_x):
	for j in range(0, bi.num_y/bi.core_dim_y):
		for k in range(0, bi.num_z/bi.core_dim_z):
			if USE_PARALLEL:
				jobs.append(delayed(fill_core)(i, j, k))
			else:
				fill_core(i, j, k)

if USE_PARALLEL:
	Parallel(n_jobs=8)(jobs)
