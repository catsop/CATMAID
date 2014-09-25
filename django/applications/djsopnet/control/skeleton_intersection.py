from django.shortcuts import get_object_or_404

from catmaid.models import Treenode, Stack, Project, User, ProjectStack
from djsopnet.models import Slice
import networkx as nx

project_id=1
raw_stack_id=1
membrane_stack_id=2
selected_skeleton_id= 102

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

def _retrieve_slices_in_boundingbox(resolution, translation, location):
	# TODO: Pixel-based lookup to select only really intersecting slices
	return set( Slice.objects.filter(
		# section = pnd['section'],
		min_x__lte = (location['x'] - translation['x']) / resolution['x'],
		max_x__gte = (location['x'] - translation['x']) / resolution['x'],
		min_y__lte = (location['y'] - translation['y']) / resolution['y'],
		max_y__gte = (location['y'] - translation['y']) / resolution['y'],
	).values('hash_value') )

def _retrieve_slices_in_boundingbox_multiple_locations(resolution, translation, locations):
	all_slices = set()
	for location in locations:
		all_slices.intersection( _retrieve_slices_in_boundingbox( resolution, translation, location ) )
	return all_slices

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

		for skeleton_graph_root_node_id_same_section in nodes_potentially_in_same_section:

			# Child in same section?
			if skeleton_graph.node[skeleton_graph_root_node_id_same_section]['z'] == skeleton_graph.node[skeleton_graph_node_id]['z']:
				nodes_in_same_section.append(skeleton_graph_root_node_id_same_section)
				nodes_potentially_in_same_section.extend( skeleton_graph.successors(skeleton_graph_root_node_id_same_section) )
			else:
				potential_cluster_parents.append((skeleton_graph_root_node_id_same_section,super_graph_node_id))

		skeleton_super_graph.add_node(super_graph_node_id,{'nodes_in_same_section':nodes_in_same_section})
		skeleton_super_graph.add_edge(super_graph_node_id, super_graph_predecessor)
		super_graph_node_id += 1
	
	# delete the dummy node from root	
	skeleton_super_graph.remove_node( -1 )

	return skeleton_super_graph

super_graph = _build_skeleton_super_graph(skeleton_graph)

for node_id, d in super_graph.nodes_iter(data=True):
	data_for_skeleton_nodes = [skeleton_graph.node[skeleton_node_id] for skeleton_node_id in d['nodes_in_same_section']]
	d['sliceset'] = _retrieve_slices_in_boundingbox_multiple_locations( resolution, translation, data_for_skeleton_nodes )


# TODO: keep a lookup table of locations that are inconsistent with the skeleton
#	- no slice found at skeleton node location
#	- N-way branch for which no branch segment exists
#	- continuation where no continuation segment exists
# -> those location are not mapped to any user constraint to constrain the solution

# supernode graph extraction
# --------------------------
# for each node, traverse the neighbourhood to find nodes of the same slice (e.g. at branch nodes)
# if no slice can be found that is consistent with this node set, retrieve the slice set for each node independently
# this makes the selection of correct slices more explicit, but without doing that we should still get
# the correct slice out at the later solver stages because the (e.g. two) constraint sets should enforce the correct larger slice


# iterate over all slice-sets to find the selection of segments

	# For parent slices, retrieve all the segments towards the child slice
	# For child slices, retrieve all the segments towards the parent slice
	# Intersection both segment set to retrieve segments of interest

