import os

os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

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

for i in range(0,4):
	for j in range(0,4):
		for k in range(0,2):

			request = ps.point3(i,j,k)

			print "Issuing first request for block (%s,%s,%s)" % (request.x,request.y,request.z)

			missing = segmentGuarantor.fill(request, segmentGuarantorParameters, config)
