import itertools
import json
import networkx as nx

from django.db import connection
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404

from catmaid.control.authentication import requires_user_role
from catmaid.control.skeleton import _import_skeleton
from catmaid.models import UserRole
from djsopnet.models import SegmentationStack


@requires_user_role(UserRole.Annotate)
def map_assembly_equivalence_to_skeleton(request, project_id, segmentation_stack_id, equivalence_id):
    segstack = get_object_or_404(SegmentationStack, id=segmentation_stack_id)
    equivalence_id = int(equivalence_id)
    cursor = connection.cursor()
    cursor.execute('''
        SELECT 1 FROM segstack_{0}.assembly_equivalence WHERE id = %s
        '''.format(segstack.id), (equivalence_id,))
    if cursor.rowcount == 0:
        raise Http404('No AssemblyEquivalence with ID %s exists' % equivalence_id)

    ids = _map_assembly_equivalence_to_skeleton(request, segmentation_stack_id, equivalence_id)
    ids['ok'] = True

    return HttpResponse(json.dumps(ids), content_type='text/json')

def _map_assembly_equivalence_to_skeleton(request, segmentation_stack_id, equivalence_id, min_nodes=2):
    segstack = SegmentationStack.objects.get(id=segmentation_stack_id)
    project_id = segstack.configuration.project_id
    # Check that this equivalence is populated with segments.
    cursor = connection.cursor()
    cursor.execute('''
        SELECT count(aseg.segment_id) FROM segstack_%(segstack_id)s.assembly_segment aseg
        JOIN segstack_%(segstack_id)s.assembly a ON a.id = aseg.assembly_id
        WHERE a.equivalence_id = %(equivalence_id)s
        ''' % {'segstack_id': segstack.id, 'equivalence_id': equivalence_id})
    segment_count = cursor.fetchone()[0]
    if segment_count == 0:
        return

    arborescence = map_assembly_equivalence_to_arborescence(segmentation_stack_id, equivalence_id)
    if arborescence.number_of_nodes() < min_nodes:
        return
    imported_skeleton = _import_skeleton(request, project_id, arborescence,
            name='AssemblyEquivalence %s' % equivalence_id)

    # Set the mapped skeleton ID for this AssemblyEquivalence.
    cursor.execute('''
        UPDATE segstack_%s.assembly_equivalence
        SET skeleton_id = %s
        WHERE id = %s
        ''' % (segstack.id, imported_skeleton['skeleton_id'], equivalence_id))

    # TODO: annotate neurons to indicate they are mapped.

    # Generate tuple string for slice ID -> treenode ID.
    tn_slice_values = \
            '),('.join([','.join(map(str, (n[0], n[1]['id']))) \
            for n in imported_skeleton['graph'].nodes_iter(data=True)])
    cursor.execute('''
        INSERT INTO segstack_%s.treenode_slice (slice_id, treenode_id)
        VALUES (%s)
        ''' % (segstack.id, tn_slice_values))

    return {'neuron_id': imported_skeleton['neuron_id'], 'skeleton_id': imported_skeleton['skeleton_id']}

def map_assembly_equivalence_to_arborescence(segmentation_stack_id, equivalence_id):
    """Create skeletons for existing equivalences and map nodes to slices."""
    segstack = SegmentationStack.objects.get(id=segmentation_stack_id)
    equivalence_id = int(equivalence_id)
    cursor = connection.cursor()

    ps = segstack.project_stack
    stack = ps.stack
    bi = segstack.configuration.block_info
    zoom = 2**bi.scale

    # Fetch all segments and their slices in equivalence.
    cursor.execute('''
        SELECT
          aseg.segment_id AS segment_id,
          JSON_AGG(DISTINCT ROW(s.id, s.ctr_x, s.ctr_y, s.section, ss.direction)) AS segment_slices
        FROM segstack_%(segstack_id)s.assembly a
        JOIN segstack_%(segstack_id)s.assembly_segment aseg
          ON (aseg.assembly_id = a.id)
        JOIN segstack_%(segstack_id)s.segment_slice ss
          ON (ss.segment_id = aseg.segment_id)
        JOIN segstack_%(segstack_id)s.slice s
          ON (s.id = ss.slice_id)
        WHERE a.equivalence_id = %(equivalence_id)s
        GROUP BY aseg.segment_id
        ''' % {'segstack_id': segstack.id, 'equivalence_id': equivalence_id})
    segments = cursor.fetchall()

    # Create an undirected graph of slices, connected by segments.
    g = nx.Graph()
    for segment in segments:
        slices = json.loads(segment[1])
        for slice in slices:
            g.add_node(slice['f1'], { # TODO: Does not handle orientation.
                    'x': slice['f2']*zoom*stack.resolution.x + ps.translation.x,
                    'y': slice['f3']*zoom*stack.resolution.y + ps.translation.y,
                    'z': slice['f4']*stack.resolution.z + ps.translation.z})
        for s1, s2 in itertools.combinations(slices, r=2):
            if s1['f5'] != s2['f5']: # Don't add edges between slices in same section
                g.add_edge(s1['f1'], s2['f1'])

    # Find a directed tree for mapping to a skeleton.
    if nx.number_of_nodes(g) > 1:
        # TODO: This discards cyclic edges in the graph, which SOPNET often creates.
        # These should be checked for and added back in with duplicate nodes.
        t = nx.bfs_tree(nx.minimum_spanning_tree(g), g.nodes()[0])
    else:
        t = nx.DiGraph()
        t.add_nodes_from(g)
    # Copy node attributes
    for n in t.nodes_iter():
        t.node[n] = g.node[n]

    return t

def generate_assembly_equivalences(segmentation_stack_id):
    """Mark assembly equivalences for compatible assemblies in the stack."""
    segmentation_stack_id = int(segmentation_stack_id)
    # Fetch all assemblies and the assemblies with which they are compatible
    # in the precedent solutions.
    cursor = connection.cursor()
    cursor.execute("""
        SELECT
          sola.assembly_id,
          ARRAY_TO_JSON(ARRAY_CAT(
              ARRAY_AGG(DISTINCT ar.assembly_a_id),
              ARRAY_AGG(DISTINCT ar.assembly_b_id)))
        FROM segstack_%(segstack_id)s.solution_precedence sp
        JOIN segstack_%(segstack_id)s.solution_assembly sola
          ON sola.solution_id = sp.solution_id
        LEFT JOIN segstack_%(segstack_id)s.assembly_relation ar
          ON (ar.assembly_a_id = sola.assembly_id OR ar.assembly_b_id = sola.assembly_id)
            AND ar.relation = 'Compatible'
        GROUP BY sola.assembly_id
        """ % {'segstack_id': segmentation_stack_id})
    assemblies = cursor.fetchall()

    # Create an undirected graph of assemblies, connected by compatibility. The
    # connected components of this graph are assembly equivalences.
    g = nx.Graph()
    for assembly in assemblies:
        g.add_node(assembly[0])
        for compatibility in json.loads(assembly[1]):
            if compatibility is not None:
                g.add_edge(assembly[0], compatibility)

    equivalence_ccs = nx.connected_components(g)
    equivalence_map = []
    assembly_ids = []
    for idx, equivalence_cc in enumerate(equivalence_ccs):
        for assembly in equivalence_cc:
            equivalence_map.append(idx)
            assembly_ids.append(assembly)

    # If no equivalences exist, do nothing.
    if not equivalence_map:
        return

    # Bulk create the number of assembly equivalences needed.
    cursor.execute('''
        INSERT INTO segstack_%(segstack_id)s.assembly_equivalence (skeleton_id)
        SELECT v.skeleton_id
        FROM (VALUES (NULL::integer))
          AS v (skeleton_id), generate_series(1, %(num_equivalences)s)
        RETURNING segstack_%(segstack_id)s.assembly_equivalence.id
        ''' % {'segstack_id': segmentation_stack_id, 'num_equivalences': len(equivalence_ccs)})
    equivalences = cursor.fetchall();
    equivalence_ids = [equivalences[idx][0] for idx in equivalence_map]

    # Bulk assign equivalences to assemblies.
    # NOTE: This query can hang Django's debug cursor wrapper. There is nothing
    # wrong with the query, apart from not being stupid enough for Django's
    # cursor wrapper. Disable the debug wrapper and it will work correctly.
    cursor.execute('''
        UPDATE segstack_%(segstack_id)s.assembly
        SET equivalence_id = equivalence_map.equivalence_id
        FROM (VALUES %(equivalence_map)s) AS equivalence_map (equivalence_id, assembly_id)
        WHERE segstack_%(segstack_id)s.assembly.id = equivalence_map.assembly_id
        ''' % {'segstack_id': segmentation_stack_id,
            'equivalence_map': ','.join(['(%s,%s)' % x for x in zip(equivalence_ids, assembly_ids)])})

def generate_compatible_assemblies_between_cores(segstack_id, core_a_id, core_b_id, run_prerequisites=True):
    """Create relations for compatible precedent assemblies between cores.

    Compatible assemblies have at least one continuation and no conflicts.

    If run_prerequisites is false, continuations and conflicts for this core
    pair should be generated first.
    """
    if run_prerequisites:
        generate_conflicting_assemblies_between_cores(segstack_id, core_a_id, core_b_id)
        generate_continuing_assemblies_between_cores(segstack_id, core_a_id, core_b_id)

    # Find compatibility and concurrency-safe upsert to assembly relations.
    # This could also be generated by EXCEPT instead of aggregation. Neither
    # approach was benchmarked.
    compatible_query = """
        SELECT ar.assembly_a_id, ar.assembly_b_id, 'Compatible'::assemblyrelation
        FROM segstack_%(segstack_id)s.assembly_relation ar
        JOIN segstack_%(segstack_id)s.solution_assembly sola_a ON sola_a.assembly_id = ar.assembly_a_id
        JOIN segstack_%(segstack_id)s.solution_assembly sola_b ON sola_b.assembly_id = ar.assembly_b_id
        JOIN segstack_%(segstack_id)s.solution_precedence sp_a ON sp_a.solution_id = sola_a.solution_id
        JOIN segstack_%(segstack_id)s.solution_precedence sp_b ON sp_b.solution_id = sola_b.solution_id
        WHERE (sp_a.core_id = %(core_a_id)s AND sp_b.core_id = %(core_b_id)s)
          OR (sp_a.core_id = %(core_b_id)s AND sp_b.core_id = %(core_a_id)s)
        GROUP BY ar.assembly_a_id, ar.assembly_b_id
        HAVING 'Continuation' = ANY(array_agg(ar.relation))
          AND NOT 'Conflict' = ANY(array_agg(ar.relation));
        """ % {'segstack_id': segstack_id, 'core_a_id': core_a_id, 'core_b_id': core_b_id}
    _generate_assembly_relation_between_cores(segstack_id, core_a_id, core_b_id, 'Compatible', compatible_query)

def generate_conflicting_assemblies_between_cores(segstack_id, core_a_id, core_b_id):
    """Create relations for conflicting precedent assemblies between cores.

    A conflict between assemblies is defined to be the existence of a
    conflict edge between slices in each assembly, OR that each assembly
    involves the same slice but via different segments in the same section. That
    is, conflicting assemblies contain conflicting slices or exclusive
    segments.
    """
    # Find conflicts and concurrency-safe upsert to assembly relations.
    conflict_query = """
        SELECT DISTINCT sola1.assembly_id, sola2.assembly_id, 'Conflict'::assemblyrelation
        FROM segstack_%(segstack_id)s.solution_precedence sp1
        JOIN segstack_%(segstack_id)s.solution_assembly sola1
          ON sola1.solution_id = sp1.solution_id
        JOIN segstack_%(segstack_id)s.assembly_segment aseg1
          ON aseg1.assembly_id = sola1.assembly_id
        JOIN segstack_%(segstack_id)s.segment_slice ss1 ON ss1.segment_id = aseg1.segment_id
        JOIN segstack_%(segstack_id)s.slice_conflict sc
          ON (sc.slice_a_id = ss1.slice_id OR sc.slice_b_id = ss1.slice_id)
        JOIN segstack_%(segstack_id)s.segment_slice ss2
          ON (((sc.slice_a_id = ss2.slice_id OR sc.slice_b_id = ss2.slice_id)
              AND ss1.slice_id <> ss2.slice_id) /* Conflicting slices */
            OR (ss1.slice_id = ss2.slice_id
                AND ss1.segment_id <> ss2.segment_id
                AND ss1.direction = ss2.direction)) /* Exclusive segments */
        JOIN segstack_%(segstack_id)s.assembly_segment aseg2
          ON aseg2.segment_id = ss2.segment_id
        JOIN segstack_%(segstack_id)s.solution_assembly sola2
          ON sola2.assembly_id = aseg2.assembly_id
        JOIN segstack_%(segstack_id)s.solution_precedence sp2 ON sp2.solution_id = sola2.solution_id
        WHERE sp1.core_id = %(core_a_id)s AND sp2.core_id = %(core_b_id)s;
        """ % {'segstack_id': segstack_id, 'core_a_id': core_a_id, 'core_b_id': core_b_id}
    _generate_assembly_relation_between_cores(segstack_id, core_a_id, core_b_id, 'Conflict', conflict_query)

def generate_continuing_assemblies_between_cores(segstack_id, core_a_id, core_b_id):
    """Create relations for continuing precedent assemblies between cores.

    A continuation is defined to be a shared slice.
    """
    # Find continuations and concurrency-safe upsert to assembly relations.
    continuation_query = """
        SELECT DISTINCT sola1.assembly_id, sola2.assembly_id, 'Continuation'::assemblyrelation
        FROM segstack_%(segstack_id)s.solution_precedence sp1
        JOIN segstack_%(segstack_id)s.solution_assembly sola1
          ON sola1.solution_id = sp1.solution_id
        JOIN segstack_%(segstack_id)s.assembly_segment aseg1
          ON aseg1.assembly_id = sola1.assembly_id
        JOIN segstack_%(segstack_id)s.segment_slice ss1 ON ss1.segment_id = aseg1.segment_id
        JOIN segstack_%(segstack_id)s.segment_slice ss2
          ON (ss2.slice_id = ss1.slice_id AND ss2.segment_id <> ss1.segment_id)
        JOIN segstack_%(segstack_id)s.assembly_segment aseg2
          ON aseg2.segment_id = ss2.segment_id
        JOIN segstack_%(segstack_id)s.solution_assembly sola2
          ON sola2.assembly_id = aseg2.assembly_id
        JOIN segstack_%(segstack_id)s.solution_precedence sp2 ON sp2.solution_id = sola2.solution_id
        WHERE sp1.core_id = %(core_a_id)s AND sp2.core_id = %(core_b_id)s;
        """ % {'segstack_id': segstack_id, 'core_a_id': core_a_id, 'core_b_id': core_b_id}
    _generate_assembly_relation_between_cores(segstack_id, core_a_id, core_b_id, 'Continuation', continuation_query)

def _generate_assembly_relation_between_cores(segstack_id, core_a_id, core_b_id, relation, relationship_query):
    cursor = connection.cursor()
    tmp_table_name = "segstack_%s_assembly_relation_tmp_%s_%s" % (segstack_id, core_a_id, core_b_id)
    # Find relationships and concurrency-safe upsert to assembly relations.
    cursor.execute("""
        BEGIN;

        CREATE TEMP TABLE %(tmp_table_name)s
          (LIKE segstack_%(segstack_id)s.assembly_relation) ON COMMIT DROP;
        ALTER TABLE %(tmp_table_name)s DROP COLUMN id;

        INSERT INTO %(tmp_table_name)s (assembly_a_id, assembly_b_id, relation)
        %(relationship_query)s

        LOCK TABLE segstack_%(segstack_id)s.assembly_relation IN EXCLUSIVE MODE;

        WITH core_assemblies AS (
            SELECT a.id AS assembly_id
            FROM segstack_%(segstack_id)s.assembly a
            WHERE a.core_id IN (%(core_a_id)s, %(core_b_id)s))
        DELETE FROM segstack_%(segstack_id)s.assembly_relation ar
        WHERE relation = '%(relation)s'::assemblyrelation
          AND (ar.assembly_a_id IN (SELECT assembly_id FROM core_assemblies) AND
               ar.assembly_b_id IN (SELECT assembly_id FROM core_assemblies));

        INSERT INTO segstack_%(segstack_id)s.assembly_relation
          (assembly_a_id, assembly_b_id, relation)
        SELECT t.assembly_a_id, t.assembly_b_id, t.relation
        FROM %(tmp_table_name)s AS t;

        COMMIT;
        """ % {'segstack_id': segstack_id,
                'core_a_id': core_a_id,
                'core_b_id': core_b_id,
                'relation': relation,
                'relationship_query': relationship_query,
                'tmp_table_name': tmp_table_name})
