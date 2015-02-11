import itertools
import json
import networkx as nx

from django.db import connection
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from catmaid.control.authentication import requires_user_role
from catmaid.control.skeleton import _import_skeleton
from catmaid.models import ProjectStack, Stack, UserRole
from djsopnet.models import AssemblyEquivalence, BlockInfo, Core

@requires_user_role(UserRole.Annotate)
def generate_assemblies_for_core(request, project_id=None, stack_id=None, core_id=None):
    c = get_object_or_404(Core, id=core_id)
    if not c.solution_set_flag:
        return HttpResponse(json.dumps(
                {'error': 'Solution flag is not set for core'}),
                status=409, content_type='application/json')

    _generate_assemblies_for_core(core_id)

    return HttpResponse(json.dumps({'ok' : True}), content_type='text/json')

def _generate_assemblies_for_core(core_id):
    """Create assemblies for the precedent solutino of a core.

    Assemblies are connected components in the segment graph of a solution.
    """
    cursor = connection.cursor()
    # Fetch the core's precedent solution ID.
    cursor.execute('''
        SELECT sp.solution_id
        FROM djsopnet_solutionprecedence sp
        WHERE sp.core_id = %s LIMIT 1
        ''' % core_id)
    solution_id = cursor.fetchone()[0]

    # Fetch all segments and the segments to which they are connected in the
    # core's precedent solution.
    cursor.execute('''
        SELECT
          ssol.segment_id AS segment_id,
          ARRAY_TO_JSON(ARRAY_AGG(DISTINCT ss2.segment_id)) AS segment_neighbors,
          ssol.id AS ssol_id
        FROM djsopnet_segmentsolution ssol
        JOIN djsopnet_segmentslice ss
          ON (ss.segment_id = ssol.segment_id)
        JOIN djsopnet_segmentslice ss2
          ON (ss2.slice_id = ss.slice_id
              AND ss2.segment_id <> ss.segment_id
              AND ss2.direction <> ss.direction)
        JOIN djsopnet_segmentsolution ssol2
          ON (ssol2.segment_id = ss2.segment_id AND ssol2.solution_id = ssol.solution_id)
        WHERE ssol.solution_id = %s
        GROUP BY ssol.segment_id, ssol.id
        ''' % solution_id)
    segments = cursor.fetchall()

    # Create an undirected graph of segments, connected by slice edges. The
    # connected components of this graph are assemblies.
    g = nx.Graph()
    for segment in segments:
        g.add_node(segment[0], {'ssol_id': segment[2]})
        for slice_edge in json.loads(segment[1]):
            g.add_edge(segment[0], slice_edge)

    assembly_ccs = nx.connected_components(g)
    assembly_map = []
    segmentsolution_ids = []
    for idx, assembly_cc in enumerate(assembly_ccs):
        for segment in assembly_cc:
            assembly_map.append(idx)
            segmentsolution_ids.append(g.node[segment]['ssol_id'])

    # Bulk create the number of assemblies needed.
    cursor.execute('''
        INSERT INTO djsopnet_assembly (solution_id)
        SELECT v.solution_id
        FROM (VALUES (%(solution_id)s))
          AS v (solution_id), generate_series(1, %(num_assemblies)s)
        RETURNING djsopnet_assembly.id
        ''' % {'solution_id': solution_id,
               'num_assemblies': len(assembly_ccs)})
    assemblies = cursor.fetchall();
    assembly_ids = [assemblies[idx][0] for idx in assembly_map]

    # Bulk assign assemblies to SegmentSolutions.
    # NOTE: This query can hang Django's debug cursor wrapper. There is nothing
    # wrong with the query, apart from not being stupid enough for Django's
    # cursor wrapper. Disable the debug wrapper and it will work correctly.
    cursor.execute('''
        UPDATE djsopnet_segmentsolution
        SET assembly_id = assembly_map.assembly_id
        FROM (VALUES %s) AS assembly_map (assembly_id, ssol_id)
        WHERE djsopnet_segmentsolution.id = assembly_map.ssol_id
        ''' % ','.join(['(%s,%s)' % x for x in zip(assembly_ids, segmentsolution_ids)]))

@requires_user_role(UserRole.Annotate)
def map_assembly_equivalence_to_skeleton(request, project_id, stack_id, equivalence_id):
    ae = get_object_or_404(AssemblyEquivalence, id=equivalence_id)

    _map_assembly_equivalence_to_skeleton(request, project_id, equivalence_id)

    return HttpResponse(json.dumps({'ok' : True}), content_type='text/json')

def _map_assembly_equivalence_to_skeleton(request, project_id, equivalence_id):
    # Check that this equivalence is populated with segments.
    cursor = connection.cursor()
    cursor.execute('''
        SELECT count(ssol.id) FROM djsopnet_segmentsolution ssol
        JOIN djsopnet_assembly a ON a.id = ssol.assembly_id
        WHERE a.equivalence_id = %s
        ''' % equivalence_id)
    segment_count = cursor.fetchone()[0]
    if segment_count == 0:
        return

    arborescence = map_assembly_equivalence_to_arborescence(equivalence_id, project_id)
    imported_skeleton = _import_skeleton(request, project_id, arborescence,
            name='AssemblyEquivalence %s' % equivalence_id)

    # Set the mapped skeleton ID for this AssemblyEquivalence.
    cursor.execute('''
        UPDATE djsopnet_assemblyequivalence
        SET skeleton_id = %s
        WHERE id = %s
        ''' % (imported_skeleton['skeleton_id'], equivalence_id))

    # TODO: annotate neurons to indicate they are mapped.

    # Generate tuple string for slice ID -> treenode ID.
    tn_slice_values = \
            '),('.join([','.join(map(str, (n[0], n[1]['id']))) \
            for n in imported_skeleton['graph'].nodes_iter(data=True)])
    cursor.execute('''
        INSERT INTO djsopnet_treenodeslice (slice_id, treenode_id)
        VALUES (%s)
        ''' % tn_slice_values)

def map_assembly_equivalence_to_arborescence(equivalence_id, project_id):
    """Create skeletons for existing equivalences and map nodes to slices."""
    equivalence_id = int(equivalence_id)
    project_id = int(project_id)
    cursor = connection.cursor()
    cursor.execute('''
        SELECT c.stack_id
        FROM djsopnet_assembly a
        JOIN djsopnet_solution sol ON sol.id = a.solution_id
        JOIN djsopnet_core c ON c.id = sol.core_id
        WHERE a.equivalence_id = %s
        LIMIT 1
        ''' % equivalence_id)
    stack_id = cursor.fetchone()[0]

    # TODO: After the CATSOP stack-schema refactor project_id will be unnecessary.
    ps = ProjectStack.objects.get(stack_id=stack_id, project_id=project_id)
    stack = Stack.objects.get(id=stack_id)
    bi = BlockInfo.objects.get(stack_id=stack_id)
    zoom = 2**bi.scale

    # Fetch all segments and their slices in equivalence.
    cursor.execute('''
        SELECT
          ssol.segment_id AS segment_id,
          JSON_AGG(DISTINCT ROW(s.id, s.ctr_x, s.ctr_y, s.section, ss.direction)) AS segment_slices
        FROM djsopnet_segmentsolution ssol
        JOIN djsopnet_assembly a
          ON (ssol.assembly_id = a.id)
        JOIN djsopnet_segmentslice ss
          ON (ss.segment_id = ssol.segment_id)
        JOIN djsopnet_slice s
          ON (s.id = ss.slice_id)
        WHERE a.equivalence_id = %s
        GROUP BY ssol.segment_id
        ''' % equivalence_id)
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
    # TODO: This discards cyclic edges in the graph, which SOPNET often creates.
    # These should be checked for and added back in with duplicate nodes.
    t = nx.bfs_tree(nx.minimum_spanning_tree(g), g.nodes()[0])
    # Copy node attributes
    for n in t.nodes_iter():
        t.node[n] = g.node[n]

    return t

def generate_assembly_equivalences(stack_id):
    """Mark assembly equivalences for compatible assemblies in the stack."""
    stack_id = int(stack_id)
    # Fetch all assemblies and the assemblies with which they are compatible
    # in the precedent solutions.
    cursor = connection.cursor()
    cursor.execute("""
        SELECT
          a.id,
          ARRAY_TO_JSON(ARRAY_CAT(
              ARRAY_AGG(DISTINCT ar.assembly_a_id),
              ARRAY_AGG(DISTINCT ar.assembly_b_id)))
        FROM djsopnet_solutionprecedence sp
        JOIN djsopnet_core c ON (c.id = sp.core_id AND c.stack_id = %s)
        JOIN djsopnet_assembly a ON (a.solution_id = sp.solution_id)
        JOIN djsopnet_assemblyrelation ar
          ON (ar.assembly_a_id = a.id OR ar.assembly_b_id = a.id)
            AND ar.relation = 'Compatible'
        GROUP BY a.id
        """ % stack_id)
    assemblies = cursor.fetchall()

    # Create an undirected graph of assemblies, connected by compatibility. The
    # connected components of this graph are assembly equivalences.
    g = nx.Graph()
    for assembly in assemblies:
        g.add_node(assembly[0])
        for compatibility in json.loads(assembly[1]):
            g.add_edge(assembly[0], compatibility)

    equivalence_ccs = nx.connected_components(g)
    equivalence_map = []
    assembly_ids = []
    for idx, equivalence_cc in enumerate(equivalence_ccs):
        for assembly in equivalence_cc:
            equivalence_map.append(idx)
            assembly_ids.append(assembly)

    # Bulk create the number of assembly equivalences needed.
    cursor.execute('''
        INSERT INTO djsopnet_assemblyequivalence (skeleton_id)
        SELECT v.skeleton_id
        FROM (VALUES (NULL::integer))
          AS v (skeleton_id), generate_series(1, %(num_equivalences)s)
        RETURNING djsopnet_assemblyequivalence.id
        ''' % {'num_equivalences': len(equivalence_ccs)})
    equivalences = cursor.fetchall();
    equivalence_ids = [equivalences[idx][0] for idx in equivalence_map]

    # Bulk assign equivalences to assemblies.
    # NOTE: This query can hang Django's debug cursor wrapper. There is nothing
    # wrong with the query, apart from not being stupid enough for Django's
    # cursor wrapper. Disable the debug wrapper and it will work correctly.
    cursor.execute('''
        UPDATE djsopnet_assembly
        SET equivalence_id = equivalence_map.equivalence_id
        FROM (VALUES %s) AS equivalence_map (equivalence_id, assembly_id)
        WHERE djsopnet_assembly.id = equivalence_map.assembly_id
        ''' % ','.join(['(%s,%s)' % x for x in zip(equivalence_ids, assembly_ids)]))

def generate_compatible_assemblies_between_cores(core_a_id, core_b_id, run_prerequisites=True):
    """Create relations for compatible precedent assemblies between cores.

    Compatible assemblies have at least one continuation and no conflicts.

    If run_prerequisites is false, continuations and conflicts for this core
    pair should be generated first.
    """
    if run_prerequisites:
        generate_conflicting_assemblies_between_cores(core_a_id, core_b_id)
        generate_continuing_assemblies_between_cores(core_a_id, core_b_id)

    # Find compatibility and concurrency-safe upsert to assembly relations.
    # This could also be generated by EXCEPT instead of aggregation. Neither
    # approach was benchmarked.
    compatible_query = """
        SELECT ar.assembly_a_id, ar.assembly_b_id, 'Compatible'::assemblyrelation
        FROM djsopnet_assemblyrelation ar
        JOIN djsopnet_assembly a_a ON a_a.id = ar.assembly_a_id
        JOIN djsopnet_assembly a_b ON a_b.id = ar.assembly_b_id
        JOIN djsopnet_solutionprecedence sp_a ON sp_a.solution_id = a_a.solution_id
        JOIN djsopnet_solutionprecedence sp_b ON sp_b.solution_id = a_b.solution_id
        WHERE (sp_a.core_id = %(core_a_id)s AND sp_b.core_id = %(core_b_id)s)
          OR (sp_a.core_id = %(core_b_id)s AND sp_b.core_id = %(core_a_id)s)
        GROUP BY ar.assembly_a_id, ar.assembly_b_id
        HAVING 'Continuation' = ANY(array_agg(ar.relation))
          AND NOT 'Conflict' = ANY(array_agg(ar.relation));
        """ % {'core_a_id': core_a_id, 'core_b_id': core_b_id}
    _generate_assembly_relation_between_cores(core_a_id, core_b_id, 'Compatible', compatible_query)

def generate_conflicting_assemblies_between_cores(core_a_id, core_b_id):
    """Create relations for conflicting precedent assemblies between cores.

    A conflict between assemblies is defined to be the existence of a
    conflict edge between slices in each assembly, OR that each assembly
    involves the same slice but via different segments in the same section. That
    is, conflicting assemblies contain conflicting slices or exclusive
    segments.
    """
    # Find conflicts and concurrency-safe upsert to assembly relations.
    conflict_query = """
        SELECT DISTINCT ssol1.assembly_id, ssol2.assembly_id, 'Conflict'::assemblyrelation
        FROM djsopnet_solutionprecedence sp1
        JOIN djsopnet_segmentsolution ssol1
          ON (ssol1.solution_id = sp1.solution_id AND ssol1.assembly_id IS NOT NULL)
        JOIN djsopnet_segmentslice ss1 ON ss1.segment_id = ssol1.segment_id
        JOIN djsopnet_sliceconflict sc
          ON (sc.slice_a_id = ss1.slice_id OR sc.slice_b_id = ss1.slice_id)
        JOIN djsopnet_segmentslice ss2
          ON (((sc.slice_a_id = ss2.slice_id OR sc.slice_b_id = ss2.slice_id)
              AND ss1.slice_id <> ss2.slice_id) /* Conflicting slices */
            OR (ss1.slice_id = ss2.slice_id
                AND ss1.segment_id <> ss2.segment_id
                AND ss1.direction = ss2.direction)) /* Exclusive segments */
        JOIN djsopnet_segmentsolution ssol2
          ON (ssol2.segment_id = ss2.segment_id AND ssol2.assembly_id IS NOT NULL)
        JOIN djsopnet_solutionprecedence sp2 ON sp2.solution_id = ssol2.solution_id
        WHERE sp1.core_id = %(core_a_id)s AND sp2.core_id = %(core_b_id)s;
        """ % {'core_a_id': core_a_id, 'core_b_id': core_b_id}
    _generate_assembly_relation_between_cores(core_a_id, core_b_id, 'Conflict', conflict_query)

def generate_continuing_assemblies_between_cores(core_a_id, core_b_id):
    """Create relations for continuing precedent assemblies between cores.

    A continuation is defined to be a shared slice.
    """
    # Find continuations and concurrency-safe upsert to assembly relations.
    continuation_query = """
        SELECT DISTINCT ssol1.assembly_id, ssol2.assembly_id, 'Continuation'::assemblyrelation
        FROM djsopnet_solutionprecedence sp1
        JOIN djsopnet_segmentsolution ssol1
          ON (ssol1.solution_id = sp1.solution_id AND ssol1.assembly_id IS NOT NULL)
        JOIN djsopnet_segmentslice ss1 ON ss1.segment_id = ssol1.segment_id
        JOIN djsopnet_segmentslice ss2
          ON (ss2.slice_id = ss1.slice_id AND ss2.id <> ss1.id)
        JOIN djsopnet_segmentsolution ssol2
          ON (ssol2.segment_id = ss2.segment_id AND ssol2.assembly_id IS NOT NULL)
        JOIN djsopnet_solutionprecedence sp2 ON sp2.solution_id = ssol2.solution_id
        WHERE sp1.core_id = %(core_a_id)s AND sp2.core_id = %(core_b_id)s;
        """ % {'core_a_id': core_a_id, 'core_b_id': core_b_id}
    _generate_assembly_relation_between_cores(core_a_id, core_b_id, 'Continuation', continuation_query)

def _generate_assembly_relation_between_cores(core_a_id, core_b_id, relation, relationship_query):
    cursor = connection.cursor()
    tmp_table_name = "djsopnet_assemblyrelation_tmp_%s_%s" % (core_a_id, core_b_id)
    # Find relationships and concurrency-safe upsert to assembly relations.
    cursor.execute("""
        BEGIN;

        CREATE TEMP TABLE %(tmp_table_name)s
          (LIKE djsopnet_assemblyrelation) ON COMMIT DROP;
        ALTER TABLE %(tmp_table_name)s DROP COLUMN id;

        INSERT INTO %(tmp_table_name)s (assembly_a_id, assembly_b_id, relation)
        %(relationship_query)s

        LOCK TABLE djsopnet_assemblyrelation IN EXCLUSIVE MODE;

        DELETE FROM djsopnet_assemblyrelation ar
        WHERE relation = '%(relation)s'::assemblyrelation
          AND EXISTS (
            SELECT 1 FROM djsopnet_solution s
            JOIN djsopnet_assembly a
              ON (a.solution_id = s.id AND a.id = ar.assembly_a_id)
            WHERE s.core_id = %(core_a_id)s OR s.core_id = %(core_b_id)s)
          AND EXISTS (
            SELECT 1 FROM djsopnet_solution s
            JOIN djsopnet_assembly a
              ON (a.solution_id = s.id AND a.id = ar.assembly_b_id)
            WHERE s.core_id = %(core_a_id)s OR s.core_id = %(core_b_id)s);

        INSERT INTO djsopnet_assemblyrelation
          (assembly_a_id, assembly_b_id, relation)
        SELECT t.assembly_a_id, t.assembly_b_id, t.relation
        FROM %(tmp_table_name)s AS t;

        COMMIT;
        """ % {'core_a_id': core_a_id,
                'core_b_id': core_b_id,
                'relation': relation,
                'relationship_query': relationship_query,
                'tmp_table_name': tmp_table_name})
