import json

from django.http import HttpResponse

from djsopnet.models import Constraint, ConstraintSegmentRelation, Segment, SegmentSolution, Slice

def retrieve_slices_for_skeleton(request, project_id = None, stack_id = None, skeleton_id = None):
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


	# TOREMOVE: dummy example
	data = {
		'slices': {
			1: {
				'section': 0,
				'min_x': 0, 'min_y': 0,
				'width': 50, 'height': 50,
				'url': 'http://neurocity.janelia.org/l3vnc/slices/0/3.png',
				'color': "rgb(255,0,0)"
			},
		},
		'segments': {
		}
	}
	return HttpResponse(json.dumps((data), separators=(',', ':')))


	"""
	data = {
		'slices': {}, 'segments': {}, 'lookup': {}
	}
	# Retrieve the UserConstraints associated with a skeleton, and then all the associated segments
	constraint_ids = Constraint.objects.filter( skeleton = skeleton_id ).values('id')

	if len(constraint_ids) == 0:
		return HttpResponse(json.dumps(({'error': 'No UserConstaints were generated for this skeleton.'}), separators=(',', ':')))	

	constraint_segment_ids = ConstraintSegmentRelation.objects.filter( constraint__in = constraint_ids ).values('segment')

	# Retrieve all continuation and branch Segments associated with these constraints
	segments = Segment.objects.filter( id__in = constraint_segment_ids, type__gt = 1 ).values('id', 'section_inf', 'type', 'ctr_x', 'ctr_y')

	for seg in segments:
		data['segments'][seg['id']] = {
			'section': seg['section_inf'],
			'type': seg['type'],
			'ctr_x': seg['ctr_x'],
			'ctr_y': seg['ctr_y'],
			'left': [], 'right': []
		}

	segment_slices = SegmentSlice.objects.filter( segment__in = data['segments'].keys() ).values('slice', 'segment', 'direction')
	for ss in segment_slices:
		if ss['direction']:
			direction = 'left'
		else:
			direction = 'right'
		data['segments'][ss['segment']][direction].append( ss['slice'] )

	# add the solution flag to the segments
	segment_solutions = SegmentSolution.objects.filter( segment__in = data['segments'].keys() ).value('segment', 'solution')
	slices_to_retrieve = set()
	for sol in segment_solutions:
		seg = data['segments'][sol['segment']]
		seg['solution'] = sol['solution']
		slices_to_retrieve.update( seg['left'] + seg['right'] ) # add all slices for retrieval

	# Retrieve all Slices associated to those segments. Mark the slices of selected solution segments.
	# On demand retrieval from the client of additional slices of segments that are not part of the solution
	slices = Slice.objects.filter( id__ind = list(slices_to_retrieve) ).values('id', 'min_x', 'min_y', 'max_x',
		'max_y', 'section')
	for sli in slices:
		data['slices'][sli['id']] = {
			'section': sli['section'],
			'min_x': sli['min_x'], 'min_y': sli['min_y'],
			'max_x': sli['max_x'], 'max_y': sli['max_y']
		}
	
	# TODO: lookup locations
	return HttpResponse(json.dumps((data), separators=(',', ':')))


def retrieve_connected_component_from_initial_segment(request, segment_id = None):
	""" Retrieve slices and segments that are connected from an initial starting segment

	TODO: If we implement a mapping table from a connected component ID (e.g. skeletonID, assemblyID)
	to a segment, this breaks down to a lookup of the ID and retrieval of the connected component
	associated with the initial segment """
	pass


