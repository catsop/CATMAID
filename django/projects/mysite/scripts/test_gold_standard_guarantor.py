import os

os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

from django.conf import settings
from django.db import connection

from djsopnet.models import BlockInfo
from tests.testsopnet import SopnetTest
import pysopnet as ps

PARALLEL_JOBS = getattr(settings, 'SOPNET_TEST_PARALLEL_JOBS', {'GOLD STANDARD': False})['GOLD STANDARD']

if PARALLEL_JOBS:
	from joblib import Parallel, delayed

# Setup Sopnet environment
st = SopnetTest()
st.setup_sopnet()
st.log("Starting blockwise Sopnet")

def vacuum_db():
    cursor = connection.cursor()
    cursor.execute('VACUUM ANALYZE;')

vacuum_db()

config = st.get_configuration()

goldStandardGuarantor = ps.GoldStandardGuarantor()

goldStandardGuarantorParameters = ps.GoldStandardGuarantorParameters()

jobs = []

def fill_core(x, y, z):
	request = ps.point3(x, y, z)

	print "Issuing first request for core (%s,%s,%s)" % (x, y, z)

	goldStandardGuarantor.fill(request, goldStandardGuarantorParameters, config)

bi = BlockInfo.objects.get(configuration_id=st.segmentation_configuration_id)
for core_coord in bi.core_range():
	if PARALLEL_JOBS:
		jobs.append(delayed(fill_core)(*core_coord))
	else:
		fill_core(*core_coord)

if PARALLEL_JOBS:
	Parallel(n_jobs=PARALLEL_JOBS)(jobs)
