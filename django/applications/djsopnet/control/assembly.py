import json
import networkx as nx

from django.db import connection

def find_compatible_assemblies_between_cores(core_a_id, core_b_id):
    """Returns an array of assembly ID tuples, where for each tuple the
    members are assembly IDs for precedent solutions from core_a and core_b,
    respectively, and the two assemblies in the tuple have at least one
    continuation and no conflicts. A continuation is defined to be a shared
    slice. A conflict between assemblies is defined to be the existence of a
    conflict edge between slices in each assembly, OR that each assembly
    involves the same slice but via different segments in the same section. That
    is, conflicting assemblies contain conflicting slices or exclusive
    segments."""

    cursor = connection.cursor()
    cursor.execute("""
        SELECT DISTINCT ssol1.assembly_id, ssol2.assembly_id
        FROM djsopnet_solutionprecedence sp1
        JOIN djsopnet_segmentsolution ssol1
          ON (ssol1.solution_id = sp1.solution_id AND ssol1.assembly_id IS NOT NULL)
        JOIN djsopnet_segmentslice ss1 ON ss1.segment_id = ssol1.segment_id
        JOIN djsopnet_segmentslice ss2
          ON (ss2.slice_id = ss1.slice_id AND ss2.id <> ss1.id)
        JOIN djsopnet_segmentsolution ssol2
          ON (ssol2.segment_id = ss2.segment_id AND ssol2.assembly_id IS NOT NULL)
        JOIN djsopnet_solutionprecedence sp2 ON sp2.solution_id = ssol2.solution_id
        WHERE sp1.core_id = %s AND sp2.core_id = %s
        """ % (core_a_id, core_b_id))
    assembly_continuations = frozenset(cursor.fetchall())

    cursor.execute("""
        SELECT DISTINCT ssol1.assembly_id, ssol2.assembly_id
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
        WHERE sp1.core_id = %s AND sp2.core_id = %s
        """ % (core_a_id, core_b_id))
    assembly_conflicts = frozenset(cursor.fetchall())

    return assembly_continuations - assembly_conflicts
