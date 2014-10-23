import os

os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

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

print "Issuing first request for block (%s,%s,%s)" % (request.x,request.y,request.z)

missing = sg.fill(request, solutionGuarantorParameters, config)

if len(missing) > 0:
	raise "There are (at least) the following segments missing: " + str(missing)

