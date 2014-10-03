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


def retrieve_connected_component_starting_from_initial_slice(request, slice_id = None):
	""" Retrieve slices and segments that are connected from an initial starting slice

	Traverse the slices and segments along segments which are in the solution. If none of the
	outgoing segments are in the solution, return these locations separately with all the associated
	segments.

	Returned data structure can be used for e.g. 
		- for visualization of the slices and segments in 3d
		- associate the set of slices and segments with an assembly id
		- iterative expansion of a neuron by processing additional core blocks
		  at no_solution_segments locations
	"""

	data = { 'slices': [], 'segments': [], 'no_solution_segments': {} }

	slices_to_visit = [(slice_id, True), (slice_id, False)]

	for sliceid, direction in slices_to_visit:

		data['slices'].append( sliceid )

		# We want to traverse in direction seen from slice, which is 'not direction', seen from segment
		reverse_direction = not direction
		segments = [s['segment'] for s in SegmentSlice.objects.filter( slice = sliceid, direction = reverse_direction).values('segment', 'slice', 'direction')]
		# any of those segments in the solution?
		solutions = [s['segment'] for s in SegmentSolution.objects.filter( segment__in = segments ).values('segment')]

		if len(solutions) == 1:
			# if yes: look up corresponding slices in direction
			solution_segmentid = solutions[0]
			# add solution segment to returned data
			data['segments'].append( solution_segmentid )

			# retrieve slices associated to the solution segmente and add to list for traversal
			associated_slices = [(s['slice'],s['direction']) for s in SegmentSlice.objects.filter( slice = solution_segmentid ).values('segment', 'slice', 'direction')]

			for associated_sliceid, associated_direction in associated_slices:
				if associated_slice != sliceid:
					# only add slice if not yet visited
					slices_to_visit.extend( (associated_sliceid, associated_direction) )

		else:
			# if no: add all segments to no_solution_segments
			data['no_solution_segments'][ (sliceid, direction) ] = {
				segments
			}

	return HttpResponse(json.dumps((data), separators=(',', ':')))