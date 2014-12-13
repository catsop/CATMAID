""" The purpose of this script is to extract a surface representation from
an assembly, i.e. a set of slices (later from an assembly equivalance) for
visualization and analysis.

It retrieves slices for a given assembly and extract their contour points
to define a point cloud in 3d including correctly oriented normal vectors for
surface reconstruction. Then, a Poisson Surface Reconstruction algorithm
(Kazhdan et al. 2006) is applied to the point cloud to reconstruct a surface,
which is then stored as PLY file that can be visualized e.g. in Meshlab.

Library dependencies:
- Numpy, Pillow, Scikit-Image
"""

from PIL import Image
import skimage.morphology
import skimage.measure
import numpy as np
import subprocess

# retrieve all segments in the current solution
from django.db import connection
cursor = connection.cursor()
cursor.execute('''
SELECT
	s.id AS slice_id,
	s.section AS section,
	s.min_x AS min_x,
	s.min_y AS min_y,
	ssol.segment_id AS segment_id,
	ssol.assembly_id AS assembly_id
FROM djsopnet_segmentsolution ssol
JOIN djsopnet_solutionprecedence sp ON (sp.solution_id = ssol.solution_id)
JOIN djsopnet_segmentslice ss ON (ss.segment_id = ssol.segment_id)
JOIN djsopnet_slice s ON (s.id = ss.slice_id)
    ''')
slices = cursor.fetchall()

all_assemblies = {}
for slice in slices:
	if not slice[5] is None:
		if not slice[5] in all_assemblies:
			all_assemblies[ slice[5] ] = []
		all_assemblies[ slice[5] ].append( slice )

xres,yres,zres = 4.6,4.6,45

for assembly_id,value in all_assemblies.items():
	print 'process assembly ', assembly_id
	# for a given assembly id, retrieve all the slice information
	datapoints = []
	for slice in all_assemblies[assembly_id]:
		# load image and extract contours for slices
		img = np.array( Image.open( '/home/stephan/catsop/components/' + str(slice[0]) + '.png' ) )
		# zero out boundary pixels to find connectd contour
		img[:,0] = img[:,-1] = 0
		img[0,:] = img[-1,:] = 0

		contours = skimage.measure.find_contours(img, 0)
		contour = contours[0]

		x = contour[:,0]
		y = contour[:,1]

		for i in range(len(x)):

			if i == 0:
				j = len(x) - 1
			else:
				j = i - 1

			# add top-left coordinate to pixel-wise coordinate to define absolute coordinates
			datapoints.append( (xres*(slice[2]+x[i]), yres*(slice[3]+y[i]), zres*slice[1],
				-(y[i]-y[j])*xres, (x[i]-x[j])*yres, 0) )

	# write out to PLY file
	f = open('/home/stephan/catsop/meshes/{0}.ply'.format(assembly_id), 'w')
	header = """ply
	format ascii 1.0
	comment VCGLIB generated
	element vertex {0}
	property float x
	property float y
	property float z
	property float nx
	property float ny
	property float nz
	element face 0
	property list uchar int vertex_indices
	end_header
	""".format(len(datapoints))
	f.write(header)
	for i in range(len(datapoints)):
		f.write("{0} {1} {2} {3} {4} {5}\n".format(*datapoints[i]))
	f.close()

	subprocess.call("/home/stephan/dev/PoissonRecon/Bin/Linux/PoissonRecon --in ~/catsop/meshes/{0}.ply --out ~/catsop/meshes/{1}-mesh.ply".format(assembly_id,assembly_id), shell=True)


# do surface reconstruction using Poisson method externally
# ./PoissonRecon --in ~/catsop/tmp/test.ply --out ~/catsop/tmp/out.ply
# open in meshlab