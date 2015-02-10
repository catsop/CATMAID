import json
import networkx as nx

from django.db import connection

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
    compatible_query = """
        SELECT ar.assembly_a_id, ar.assembly_b_id, 'Compatible'::assemblyrelation
        FROM djsopnet_assemblyrelation ar
        JOIN djsopnet_assembly a
          ON (a.id = ar.assembly_a_id OR a.id = ar.assembly_b_id)
        JOIN djsopnet_solutionprecedence sp ON sp.solution_id = a.solution_id
        WHERE sp.core_id = %s OR sp.core_id = %s
        GROUP BY ar.assembly_a_id, ar.assembly_b_id
        HAVING 'Continuation' = ALL(array_agg(ar.relation));
        """ % (core_a_id, core_b_id)
    _generate_assembly_relation_between_cores(core_a_id, core_b_id, compatible_query)

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
    _generate_assembly_relation_between_cores(core_a_id, core_b_id, conflict_query)

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
    _generate_assembly_relation_between_cores(core_a_id, core_b_id, continuation_query)

def _generate_assembly_relation_between_cores(core_a_id, core_b_id, relationship_query):
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

        INSERT INTO djsopnet_assemblyrelation
          (assembly_a_id, assembly_b_id, relation)
        SELECT t.assembly_a_id, t.assembly_b_id, t.relation
        FROM %(tmp_table_name)s AS t
        LEFT OUTER JOIN djsopnet_assemblyrelation a
          ON ((a.assembly_a_id, a.assembly_b_id, a.relation) =
              (t.assembly_a_id, t.assembly_b_id, t.relation))
        WHERE a.id IS NULL;

        COMMIT;
        """ % {'relationship_query': relationship_query, 'tmp_table_name': tmp_table_name})
