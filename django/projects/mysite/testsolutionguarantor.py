import os

os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

from django.conf import settings

from djsopnet.models import BlockInfo
from tests.testsopnet import SopnetTest
import pysopnet as ps

PARALLEL_JOBS = getattr(settings, 'SOPNET_TEST_PARALLEL_JOBS', {'SOLUTION': False})['SOLUTION']

if PARALLEL_JOBS:
	from joblib import Parallel, delayed

# Setup Sopnet environment
st = SopnetTest()
st.clear_database(clear_slices=False, clear_segments=False, clear_solutions=True)
st.setup_sopnet(log_level=ps.LogLevel.Debug)
st.log("Starting blockwise Sopnet")

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
		raise Exception("There are (at least) the following segments missing: " + ', '.join(map(str, missing)))

bi = BlockInfo.objects.get(configuration_id=st.segmentation_configuration_id)
for core_coord in bi.core_range():
	if PARALLEL_JOBS:
		jobs.append(delayed(fill_core)(*core_coord))
	else:
		fill_core(*core_coord)

if PARALLEL_JOBS:
	Parallel(n_jobs=PARALLEL_JOBS)(jobs)
