import os

os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

from django.conf import settings
from django.db import connection

from djsopnet.models import BlockInfo
from tests.testsopnet import SopnetTest
import pysopnet as ps

PARALLEL_JOBS = getattr(settings, 'SOPNET_TEST_PARALLEL_JOBS', {'GROUND TRUTH': False})['GROUND TRUTH']

if PARALLEL_JOBS:
	from joblib import Parallel, delayed

# Setup Sopnet environment
st = SopnetTest()
st.clear_database(clear_slices=True, clear_segments=True, clear_solutions=True, stack_types=['GroundTruth'])
st.setup_sopnet()
st.log("Starting blockwise Sopnet")

def vacuum_db():
    cursor = connection.cursor()
    cursor.execute('VACUUM ANALYZE;')

vacuum_db()

config = st.get_configuration()

groundTruthGuarantor = ps.GroundTruthGuarantor()

groundTruthGuarantorParameters = ps.GroundTruthGuarantorParameters()

jobs = []

def fill_core(x, y, z):
	request = ps.point3(x, y, z)

	print "Issuing first request for core (%s,%s,%s)" % (x, y, z)

	groundTruthGuarantor.fill(request, groundTruthGuarantorParameters, config)

bi = BlockInfo.objects.get(configuration_id=st.segmentation_configuration_id)
for core_coord in bi.core_range():
	if PARALLEL_JOBS:
		jobs.append(delayed(fill_block)(*core_coord))
	else:
		fill_core(*core_coord)

if PARALLEL_JOBS:
	Parallel(n_jobs=PARALLEL_JOBS)(jobs)
