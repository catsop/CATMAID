import os
import operator
import csv
import time

os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

from django.db import connection
from djsopnet.models import int_ceil, BlockInfo, SegmentationStack
from tests.testsopnet import SopnetTest
import pysopnet as ps

from joblib import Parallel, delayed

# Define how the volume will be divided, i.e., the number of blocks,
# with one worker per block.
# blockSizes = [(1, 1, 1), (1, 1, 2), (1, 1, 3), (1, 2, 2), (1, 2, 3), (2, 2, 2)]

filehandle = open('strong_scaling.csv', 'wb')
filewriter = csv.writer(filehandle, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
filewriter.writerow(['N', 'X', 'Y', 'Z', 'slices', 'segments', 'solutions'])

def vacuum_db():
    cursor = connection.cursor()
    cursor.execute('VACUUM ANALYZE;')

for blockSize in blockSizes:
    nJobs = reduce(operator.mul, blockSize, 1)
    # For "preblocked", semi-strong scaling, reset the block size.
    # blockSize = (2, 2, 2)

    # Setup Sopnet environment
    st = SopnetTest()
    rawStack = SegmentationStack.objects.get(configuration_id=st.segmentation_configuration_id, type="Raw").project_stack.stack
    st.block_width = int_ceil(rawStack.dimension.x, blockSize[0])
    st.block_height = int_ceil(rawStack.dimension.y, blockSize[1])
    st.block_depth = int_ceil(rawStack.dimension.z, blockSize[2])
    st.core_width = 1
    st.core_height = 1
    st.core_depth = 1
    st.clear_database(clear_slices=True, clear_segments=True, clear_solutions=True)
    st.setup_sopnet(log_level=ps.LogLevel.Debug)
    st.log("Starting blockwise Sopnet")

    config = st.get_configuration()

    vacuum_db()


    # Slice guarantor
    sliceGuarantor = ps.SliceGuarantor()

    sliceGuarantorParameters = ps.SliceGuarantorParameters()
    sliceGuarantorParameters.setMembraneIsBright(False)
    sliceGuarantorParameters.setMaxSliceSize(300000)

    jobs = []

    def fill_block_slices(x, y, z):
        request = ps.point3(x, y, z)

        print "Issuing first request for block (%s,%s,%s)" % (x, y, z)

        sliceGuarantor.fill(request, sliceGuarantorParameters, config)

    bi = BlockInfo.objects.get(configuration_id=st.segmentation_configuration_id)
    for i in range(0, bi.num_x):
        for j in range(0, bi.num_y):
            for k in range(0, bi.num_z):
                jobs.append(delayed(fill_block_slices)(i, j, k))

    start = time.time()
    Parallel(n_jobs=nJobs)(jobs)
    slicesElapsed = time.time() - start

    vacuum_db()

    # Segment guarantor
    segmentGuarantor = ps.SegmentGuarantor()

    segmentGuarantorParameters = ps.SegmentGuarantorParameters()

    jobs = []

    def fill_block_segments(x, y, z):
        request = ps.point3(x, y, z)

        print "Issuing first request for block (%s,%s,%s)" % (x, y, z)

        missing = segmentGuarantor.fill(request, segmentGuarantorParameters, config)

        if len(missing) > 0:
            raise "There are (at least) the following segments missing: " + str(missing)

    for i in range(0, bi.num_x):
        for j in range(0, bi.num_y):
            for k in range(0, bi.num_z):
                jobs.append(delayed(fill_block_segments)(i, j, k))

    start = time.time()
    Parallel(n_jobs=nJobs)(jobs)
    segmentsElapsed = time.time() - start

    vacuum_db()

    # Solution guarantor
    solutionGuarantorParameters = ps.SolutionGuarantorParameters()
    solutionGuarantorParameters.setCorePadding(1)
    solutionGuarantorParameters.setForceExplanation(True)
    solutionGuarantorParameters.setStoreCosts(False)

    solutionGuarantor = ps.SolutionGuarantor()

    jobs = []

    def fill_core_solutions(x, y, z):
        request = ps.point3(x, y, z)
        print "Issuing first request for core (%s,%s,%s)" % (x, y, z)
        missing = solutionGuarantor.fill(request, solutionGuarantorParameters, config)

        if len(missing) > 0:
            raise "There are (at least) the following segments missing: " + str(missing)

    for i in range(0, bi.num_x/bi.core_dim_x):
        for j in range(0, bi.num_y/bi.core_dim_y):
            for k in range(0, bi.num_z/bi.core_dim_z):
                jobs.append(delayed(fill_core_solutions)(i, j, k))

    start = time.time()
    Parallel(n_jobs=nJobs)(jobs)
    solutionsElapsed = time.time() - start

    filewriter.writerow([nJobs, blockSize[0], blockSize[1], blockSize[2], slicesElapsed, segmentsElapsed, solutionsElapsed])
    filehandle.flush()

filehandle.close()
