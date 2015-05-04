import json
import networkx as nx

from django.db import connection
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from catmaid.models import Treenode, Stack, Project, User, ProjectStack, ClassInstance
from djsopnet.control.slice import _slice_ids_intersecting_point
from djsopnet.models import SegmentationStack


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


def _retrieve_slices_in_boundingbox(segmentation_stack_id, resolution, translation, location):
    return set(_slice_ids_intersecting_point(segmentation_stack_id,
            (location['x'] - translation['x']) / resolution['x'],
            (location['y'] - translation['y']) / resolution['y'],
            int((location['z'] - translation['z']) / resolution['z'])))


def _retrieve_slices_in_boundingbox_multiple_locations(segmentation_stack_id, resolution, translation, locations):
    all_slices = _retrieve_slices_in_boundingbox(segmentation_stack_id, resolution, translation, locations[0])
    if len(locations) > 1:
        for i, location in enumerate(locations[1:]):
            all_slices = all_slices.intersection(_retrieve_slices_in_boundingbox(segmentation_stack_id, resolution, translation, location))
    return all_slices


def _generate_user_constraint_from_intersection_segments(segmentation_stack_id, user, skt, all_compatible_segments):
    cursor = connection.cursor()

    for current_and_successor_node_id, compatible_segments in all_compatible_segments:
        cursor.execute('''
                INSERT INTO segstack_%(segstack_id)s.solution_constraint
                (user_id, creation_time, edition_time, skeleton_id, relation, value) VALUES
                (%(user_id)s, now(), now(), %(skeleton_id)s, 'Equal'::constraintrelation, 1.0)
                RETURNING id;
                ''' % {'segstack_id': segmentation_stack_id, 'user_id': user.id, 'skeleton_id': skt.id})
        constraint_id = cursor.fetchone()[0]
        segment_ids = '),('.join(map(str, compatible_segments))
        cursor.execute('''
                INSERT INTO segstack_%(segstack_id)s.constraint_segment_relation
                (constraint_id, segment_id, coefficient)
                SELECT %(constraint_id)s, seg.id, 1
                FROM (VALUES (%(segment_ids)s)) AS seg(id);
                ''' % {'segstack_id': segmentation_stack_id,
                       'constraint_id': constraint_id,
                       'segment_ids': segment_ids})


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


def _generate_user_constraints(user_id=None, segmentation_stack_id=None, skeleton_id=None):
    u = get_object_or_404(User, pk=user_id)
    segstack = get_object_or_404(SegmentationStack, pk=segmentation_stack_id)
    skt = get_object_or_404(ClassInstance, pk=skeleton_id)
    t = segstack.project_stack.translation
    translation = {'x': t.x, 'y': t.y, 'z': t.z}
    r = segstack.project_stack.stack.resolution
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
        d['sliceset'] = _retrieve_slices_in_boundingbox_multiple_locations(segstack.id, resolution, translation, data_for_skeleton_nodes)

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

    graph_traversal_nodes = [super_graph_root_node_id]
    all_compatible_segments = []
    # List of edges for which no compatible segment could be found:
    incompatible_locations = []
    cursor = connection.cursor()
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

            bottom_section_slice_set = list(bottom_node['sliceset'])

            top_section_slice_set = list(top_node['sliceset'])

            segment_containing_edge_ids = set()

            if len(bottom_section_slice_set) != 0 and len(top_section_slice_set) != 0:

                string_top_node_sliceset = '(' + ','.join(map(str, top_node['sliceset'])) + ')'
                print 'Top node slice set: ' + string_top_node_sliceset

                string_bottom_node_sliceset = '(' + ','.join(map(str, bottom_node['sliceset'])) + ')'
                print 'Bottom node slice set: ' + string_bottom_node_sliceset

                cursor.execute('''
                        SELECT DISTINCT ss1.segment_id
                        FROM segstack_%(segstack_id)s.segment_slice ss1
                        JOIN segstack_%(segstack_id)s.segment_slice ss2
                        ON ss1.segment_id = ss2.segment_id
                        WHERE ss1.slice_id IN %(top_sliceset)s
                        AND ss2.slice_id IN %(bottom_sliceset)s;
                        ''' % {'segstack_id': segstack.id,
                               'top_sliceset': string_top_node_sliceset,
                               'bottom_sliceset': string_bottom_node_sliceset})

                segment_containing_edge_ids.update([r[0] for r in cursor.fetchall()])

            print 'SegmentsContainingEdge: ' + str(segment_containing_edge_ids)

            compatible_segment_ids = []
            # Then select those where all (the other) top and bottom sections are in the respective section slice sets
            for segment_id in segment_containing_edge_ids:
                # Get the slices that constitute the segment
                cursor.execute('''
                        SELECT slice_id, direction
                        FROM segstack_%s.segment_slice
                        WHERE segment_id = %s
                        ''' % (segstack.id, segment_id))
                segment_slices = cursor.fetchall()
                top_slices = set([s[0] for s in segment_slices if s[1]])
                bottom_slices = set([s[0] for s in segment_slices if not s[1]])
                if top_slices <= set(top_section_slice_set) and bottom_slices <= set(bottom_section_slice_set):
                    compatible_segment_ids.append(segment_id)

            # When no compatible segment is found for a particular edge we want to store the edge in a lookup table to review that location later manually.
            # In this case no user constraint should be added.
            if len(compatible_segment_ids) == 0:
                skeleton_nodes_in_current_node = super_graph.node[current_node_id]['nodes_in_same_section']
                skeleton_nodes_in_successor_node = super_graph.node[successor_id]['nodes_in_same_section']
                super_edge_in_skeleton = (skeleton_nodes_in_current_node, skeleton_nodes_in_successor_node)
                super_graph_edge = (current_node_id, successor_id)
                incompatible_locations.append((super_edge_in_skeleton, super_graph_edge))
            else:
                all_compatible_segments.append(((current_node_id, successor_id), compatible_segment_ids))

    # generate user constraints from intersection
    _generate_user_constraint_from_intersection_segments(segstack.id, u, skt, all_compatible_segments)

    return {'all_compatible_segments': all_compatible_segments, 'incompatible_locations': incompatible_locations}


def generate_user_constraints(request, project_id=None, segmentation_stack_id=None, skeleton_id=None):
    """ For a given skeleton, generate user constraints """
    data = _generate_user_constraints(request.user.id, segmentation_stack_id, skeleton_id)
    return HttpResponse(json.dumps((data), separators=(',', ':')))

# TODO: keep a lookup table of locations that are inconsistent with the skeleton
#   - no slice found at skeleton node location
#   - N-way branch for which no branch segment exists: in supergraph if more than two successors
#   - continuation where no continuation segment exists
# -> those location are not mapped to any user constraint to constrain the solution, but stored and displayed for review
