from django.shortcuts import get_object_or_404

from catmaid.models import Treenode, Stack, Project, User, ProjectStack
from djsopnet.models import Slice, Segment
import networkx as nx

project_id=1
raw_stack_id=1
membrane_stack_id=2
selected_skeleton_id= 40

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
	skeleton_graph.node[ skeleton_node['id'] ] = {
		'x': x, 'y': y, 'z': z
	}

# ensure that root node has only one successor
if len( skeleton_graph.successors( root_node_id ) ) != 1:
	raise Exception('Skeleton graph root node requires to have only one continuation node in another section!')


def _retrieve_slices_in_boundingbox(resolution, translation, location):
	# TODO: Pixel-based lookup to select only really intersecting slices
	retslices = Slice.objects.filter(
		# section = pnd['section'],
		min_x__lte = (location['x'] - translation['x']) / resolution['x'],
		max_x__gte = (location['x'] - translation['x']) / resolution['x'],
		min_y__lte = (location['y'] - translation['y']) / resolution['y'],
		max_y__gte = (location['y'] - translation['y']) / resolution['y'],
	).values('hash_value')
	#print 'nr of slices found', len(retslices)
	return set( [r['hash_value'] for r in retslices] )

def _retrieve_slices_in_boundingbox_multiple_locations(resolution, translation, locations):
	all_slices = _retrieve_slices_in_boundingbox( resolution, translation, locations[0] )
	#print '0: nr of slices of all locations', len(all_slices)
	if len(locations) > 1:
		for i, location in enumerate(locations[1:]):
			all_slices = all_slices.intersection( _retrieve_slices_in_boundingbox( resolution, translation, location ) )
			#print str(i+1), 'nr of slices of all locations', len(all_slices)
	return all_slices

# supernode graph extraction
# --------------------------
# for each node, traverse the neighbourhood to find nodes of the same slice (e.g. at branch nodes)
# if no slice can be found that is consistent with this node set, retrieve the slice set for each node independently
# this makes the selection of correct slices more explicit, but without doing that we should still get
# the correct slice out at the later solver stages because the (e.g. two) constraint sets should enforce the correct larger slice

def _build_skeleton_super_graph(skeleton_graph):

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

super_graph = _build_skeleton_super_graph(skeleton_graph)

for node_id, d in super_graph.nodes_iter(data=True):
	data_for_skeleton_nodes = [skeleton_graph.node[skeleton_node_id] for skeleton_node_id in d['nodes_in_same_section']]
	# print '-----', d
	d['sliceset'] = _retrieve_slices_in_boundingbox_multiple_locations( resolution, translation, data_for_skeleton_nodes )


def _retrieve_end_segments_for_sliceset( sliceset, direction ):
		return  set([s['hash_value'] for s in \
			Segment.objects.filter( slice_a_hash__in = list(sliceset), type = 0, \
				direction = direction ).values('hash_value')])


# iterate the supergraph in order to select segments between each edge/leaf node

super_graph_root_node_id = [n for n,d in super_graph.in_degree().items() if d==0][0]

if len( skeleton_graph.successors( root_node_id ) ) != 1:
	raise Exception('Skeleton graph root node requires to have only one continuation node in another section!')

graph_traversal_nodes = [ super_graph_root_node_id ]

for node_id in graph_traversal_nodes:
	print '----'
	successors_of_node = super_graph.successors( node_id )
	nr_of_successors = len( successors_of_node )
	if nr_of_successors > 1:
		print 'found branch node'
		# found a branch node, skip it for now
		graph_traversal_nodes.extend( successors_of_node )
	elif nr_of_successors == 0 or node_id == super_graph_root_node_id:
		print 'found leaf node'
		# found leaf nodes, and define constraints
		current_node = super_graph.node[node_id]
		if node_id == super_graph_root_node_id:
			neighbor = super_graph.successors(node_id)[0]
			# continue from the root node
			graph_traversal_nodes.append( neighbor )
		else:
			neighbor = super_graph.predecessors(node_id)[0]
		parent_node_z = super_graph.node[ neighbor ]['z']
		if (parent_node_z - current_node['z']) > 0:
			intersection_segments = _retrieve_end_segments_for_sliceset( current_node['sliceset'], 0 )
		else:
			intersection_segments = _retrieve_end_segments_for_sliceset( current_node['sliceset'], 1 )

	else:
		print 'found contination node'
		assert( len(successors_of_node) == 1)
		# found continuation, find segments in the correct direction and create constraint
		top_node = super_graph.node[node_id]
		bottom_node = super_graph.node[successors_of_node[0]]
		if (bottom_node['z'] - top_node['z']) < 0:
			# top node has a higher z section index than bottom node, i.e.
			# continuations of slices of bottom node are in slice_b_hash
			tmp_node = bottom_node
			bottom_node = top_node
			top_node = tmp_node

		# Segments whose 'upper' slice is in the set of slices associated with the super node (only continuation egments)
		top_segments = set([s['hash_value'] for s in Segment.objects.filter( slice_a_hash__in = list(top_node['sliceset']), type = 1 ).values('hash_value')])

		# Segments whow 'lower' slice is in the set of slices associated with the one successor of the super node
		bottom_segments = set([s['hash_value'] for s in Segment.objects.filter( slice_b_hash__in = list(bottom_node['sliceset']), type = 1 ).values('hash_value')])

		# only select those continuation segments that are consistent with the skeleton
		intersection_segments = top_segments.intersection( bottom_segments )

		# create new user constraint for this set of segments
		graph_traversal_nodes.append( successors_of_node[0] )

	print 'intersection segments', intersection_segments


# how to map slices OR segments to blocks for the constraint


# TODO: keep a lookup table of locations that are inconsistent with the skeleton
#	- no slice found at skeleton node location
#	- N-way branch for which no branch segment exists
#	- continuation where no continuation segment exists
# -> those location are not mapped to any user constraint to constrain the solution, but stored and displayed for review


