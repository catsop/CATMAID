from django.shortcuts import get_object_or_404

from catmaid.models import Treenode, Stack, Project, User, ProjectStack
from djsopnet.models import Slice, Segment, Constraint, ConstraintSegmentRelation
import networkx as nx


def _build_skeleton_super_graph(skeleton_graph):
	""" From the skeleton graph, extract a super-graph where consecutive nodes in the
	same section are grouped together into a super-node. The purpose is to limit the set
	of slices to the set that is consistent with all the consecutive nodes, presumably
	annotated in the same slice """

	# Set up new (empty) super graph
	skeleton_super_graph = nx.DiGraph()
	
	# Initiallize the unique id for the super graph as 0.
	super_graph_node_id = 0
	
	# Find the root node of the skeleton graph to traverse it and build the super graph in the process
	skeleton_graph_root_node_id = [n for n,d in skeleton_graph.in_degree().items() if d==0][0]

	# Initially start the search from the skeleton graph root node
	potential_cluster_parents = [(skeleton_graph_root_node_id,-1)]
	
	# Traverse graph
	for skeleton_graph_node_id, super_graph_predecessor in potential_cluster_parents:

		# Find all the downstream nodes in the same section
		nodes_potentially_in_same_section = skeleton_graph.successors(skeleton_graph_node_id)
		nodes_in_same_section = [skeleton_graph_node_id]
		zsection = skeleton_graph.node[skeleton_graph_node_id]['z']

		for skeleton_graph_root_node_id_same_section in nodes_potentially_in_same_section:

			# Child in same section?
			if skeleton_graph.node[skeleton_graph_root_node_id_same_section]['z'] == zsection:
				nodes_in_same_section.append(skeleton_graph_root_node_id_same_section)
				nodes_potentially_in_same_section.extend( skeleton_graph.successors(skeleton_graph_root_node_id_same_section) )
			else:
				potential_cluster_parents.append((skeleton_graph_root_node_id_same_section,super_graph_node_id))

		skeleton_super_graph.add_node(super_graph_node_id,{'nodes_in_same_section': nodes_in_same_section, 'z': zsection})
		skeleton_super_graph.add_edge(super_graph_predecessor, super_graph_node_id)
		super_graph_node_id += 1
	
	# delete the dummy node from root	
	skeleton_super_graph.remove_node( -1 )

	return skeleton_super_graph


def _retrieve_slices_in_boundingbox(resolution, translation, location):
	retslices = Slice.objects.filter(
		# section = pnd['section'],
		min_x__lte = (location['x'] - translation['x']) / resolution['x'],
		max_x__gte = (location['x'] - translation['x']) / resolution['x'],
		min_y__lte = (location['y'] - translation['y']) / resolution['y'],
		max_y__gte = (location['y'] - translation['y']) / resolution['y'],
	).values('id')
	# TODO: for retrieved slices, perform a pixel-based lookup to select only the
	# really intersecting slices
	return set( [r['id'] for r in retslices] )


def _retrieve_slices_in_boundingbox_multiple_locations(resolution, translation, locations):
	all_slices = _retrieve_slices_in_boundingbox( resolution, translation, locations[0] )
	if len(locations) > 1:
		for i, location in enumerate(locations[1:]):
			all_slices = all_slices.intersection( _retrieve_slices_in_boundingbox( resolution, translation, location ) )
	return all_slices


def _retrieve_end_segments_for_sliceset( sliceset, direction ):
		return  set([s['id'] for s in \
			Segment.objects.filter( slice_a_id_in = list(sliceset), type = 0, \
				direction = direction ).values('id')])


def _generate_user_constraint_from_intersection_segments( skeletonid, super_graph, all_intersection_segments ):
	for node_id, intersection_segments in all_intersection_segments:
		constraint = Constraint(user = u, project = p, skeleton = skeletonid, \
			associated_skeleton_nodes = super_graph.node[node_id]['nodes_in_same_section'] )
		constraint.save()
		for segment in intersection_segments:
			ConstraintSegmentRelation( constraint=constraint,
				segment = int(segment) ).save()

def _get_section_node_dictionary( super_graph ):
	section_node_dictionary = dict()
	for node_id in super_graph.nodes():
		# check if there are already nodes listed in the dictionary for the section of the current node
		node_section = super_graph.node[node_id]['z']
		if node_section in section_node_dictionary:
			# if yes append the current node
			section_node_dictionary[node_section].append(node_id)
		else:
			# if no create a new entry with the current node
			section_node_dictionary[node_section] = [node_id]
	return section_node_dictionary

####################################################################################
# Start script that goes later into a function that is called for a given skeleton
####################################################################################

project_id=1
raw_stack_id=1
membrane_stack_id=2
selected_skeleton_id=16
lookup_locations = []
# keep track of sites on the skeleton for later manual reviewing of the SOPNET solution
# no_slice_found: at the skeleton node location
# n-way-branch: 
# no_continuation_found:

# TODO: keep a lookup table of locations that are inconsistent with the skeleton
#	- no slice found at skeleton node location
#	- N-way branch for which no branch segment exists
#	- continuation where no continuation segment exists
# -> those location are not mapped to any user constraint to constrain the solution, but stored and displayed for review

s = get_object_or_404(Stack, pk=raw_stack_id)
p = get_object_or_404(Project, pk=project_id)
u = User.objects.get(id = 1)
t = ProjectStack.objects.filter( stack = s, project = p )[0].translation
translation = {'x': t.x, 'y': t.y, 'z': t.z}
r = s.resolution
resolution = {'x': r.x, 'y': r.y, 'z': r.z}

skeleton_nodes = Treenode.objects.filter(skeleton_id=selected_skeleton_id).values('id', 'location', 'parent_id')
skeleton_graph = nx.DiGraph()
root_node_id = None
for skeleton_node in skeleton_nodes:
	if skeleton_node['parent_id'] is None:
		root_node_id = skeleton_node['id']
		skeleton_graph.add_node( skeleton_node['id'], {} )
	else:
		skeleton_graph.add_edge( skeleton_node['parent_id'], skeleton_node['id'] )
	
	x,y,z = map(float, skeleton_node['location'][1:-1].split(','))
	skeleton_graph.node[ skeleton_node['id'] ] = { 'x': x, 'y': y, 'z': z }

# ensure that root node has only one successor
if len( skeleton_graph.successors( root_node_id ) ) != 1:
	raise Exception('Skeleton graph root node requires to have only one continuation node in another section!')

super_graph = _build_skeleton_super_graph(skeleton_graph)

for node_id, d in super_graph.nodes_iter(data=True):
	data_for_skeleton_nodes = [skeleton_graph.node[skeleton_node_id] for skeleton_node_id in d['nodes_in_same_section']]
	d['sliceset'] = _retrieve_slices_in_boundingbox_multiple_locations( resolution, translation, data_for_skeleton_nodes )

# iterate the supergraph in order to select segments between each edge/leaf node
super_graph_root_node_id = [n for n,d in super_graph.in_degree().items() if d==0][0]

if len( skeleton_graph.successors( root_node_id ) ) != 1:
	raise Exception('Skeleton graph root node requires to have only one continuation node in another section!')

# To find the set of constraints that ensures a solution that is compatible with an interpretation of a particular skeleton we will procede as follows:
# For each edge in the supergraph we will add the constraint that this edge is either part of a continuation or part of a branch.
# For the continuations we will select all segments that 'contain' the edge.
# For the branches we will select segments that contian the edge and at least one additional node in one of the two sections of the edge.
# This might lead to the acceptance of unlikely branch segments which is hopefully prevented by virtue of these branch segments not being generated in sopnet.

section_node_dictionary = _get_section_node_dictionary(super_graph)

graph_traversal_nodes = [ super_graph_root_node_id ]
allCompatibleSegments = []
# List of edges for which no compatible segment could be found:
uncompatibleLocations = []
for current_node_id in graph_traversal_nodes:
	# We will need the successors of the current node to traverse the graph and to find the segments that constitute the skeleton constraints.
	successors_of_node = super_graph.successors( current_node_id )
	# Remember the successors of the current node to continue to traverse the graph later
	graph_traversal_nodes.extend(successors_of_node)

	for successor_id in successors_of_node:

		# Its helpful to know if the edge points up or down in the stack
		if super_graph.node[current_node_id]['z'] < super_graph.node[successor]['z']:
			top_node_id = current_node_id
			bottom_node_id = successor_id
		else:
			top_node_id = successor_id
			bottom_node_id = current_node_id

		# Get the actual nodes from the ids
		top_node = super_graph.node[top_node_id]
		bottom_node = super_graph.node[bottom_node_id]

		# CONTINUATIONS
		# We will need to find the continuations that contain the edge in question

		# Continuations that contain the top node:
		continuationsContTopNode = set([s['id'] for s in Segment.objects.filter( slice_a_id__in = list(top_node['sliceset']), type = 1 ).values('id')])
		# Continuations that contain the bottom node:
		continuationsContBottomNode = set([s['id'] for s in Segment.objects.filter( slice_b_id__in = list(bottom_node['sliceset']), type = 1 ).values('id')])	
		
		# Continuations that contain the top and the bottom node:
		compatibleContinuations = continuationsContTopNode.intersection( continuationsContBottomNode )

		# BRANCHES
		# We will also need to find the branches where the edge is contained in one arm and the other arm contains another node of the same skeleton
		# super graph

		compatibleBranches = []

		# Downward branches: branches that have the a-slice in the upper section
		# Set of slices that contain nodes of the current skeleton in the section of the bottom node
		bottomSectionSliceSet = []
		for nodeInSection in section_node_dictionary[bottom_node['z']]:
			bottomSectionSliceSet.extend(list(bottom_node['sliceset']))
 
		# Edge in AB-arm
		DABbranchesContTopNode = set([s['id'] for s in Segment.objects.filter( slice_a_id__in = list(top_node['sliceset']), type = 2 ).values('id')])
		DABbranchesContBottomNode = set([s['id'] for s in Segment.objects.filter( slice_b_id__in = list(bottom_node['sliceset']), type = 2 ).values('id')])
		DABbranchesContEdge = DABbranchesContTopNode.intersection( DABbranchesContBottomNode ) 

		# AC-arm contains another node of the skeleton
		branchesContNode = set([s['id'] for s in Segment.objects.filter( slice_c_id__in = bottomSectionSliceSet, type = 2 ).values('id')])
		DABbranchesContEdgeAndNode = DABbranchesContEdge.intersection( branchesContNode )
		compatibleBranches.extend( DABbranchesContEdgeAndNode )

		# Edge in AC-arm
		DACbranchesContTopNode = set([s['id'] for s in Segment.objects.filter( slice_a_id__in = list(top_node['sliceset']), type = 2 ).values('id')])
		DACbranchesContBottomNode = set([s['id'] for s in Segment.objects.filter( slice_c_id__in = list(bottom_node['sliceset']), type = 2 ).values('id')])
		DACbranchesContEdge = DACbranchesContTopNode.intersection( DACbranchesContBottomNode ) 

		# AB-arm contains another node of the skeleton
		branchesContNode = set([s['id'] for s in Segment.objects.filter( slice_b_id__in = bottomSectionSliceSet, type = 2 ).values('id')])
		DACbranchesContEdgeAndNode = DACbranchesContEdge.intersection( branchesContNode )
		compatibleBranches.extend( DACbranchesContEdgeAndNode )

		# Upward branches: branches that have the a-slice in the lower section
		# Set of slices that contain nodes of the current skeleton in the section of the top node
		topSectionSliceSet = []
		for nodeInSection in section_node_dictionary[top_node['z']]:
			topSectionSliceSet.extend(list(top_node['sliceset']))

		# Edge in AB-arm
		UABbranchesContTopNode = set([s['id'] for s in Segment.objects.filter( slice_b_id__in = list(top_node['sliceset']), type = 2 ).values('id')])
		UABbranchesContBottomNode = set([s['id'] for s in Segment.objects.filter( slice_a_id__in = list(bottom_node['sliceset']), type = 2 ).values('id')])
		UABbranchesContEdge = UABbranchesContTopNode.intersection( UABbranchesContBottomNode ) 

		# AC-arm contains another node of the skeleton
		branchesContNode = set([s['id'] for s in Segment.objects.filter( slice_c_id__in = topSectionSliceSet, type = 2 ).values('id')])
		UABbranchesContEdgeAndNode = UABbranchesContEdge.intersection( branchesContNode )
		compatibleBranches.extend( UABbranchesContEdgeAndNode )

		# Edge in AC-arm
		UACbranchesContTopNode = set([s['id'] for s in Segment.objects.filter( slice_c_id__in = list(top_node['sliceset']), type = 2 ).values('id')])
		UACbranchesContBottomNode = set([s['id'] for s in Segment.objects.filter( slice_a_id__in = list(bottom_node['sliceset']), type = 2 ).values('id')])
		UACbranchesContEdge = UACbranchesContTopNode.intersection( UACbranchesContBottomNode ) 

		# AB-arm contains another node of the skeleton
		branchesContNode = set([s['id'] for s in Segment.objects.filter( slice_b_id__in = topSectionSliceSet, type = 2 ).values('id')])
		UACbranchesContEdgeAndNode = UACbranchesContEdge.intersection( branchesContNode )
		compatibleBranches.extend( UACbranchesContEdgeAndNode )


		# At this point all compatible continuations and branches should have been found, so we can combine them to find all the compatible segments.
		compatibleSegments = compatibleContinuations.union( compatibleBranches )

		allCompatibleSegments.append( ((current_node_id, successor_id), compatibleSegments) )

		# When no compatible segment is found for a particular edge we want to store the edge in a lookup table to review that location later manually.
		# In this case no user constraint should be added.
		if len(compatibleSegments) == 0:
			skeletonNodesInCurrentNode = super_graph.node[current_node_id]['nodes_in_same_section']
			skeletonNodesInSuccessorNode = super_graph.node[successor_id]['nodes_in_same_section']
			super_edge_in_skeleton = (skeletonNodesInCurrentNode, skeletonNodesInSuccessorNode)
			super_graph_edge = (current_node_id, successor_id)
			uncompatibleLocations.append( (super_edge_in_skeleton, super_graph_edge) )

