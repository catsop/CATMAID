import os

os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

from django.conf import settings

from djsopnet.models import BlockInfo
from tests.testsopnet import SopnetTest
import pysopnet as ps

PARALLEL_JOBS = getattr(settings, 'SOPNET_TEST_PARALLEL_JOBS', {'SEGMENT': False})['SEGMENT']

if PARALLEL_JOBS:
	from joblib import Parallel, delayed

# Setup Sopnet environment
st = SopnetTest()
st.clear_database(clear_slices=False, clear_segments=True)
st.setup_sopnet(log_level=ps.LogLevel.Debug)
st.log("Starting blockwise Sopnet")

config = st.get_configuration()

segmentGuarantor = ps.SegmentGuarantor()

segmentGuarantorParameters = ps.SegmentGuarantorParameters()

jobs = []

def fill_block(x, y, z):
	request = ps.point3(x, y, z)

	print "Issuing first request for block (%s,%s,%s)" % (x, y, z)

	missing = segmentGuarantor.fill(request, segmentGuarantorParameters, config)

	if len(missing) > 0:
		raise Exception("There are (at least) the following slices missing: " + ', '.join(map(str, missing)))

bi = BlockInfo.objects.get(configuration_id=st.segmentation_configuration_id)
for i in range(0, bi.num_x):
	for j in range(0, bi.num_y):
		for k in range(0, bi.num_z):
			if PARALLEL_JOBS:
				jobs.append(delayed(fill_block)(i, j, k))
			else:
				fill_block(i, j, k)

if PARALLEL_JOBS:
	Parallel(n_jobs=PARALLEL_JOBS)(jobs)
