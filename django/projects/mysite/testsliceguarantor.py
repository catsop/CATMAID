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
st.clear_database(clear_slices=True, clear_segments=False)
st.setup_sopnet(loglevel=3)
st.log("Starting blockwise Sopnet")

config = st.get_configuration()

ps.setLogLevel(3)

sliceGuarantor = ps.SliceGuarantor()

sliceGuarantorParameters = ps.SliceGuarantorParameters()

jobs = []

def fill_block(x, y, z):
	request = ps.point3(x, y, z)

	print "Issuing first request for block (%s,%s,%s)" % (x, y, z)

	sliceGuarantor.fill(request, sliceGuarantorParameters, config)

bi = BlockInfo.objects.get(configuration_id=st.segmentation_configuration_id)
for i in range(0, bi.num_x):
	for j in range(0, bi.num_y):
		for k in range(0, bi.num_z):
			if USE_PARALLEL:
				jobs.append(delayed(fill_block)(i, j, k))
			else:
				fill_block(i, j, k)

if USE_PARALLEL:
	Parallel(n_jobs=8)(jobs)
