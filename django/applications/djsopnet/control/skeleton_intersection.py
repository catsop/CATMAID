import json
import networkx as nx

from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from catmaid.models import Treenode, Stack, Project, User, ProjectStack, ClassInstance
from djsopnet.models import Slice, Segment, SegmentSlice, Constraint, ConstraintSegmentRelation


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
    skeleton_graph_root_node_id = [n for n, d in skeleton_graph.in_degree().items() if d == 0][0]

    # Initially start the search from the skeleton graph root node
    potential_cluster_parents = [(skeleton_graph_root_node_id, -1)]

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
                nodes_potentially_in_same_section.extend(skeleton_graph.successors(skeleton_graph_root_node_id_same_section))
            else:
                potential_cluster_parents.append((skeleton_graph_root_node_id_same_section, super_graph_node_id))

        skeleton_super_graph.add_node(super_graph_node_id, {'nodes_in_same_section': nodes_in_same_section, 'z': zsection})
        skeleton_super_graph.add_edge(super_graph_predecessor, super_graph_node_id)
        super_graph_node_id += 1

    # delete the dummy node from root
    skeleton_super_graph.remove_node(-1)

    return skeleton_super_graph


def _retrieve_slices_in_boundingbox(resolution, translation, location):
    retslices = Slice.objects.filter(
            section=int((location['z'] - translation['z']) / resolution['z']),
            min_x__lte=(location['x'] - translation['x']) / resolution['x'],
            max_x__gte=(location['x'] - translation['x']) / resolution['x'],
            min_y__lte=(location['y'] - translation['y']) / resolution['y'],
            max_y__gte=(location['y'] - translation['y']) / resolution['y'],
    ).values('id')
    # TODO: for retrieved slices, perform a pixel-based lookup to select only the
    # really intersecting slices
    return set([r['id'] for r in retslices])


def _retrieve_slices_in_boundingbox_multiple_locations(resolution, translation, locations):
    all_slices = _retrieve_slices_in_boundingbox(resolution, translation, locations[0])
    if len(locations) > 1:
        for i, location in enumerate(locations[1:]):
            all_slices = all_slices.intersection(_retrieve_slices_in_boundingbox(resolution, translation, location))
    return all_slices


def _generate_user_constraint_from_intersection_segments(skt, super_graph, allCompatibleSegments, u, p):
    for current_and_successor_node_id, compatible_segments in allCompatibleSegments:
        constraint = Constraint(user=u, project=p) # skeleton = skt <-- needs database modification
        constraint.save()
        for segment in compatible_segments:
            ConstraintSegmentRelation(constraint=constraint, segment_id=int(segment)).save()


def _get_section_node_dictionary(super_graph):
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


def _generate_user_constraints(user_id=None, project_id=None, stack_id=None, skeleton_id=None):
    u = get_object_or_404(User, pk=user_id)
    s = get_object_or_404(Stack, pk=stack_id)
    skt = get_object_or_404(ClassInstance, pk=skeleton_id)
    p = get_object_or_404(Project, pk=project_id)
    t = ProjectStack.objects.filter(stack=s, project=p)[0].translation
    translation = {'x': t.x, 'y': t.y, 'z': t.z}
    r = s.resolution
    resolution = {'x': r.x, 'y': r.y, 'z': r.z}

    skeleton_nodes = Treenode.objects.filter(skeleton_id=skeleton_id).values('id', 'location_x',
        'location_y', 'location_z', 'parent_id')
    skeleton_graph = nx.DiGraph()
    root_node_id = None
    for skeleton_node in skeleton_nodes:
        if skeleton_node['parent_id'] is None:
            root_node_id = skeleton_node['id']
            skeleton_graph.add_node(skeleton_node['id'], {})
        else:
            skeleton_graph.add_edge(skeleton_node['parent_id'], skeleton_node['id'])

        x, y, z = float(skeleton_node['location_x']), float(skeleton_node['location_y']), float(skeleton_node['location_z']),
        skeleton_graph.node[skeleton_node['id']] = {'x': x, 'y': y, 'z': z}

    # ensure that root node has only one successor
    if len(skeleton_graph.successors(root_node_id)) != 1:
        raise Exception('Skeleton graph root node requires to have only one continuation node in another section!')

    super_graph = _build_skeleton_super_graph(skeleton_graph)

    for node_id, d in super_graph.nodes_iter(data=True):
        data_for_skeleton_nodes = [skeleton_graph.node[skeleton_node_id] for skeleton_node_id in d['nodes_in_same_section']]
        d['sliceset'] = _retrieve_slices_in_boundingbox_multiple_locations(resolution, translation, data_for_skeleton_nodes)

    # iterate the supergraph in order to select segments between each edge/leaf node
    super_graph_root_node_id = [n for n, d in super_graph.in_degree().items() if d == 0][0]

    if len(skeleton_graph.successors(root_node_id)) != 1:
        raise Exception('Skeleton graph root node requires to have only one continuation node in another section!')

    # To find the set of constraints that ensures a solution that is compatible with an interpretation of a particular skeleton we will procede as follows:
    # For each edge in the supergraph we will find segments in the database that contain the edge,
    # that is segments where at least one upper slice is in the sliceset of the top node and at least one lower slice is in the sliceset of the bottom node.
    # Additionally we want to further select those segments where all the other slices cover nodes of the supergraph,
    # that is all upper slices are contained within the section slice set of the upper node
    # and all the bottom slices are contained within the section slice set of the bottom node.

    section_node_dictionary = _get_section_node_dictionary(super_graph)

    graph_traversal_nodes = [super_graph_root_node_id]
    allCompatibleSegments = []
    # List of edges for which no compatible segment could be found:
    uncompatibleLocations = []
    for current_node_id in graph_traversal_nodes:
        # We will need the successors of the current node to traverse the graph and to find the segments that constitute the skeleton constraints.
        successors_of_node = super_graph.successors(current_node_id)
        # Remember the successors of the current node to continue to traverse the graph later
        graph_traversal_nodes.extend(successors_of_node)

        for successor_id in successors_of_node:

            # Its helpful to know if the edge points up or down in the stack
            if super_graph.node[current_node_id]['z'] < super_graph.node[successor_id]['z']:
                top_node_id = current_node_id
                bottom_node_id = successor_id
            else:
                top_node_id = successor_id
                bottom_node_id = current_node_id

            # Get the actual nodes from the ids
            top_node = super_graph.node[top_node_id]
            bottom_node = super_graph.node[bottom_node_id]

            bottomSectionSliceSet = []
            for nodeInSection in section_node_dictionary[bottom_node['z']]:
                bottomSectionSliceSet.extend(list(bottom_node['sliceset']))

            topSectionSliceSet = []
            for nodeInSection in section_node_dictionary[top_node['z']]:
                topSectionSliceSet.extend(list(top_node['sliceset']))

            segmentsContainingEdge_id = set()

            if len(bottomSectionSliceSet) != 0 and len(topSectionSliceSet) != 0:

                string_top_node_sliceset = '('
                for n in top_node['sliceset']:
                    string_top_node_sliceset = string_top_node_sliceset + str(n) + ','
                string_top_node_sliceset = string_top_node_sliceset[:-1]
                string_top_node_sliceset = string_top_node_sliceset + ')'
                print 'Top node slice set: ' + string_top_node_sliceset

                string_bottom_node_sliceset = '('
                for n in bottom_node['sliceset']:
                    string_bottom_node_sliceset = string_bottom_node_sliceset + str(n) + ','
                string_bottom_node_sliceset = string_bottom_node_sliceset[:-1]
                string_bottom_node_sliceset = string_bottom_node_sliceset + ')'
                print 'Bottom node slice set: ' + string_bottom_node_sliceset

                query_string = '''
                        SELECT DISTINCT ss1.id FROM djsopnet_segmentslice ss1
                        JOIN djsopnet_segmentslice ss2
                        ON ss1.segment_id = ss2.segment_id
                        WHERE ss1.slice_id IN %s
                        AND ss2.slice_id IN %s;
                        ''' % (string_top_node_sliceset, string_bottom_node_sliceset)

                for ss in SegmentSlice.objects.raw(query_string):
                    segmentsContainingEdge_id.add(ss.segment.id)

            print 'SegmentsContainingEdge: ' + str(segmentsContainingEdge_id)

            compatibleSegments_id = []
            # Then select those where all (the other) top and bottom sections are in the respective section slice sets
            for segment_id in segmentsContainingEdge_id:
                # Get the slices that constitute the segment
                top_slices = set([s['slice'] for s in SegmentSlice.objects.filter(segment=segment_id, direction=True).values('slice')])
                bottom_slices = set([s['slice'] for s in SegmentSlice.objects.filter(segment=segment_id, direction=False).values('slice')])
                if top_slices <= set(topSectionSliceSet) and bottom_slices <= set(bottomSectionSliceSet):
                    compatibleSegments_id.append(segment_id)

            # When no compatible segment is found for a particular edge we want to store the edge in a lookup table to review that location later manually.
            # In this case no user constraint should be added.
            if len(compatibleSegments_id) == 0:
                skeletonNodesInCurrentNode = super_graph.node[current_node_id]['nodes_in_same_section']
                skeletonNodesInSuccessorNode = super_graph.node[successor_id]['nodes_in_same_section']
                super_edge_in_skeleton = (skeletonNodesInCurrentNode, skeletonNodesInSuccessorNode)
                super_graph_edge = (current_node_id, successor_id)
                uncompatibleLocations.append((super_edge_in_skeleton, super_graph_edge))
            else:
                allCompatibleSegments.append(((current_node_id, successor_id), compatibleSegments_id))

    # generate user constraints from intersection
    _generate_user_constraint_from_intersection_segments(skt, super_graph, allCompatibleSegments, u, p)

    return {'all_compatible_segments': allCompatibleSegments, 'uncompatible_locations': uncompatibleLocations}


def generate_user_constraints(request, project_id=None, stack_id=None, skeleton_id=None):
    """ For a given skeleton, generate user constraints """
    data = _generate_user_constraints(request.user.id, project_id, stack_id, skeleton_id)
    return HttpResponse(json.dumps((data), separators=(',', ':')))

# TODO: keep a lookup table of locations that are inconsistent with the skeleton
#   - no slice found at skeleton node location
#   - N-way branch for which no branch segment exists: in supergraph if more than two successors
#   - continuation where no continuation segment exists
# -> those location are not mapped to any user constraint to constrain the solution, but stored and displayed for review

#_generate_user_constraints( 1, 1, 1, 40 )

