import os

os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

from djsopnet.models import BlockInfo
from djsopnet.views import create_project_config, _clear_djsopnet
from djsopnet.views import _setup_blocks
from tests.testsopnet import SopnetTest, print_locations
import pysopnet as ps

# Setup Sopnet environment
st = SopnetTest()
st.setup_sopnet(loglevel=4)
st.log("Starting blockwise Sopnet")

ps.setLogLevel(3)

config = st.get_configuration()

solutionGuarantorParameters = ps.SolutionGuarantorParameters()
solutionGuarantorParameters.setCorePadding(1)

sg = ps.SolutionGuarantor()

request = ps.point3(0,0,0)

bi = BlockInfo.objects.get(stack_id=st.raw_stack_id)
for i in range(0, bi.num_x/bi.core_dim_x):
	for j in range(0, bi.num_y/bi.core_dim_y):
		for k in range(0, bi.num_z/bi.core_dim_z):
			print "Issuing first request for core (%s,%s,%s)" % (request.x,request.y,request.z)

			missing = sg.fill(request, solutionGuarantorParameters, config)

			if len(missing) > 0:
				raise "There are (at least) the following segments missing: " + str(missing)
