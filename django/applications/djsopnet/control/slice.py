from djsopnet.models import *

def retrieve_slices_for_skeleton(request, skeleton_id = None):
	"""To visualize the slices found for a given skeleton, for which UserConstraints and solutions were generated,
	we retrieve all segments with their solution flag, and retrieve all associated slices, and mark the
	selected slices that are in the solution.

	In addition, special locations are found and returned where SOPNET has potentially found a solution segment
	that needs review:
	- Leaf nodes of connected components, e.g. at skeleton branch locations where no user constrait
	  could be generated
	- skeleton leaf nodes where SOPNET found additional segments
	- high cost segments that were selected by SOPNET

	For those locations, a segment is associated. Then, a lookup function to retrieve for a given segments the
	associated connected componente, i.e. the traversal along selected segments of the solution, can be called.
	"""
	data = {
		'slices': {}, 'segments': {}, 'lookup': {}
	}
	# Retrieve the UserConstraints associated with a skeleton

	# Retrieve all Segments associated with these constraints including the solution flag

	# Retrieve all Slices associated to those segments. Mark the slices of selected solution segments.

	return HttpResponse(json.dumps((data), separators=(',', ':')))


def retrieve_connected_component_from_initial_segment(request, segment_id = None):
	""" Retrieve slices and segments that are connected from an initial starting segment

	TODO: If we implement a mapping table from a connected component ID (e.g. skeletonID, assemblyID)
	to a segment, this breaks down to a lookup of the ID and retrieval of the connected component
	associated with the initial segment """
	pass
