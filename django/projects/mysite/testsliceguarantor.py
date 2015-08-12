import os

os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

from django.conf import settings

from djsopnet.models import BlockInfo
from tests.testsopnet import SopnetTest
import pysopnet as ps

PARALLEL_JOBS = getattr(settings, 'SOPNET_TEST_PARALLEL_JOBS', {'SLICE': False})['SLICE']

if PARALLEL_JOBS:
	from joblib import Parallel, delayed

# Setup Sopnet environment
st = SopnetTest()
st.clear_database(clear_slices=True, clear_segments=False)
st.setup_sopnet(log_level=ps.LogLevel.Debug)
st.log("Starting blockwise Sopnet")

config = st.get_configuration()

sliceGuarantor = ps.SliceGuarantor()

sliceGuarantorParameters = ps.SliceGuarantorParameters()

jobs = []

def fill_block(x, y, z):
	request = ps.point3(x, y, z)

	print "Issuing first request for block (%s,%s,%s)" % (x, y, z)

	sliceGuarantor.fill(request, sliceGuarantorParameters, config)

bi = BlockInfo.objects.get(configuration_id=st.segmentation_configuration_id)
for block_coord in bi.block_range():
	if PARALLEL_JOBS:
		jobs.append(delayed(fill_block)(*block_coord))
	else:
		fill_block(*block_coord)

if PARALLEL_JOBS:
	Parallel(n_jobs=PARALLEL_JOBS)(jobs)
