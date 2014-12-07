import os

os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

from djsopnet.models import BlockInfo
from djsopnet.views import create_project_config, _clear_djsopnet
from djsopnet.views import _setup_blocks
from tests.testsopnet import SopnetTest, print_locations
import pysopnet as ps

# Setup Sopnet environment
st = SopnetTest()
st.clear_database(clear_slices=False, clear_segments=True)
st.setup_sopnet(loglevel=3)
st.log("Starting blockwise Sopnet")

config = st.get_configuration()

ps.setLogLevel(3)

segmentGuarantor = ps.SegmentGuarantor()

segmentGuarantorParameters = ps.SegmentGuarantorParameters()

bi = BlockInfo.objects.get(stack_id=st.raw_stack_id)
for i in range(0, bi.num_x):
	for j in range(0, bi.num_y):
		for k in range(0, bi.num_z):

			request = ps.point3(i,j,k)

			print "Issuing first request for block (%s,%s,%s)" % (request.x,request.y,request.z)

			missing = segmentGuarantor.fill(request, segmentGuarantorParameters, config)
