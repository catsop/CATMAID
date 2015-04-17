import json
from collections import namedtuple

import pysopnet

from django.db import connection
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404

from catmaid.models import UserRole
from catmaid.control.authentication import requires_user_role

from djsopnet.control.common import error_response, safe_split, hash_to_id, id_to_hash
from djsopnet.control.slice import slice_dict, _retrieve_slices_by_ids, \
        _slicecursor_to_namedtuple, _slice_select_query
from djsopnet.models import SegmentationStack


def segment_dict(segment, with_solution=False):
    sd = {'hash': id_to_hash(segment.id),
          'section': segment.section_sup,
          'box': [segment.min_x, segment.min_y, segment.max_x, segment.max_y],
          'ctr': [segment.ctr_x, segment.ctr_y],
          'type': segment.type}

    if with_solution:
        sd['in_solution'] = segment.in_solution

    return sd


def generate_segment_response(segment):
    if segment:
        return HttpResponse(json.dumps(segment_dict(segment)), content_type='text/json')
    else:
        return HttpResponse(json.dumps({'id': None}), content_type='text/json')


def generate_segments_response(segments, with_solutions=False):
    segment_list = [segment_dict(segment, with_solutions) for segment in segments]
    return HttpResponse(json.dumps({'ok': True, 'segments': segment_list}), content_type='text/json')


def generate_features_response(features):
    features_dicts = []
    for feature in features:
        segment_hash = id_to_hash(feature.segment_id)
        feature_values = feature.features
        features_dicts.append({'hash': segment_hash, 'fv': feature_values})
    return HttpResponse(json.dumps({'ok': True, 'features': features_dicts}), content_type='text/json')


# --- Segments ---
def setup_feature_names(names, stack, project):
    try:
        FeatureInfo.objects.get(stack=stack)
        return False
    except FeatureInfo.DoesNotExist:
        ids = []
        for name in names:
            feature_name = FeatureName(name=name)
            feature_name.save()
            ids.append(feature_name.id)
        info = FeatureInfo(stack=stack, name_ids=ids, size=len(ids))
        info.save()
        return True


def get_feature_names(stack, project):
    # get feature names, if they exist.
    # throws FeatureNameInfo.DoesNotExist, and possibly FeatureNameInfo.MultipleObjectsReturned
    feature_info = FeatureInfo.objects.get(stack=stack)
    keys = feature_info.name_ids
    feature_name_objects = FeatureName.objects.filter(id__in=keys)
    feature_names = []
    # ensure that the order of the feature_names list corresponds to that of keys
    for id in keys:
        for fno in feature_name_objects:
            if fno.id == id:
                feature_names.append(fno.name)
    return feature_names


def _segmentcursor_to_namedtuple(cursor):
    """Create a namedtuple list stubbing for Segment objects from a cursor.

    Assumes the cursor has been executed and has at least the following columns:
    in_solution_core_ids.
    """
    cols = [col[0] for col in cursor.description]

    SegmentTuple = namedtuple('SegmentTuple', cols)

    def segmentrow_to_namedtuple(row):
        rowdict = dict(zip(cols, row))
        # In PostgreSQL 9.4 it will be possible to preserve column names in JSON
        # aggregated ROW columns without subqueries or CTEs. For now manually
        # map from default field names to original column names.
        rowdict.update({
                'in_solution': dict([
                    (solution['f1'], solution['f2'])
                    for solution in json.loads(rowdict['in_solution'])
                ])
            })
        if not any(rowdict['in_solution'].keys()):
            rowdict['in_solution'] = False
        return SegmentTuple(**rowdict)

    return [segmentrow_to_namedtuple(row) for row in cursor.fetchall()]


def _segment_select_query(segmentation_stack_id, segment_id_query):
    """Build a querystring to select segments given an ID query.

    Keyword arguments:
    segment_id_query -- A string SELECT statement returning a segment_id column
    """
    return '''
            SELECT
              s.id, s.section_sup,
              s.min_x, s.min_y, s.max_x, s.max_y,
              s.ctr_x, s.ctr_y, s.type, s.cost,
              ARRAY_TO_JSON(ARRAY_AGG(DISTINCT ROW(ssol.solution_id, ssol.assembly_id))) AS in_solution
            FROM segstack_%(segstack_id)s.segment s
            JOIN (%(segment_id_query)s) AS segment_id_query
              ON (segment_id_query.segment_id = s.id)
            LEFT JOIN
              (SELECT ssol.segment_id, ssol.solution_id, ssol.assembly_id, sp.core_id
                  FROM segstack_%(segstack_id)s.segment_solution ssol
                  JOIN segstack_%(segstack_id)s.solution_precedence sp ON sp.solution_id = ssol.solution_id)
              AS ssol
                ON (ssol.segment_id = s.id)
            GROUP BY s.id
            ''' % {'segstack_id': segmentation_stack_id, 'segment_id_query': segment_id_query}


def _retrieve_segments_by_ids(segmentation_stack_id, segment_ids):
    segments = []
    if segment_ids:
        cursor = connection.cursor()
        cursor.execute(_segment_select_query(
                segmentation_stack_id, '''
                SELECT * FROM (VALUES (%s)) AS t (segment_id)
                ''' % '),('.join(map(str, segment_ids))))

        segments = _segmentcursor_to_namedtuple(cursor)

    return segments


def retrieve_segment_and_conflicts(request, project_id, segmentation_stack_id):
    """
    Retrieve a segment (or set of co-section conflicting segments), its slices,
    their first-order conflict slices, and segments involving these slices in
    the same section.
    """
    segstack = get_object_or_404(SegmentationStack, pk=segmentation_stack_id)
    try:
        segment_id = ','.join([str(hash_to_id(x)) for x in safe_split(request.POST.get('hash'), 'segment hashes')])

        cursor = connection.cursor()
        cursor.execute(('''
                WITH req_seg_slices AS (
                    SELECT slice_id FROM segstack_%(segstack_id)s.segment_slice
                      WHERE segment_id IN (%(segment_id)s))
                ''' % {'segstack_id': segmentation_stack_id, 'segment_id': segment_id}) + \
                _slice_select_query(segmentation_stack_id, '''
                        SELECT ss2.slice_id
                            FROM segstack_%(segstack_id)s.segment_slice ss1
                            JOIN segstack_%(segstack_id)s.segment ss1_seg
                                ON (ss1.segment_id = ss1_seg.id
                                    AND ss1_seg.section_sup = (
                                        SELECT section_sup FROM segstack_%(segstack_id)s.segment
                                        WHERE id IN (%(segment_id)s) LIMIT 1))
                            JOIN segstack_%(segstack_id)s.segment_slice ss2
                                ON (ss2.segment_id = ss1.segment_id)
                            WHERE ss1.slice_id IN
                                (SELECT slice_id FROM req_seg_slices
                                UNION SELECT scs_a.slice_a_id AS slice_id
                                  FROM segstack_%(segstack_id)s.slice_conflict scs_a, req_seg_slices
                                  WHERE scs_a.slice_b_id = req_seg_slices.slice_id
                                UNION SELECT scs_b.slice_b_id AS slice_id
                                  FROM segstack_%(segstack_id)s.slice_conflict scs_b, req_seg_slices
                                  WHERE scs_b.slice_a_id = req_seg_slices.slice_id)
                        ''' % {'segstack_id': segmentation_stack_id, 'segment_id': segment_id}))

        slices = _slicecursor_to_namedtuple(cursor)

        expanded_segment_ids = sum([
            [summary['segment_id'] for summary in slice.segment_summaries]
            for slice in slices if slice.segment_summaries], [])

        segments = _retrieve_segments_by_ids(segstack.id, expanded_segment_ids)

        segment_list = [segment_dict(segment, with_solution=True) for segment in segments]
        slices_list = [slice_dict(slice, with_conflicts=True, with_solution=True) for slice in slices or conflict_slices]
        return HttpResponse(json.dumps({'ok': True, 'segments': segment_list, 'slices': slices_list}), content_type='text/json')
    except:
        return error_response()


def set_feature_names(request, project_id=None, stack_id=None):
    s = get_object_or_404(Stack, pk=stack_id)
    p = get_object_or_404(Project, pk=project_id)
    names = []

    try:
        names = safe_split(request.POST.get('names'), 'names')

        existing_names = get_feature_names(s, p)
        if existing_names == names:
            return HttpResponse(json.dumps({'ok': True}), content_type='text/json')
        else:
            return HttpResponse(json.dumps({'ok': False,
                                            'reason' : 'tried to set different feature names'}),
                                content_type='text/json')
    except FeatureInfo.DoesNotExist:
        if setup_feature_names(names, s, p):
            return HttpResponse(json.dumps({'ok': True}), content_type='text/json')
        else:
            return HttpResponse(json.dumps({'ok': False,
                                            'reason' : 'something went horribly, horribly awry'}),
                                content_type='text/json')
    except:
        return error_response()


def retrieve_feature_names(request, project_id=None, stack_id=None):
    s = get_object_or_404(Stack, pk=stack_id)
    p = get_object_or_404(Project, pk=project_id)
    names = get_feature_names(s, p)
    return HttpResponse(json.dumps({'names': names}), content_type='text/json')


def get_segment_features(request, project_id=None, stack_id=None):
    s = get_object_or_404(Stack, pk=stack_id)
    try:
        segment_ids = map(hash_to_id, safe_split(request.POST.get('hash'), 'segment hashes'))
        features = SegmentFeatures.objects.filter(segment__in=segment_ids)
        return generate_features_response(features)
    except:
        return error_response()


def retrieve_segment_solutions(request, project_id=None, stack_id=None):
    try:
        segment_ids = map(hash_to_id, safe_split(request.POST.get('hash'), 'segment hashes'))
        core_id = int(request.POST.get('core_id'))
        solutions = SegmentSolution.objects.filter(core_id=core_id, segment__in=segment_ids)

        solution_dicts = [{'hash': id_to_hash(solution.segment.id),
                           'solution': solution.solution} for solution in solutions]

        return HttpResponse(json.dumps({'ok': True, 'solutions': solution_dicts}),
                            content_type='text/json')
    except:
        return error_response()


def retrieve_block_ids_by_segments(request, project_id=None, stack_id=None):
    s = get_object_or_404(Stack, pk=stack_id)
    try:
        segment_ids = map(hash_to_id, safe_split(request.POST.get('hash'), 'segment hashes'))

        segments = Segment.objects.filter(stack=s, id__in=segment_ids)
        block_relations = SegmentBlockRelation.objects.filter(segment__in=segments)
        blocks = {br.block for br in block_relations}
        block_ids = [block.id for block in blocks]

        return HttpResponse(json.dumps({'ok': True, 'block_ids': block_ids}), content_type='text/json')
    except:
        return error_response()


@requires_user_role(UserRole.Annotate)
def create_segment_for_slices(request, project_id, segmentation_stack_id):
    """Creates a segment joining a specified set of slices. Ends must specify section supremum."""
    segstack = get_object_or_404(SegmentationStack, pk=segmentation_stack_id)
    try:
        slice_ids = map(hash_to_id, safe_split(request.POST.get('hash'), 'slice hashes'))
        if len(slice_ids) == 0:
            return HttpResponseBadRequest(json.dumps({'error': 'Must specify at least one slices for a segment'}), content_type='application/json')

        slices = _retrieve_slices_by_ids(segmentation_stack_id, slice_ids)
        if len(slices) != len(slice_ids):
            return HttpResponseBadRequest(json.dumps({'error': 'Segment refers to non-existent slices'}), content_type='application/json')

        sections = [x.section for x in slices]
        section_span = max(sections) - min(sections)
        if section_span > 1:
            return HttpResponseBadRequest(json.dumps({'error': 'Slices must be in adjacent sections'}))
        if section_span == 0 and len(slices) > 1:
            return HttpResponseBadRequest(json.dumps({'error': 'End segments must contain exactly one slice'}), content_type='application/json')
        if len(slices) > 3:
            return HttpResponseBadRequest(json.dumps({'error': 'SOPNET only supports branches of 1:2 slices'}), content_type='application/json')

        # Set segment section_sup
        #   If continuation or branch, should be max(sections)
        #   If an end, should be request param, otherwise 400
        section_sup = max(sections)
        if len(slices) == 1:
            section_sup = request.POST.get('section_sup', None)
            if section_sup is None:
                return HttpResponseBadRequest(json.dumps({'error': 'End segments must specify section supremum'}), content_type='application/json')

        # Set segment extents extrema of slice extents
        min_x = min([x.min_x for x in slices])
        min_y = min([x.min_y for x in slices])
        max_x = min([x.max_x for x in slices])
        max_y = min([x.max_y for x in slices])

        # Set segment centroid as center of extents (not identical to Sopnet's method)
        ctr_x = (min_x + max_x) / 2
        ctr_y = (min_y + max_y) / 2

        # Get segment hash from SOPNET
        leftSliceHashes = pysopnet.SliceHashVector()
        leftSliceHashes.extend([long(id_to_hash(x.id)) for x in slices if x.section != section_sup])
        rightSliceHashes = pysopnet.SliceHashVector()
        rightSliceHashes.extend([long(id_to_hash(x.id)) for x in slices if x.section == section_sup])
        segment_hash = pysopnet.segmentHashValue(leftSliceHashes, rightSliceHashes)
        segment_id = hash_to_id(segment_hash)

        cursor = connection.cursor()
        cursor.execute('SELECT 1 FROM segstack_%s.segment WHERE id = %s LIMIT 1' % (segstack.id, segment_id))
        if cursor.rowcount > 0:
            return HttpResponse(json.dumps(
                    {'error': 'Segment already exists with hash: %s id: %s' % (segment_hash, segment_id)}),
                    status=409, content_type='application/json')

        type = len(slices) - 1
        # Create segment, associate slices to segment, and associate segment to blocks
        cursor.execute('''
                INSERT INTO segstack_%(segstack_id)s.segment
                (id, section_sup, type, ctr_x, ctr_y, min_x, min_y, max_x, max_y) VALUES
                (%(segment_id)s, %(section_sup)s, %(type)s, %(ctr_x)s, %(ctr_y)s,
                    %(min_x)s, %(min_y)s, %(max_x)s, %(max_y)s);

                INSERT INTO segstack_%(segstack_id)s.segment_slice
                (segment_id, slice_id, direction)
                SELECT seg.id, slice.id, slice.section <> %(section_sup)s
                FROM (VALUES (%(segment_id)s)) AS seg (id),
                (SELECT id, section FROM segstack_%(segstack_id)s.slice
                    WHERE id IN (%(slice_ids)s)) AS slice (id);

                INSERT INTO segstack_%(segstack_id)s.segment_block_relation
                (segment_id, block_id)
                SELECT seg.id, sbr.block_id
                FROM (VALUES (%(segment_id)s)) AS seg (id),
                (SELECT DISTINCT block_id FROM segstack_%(segstack_id)s.slice_block_relation
                    WHERE slice_id IN (%(slice_ids)s)) AS sbr;
                ''' % {'segstack_id': segstack.id, 'segment_id': segment_id,
                    'section_sup': section_sup, 'type': type,
                    'ctr_x': ctr_x, 'ctr_y': ctr_y,
                    'min_x': min_x, 'min_y': min_y,
                    'max_x': max_x, 'max_y': max_y,
                    'slice_ids': ','.join(map(str, slice_ids))})

        segment = _retrieve_segments_by_ids(segmentation_stack_id, [segment_id])[0]

        return generate_segment_response(segment)
    except:
        return error_response()


@requires_user_role(UserRole.Annotate)
def constrain_segment(request, project_id, segmentation_stack_id, segment_hash):
    segstack = get_object_or_404(SegmentationStack, pk=segmentation_stack_id)
    try:
        segment_id = hash_to_id(segment_hash)

        cursor = connection.cursor()
        cursor.execute('SELECT 1 FROM segstack_%s.segment WHERE id = %s LIMIT 1' % (segstack.id, segment_id))
        if cursor.rowcount == 0:
            raise Http404('No segment exists with hash: %s id: %s' % (segment_hash, segment_id))

        cursor.execute('''
                WITH solconstraint AS (
                    INSERT INTO segstack_%(segstack_id)s.solution_constraint
                        (user_id, relation, value, creation_time, edition_time) VALUES
                        (%(user_id)s, 'Equal', 1.0, current_timestamp, current_timestamp)
                        RETURNING id)
                INSERT INTO segstack_%(segstack_id)s.constraint_segment_relation
                    (segment_id, constraint_id, coefficient)
                    (SELECT segment.id, solconstraint.id, 1.0
                        FROM (VALUES (%(segment_id)s)) AS segment (id), solconstraint)
                    RETURNING constraint_id;
                ''' % {'segstack_id': segstack.id, 'segment_id': segment_id, 'user_id': request.user.id})
        constraint_id = cursor.fetchone()[0]

        cursor.execute('''
            INSERT INTO segstack_%(segstack_id)s.block_constraint_relation
                (constraint_id, block_id)
                (SELECT solconstraint.id, sbr.block_id
                    FROM (VALUES (%(constraint_id)s)) AS solconstraint (id),
                    (SELECT block_id FROM segstack_%(segstack_id)s.segment_block_relation
                        WHERE segment_id = %(segment_id)s) AS sbr);
            ''' % {'segstack_id': segstack.id, 'segment_id': segment_id, 'constraint_id': constraint_id})

        # Mark explicitly conflicting segments (segments with slices in conflict
        # sets with the constrained segment, or segments in the same section
        # with slices in common with the constrained segment) as mistakes being
        # corrected. The latter condition is needed to mark end segments, which
        # may not involve a conflicting slice.
        cursor.execute('''
            WITH req_seg_slices AS (
                SELECT slice_id, direction
                FROM segstack_%(segstack_id)s.segment_slice
                  WHERE segment_id = %(segment_id)s)
            INSERT INTO segstack_%(segstack_id)s.correction (constraint_id, mistake_id)
            SELECT c.id, conflict.segment_id
            FROM (VALUES (%(constraint_id)s)) AS c (id),
                (SELECT DISTINCT ssol.segment_id AS segment_id
                    FROM segstack_%(segstack_id)s.solution_precedence sp
                    JOIN segstack_%(segstack_id)s.segment_solution ssol
                      ON (sp.solution_id = ssol.solution_id AND ssol.segment_id <> %(segment_id)s)
                    JOIN segstack_%(segstack_id)s.segment_slice ss ON (ssol.segment_id = ss.segment_id)
                    WHERE ss.slice_id IN (
                            SELECT scs_a.slice_a_id AS slice_id
                              FROM segstack_%(segstack_id)s.slice_conflict scs_a, req_seg_slices
                              WHERE scs_a.slice_b_id = req_seg_slices.slice_id
                            UNION SELECT scs_b.slice_b_id AS slice_id
                              FROM segstack_%(segstack_id)s.slice_conflict scs_b, req_seg_slices
                              WHERE scs_b.slice_a_id = req_seg_slices.slice_id)
                      OR ((ss.slice_id, ss.direction) IN (SELECT * FROM req_seg_slices)))
                    AS conflict
            ''' % {'segstack_id': segstack.id, 'segment_id': segment_id, 'constraint_id': constraint_id})

        return HttpResponse(json.dumps({'ok': True, 'constraint_id': constraint_id}), content_type='text/json')
    except:
        return error_response()


def retrieve_user_constraints_by_blocks(request, project_id=None, stack_id=None):
    try:
        block_ids = [int(id) for id in safe_split(request.POST.get('block_ids'), 'block IDs')]
        cursor = connection.cursor()
        cursor.execute('''
            SELECT csr.constraint_id, array_agg(csr.segment_id) as segment_ids
            FROM djsopnet_blockconstraintrelation bcr
            JOIN djsopnet_constraintsegmentrelation csr
                ON bcr.constraint_id = csr.constraint_id
            WHERE bcr.block_id IN (%s)
            GROUP BY csr.constraint_id
            ''' % ','.join(map(str, block_ids)))
        constraints = cursor.fetchall()

        return HttpResponse(json.dumps({'ok': True, 'constraints': constraints}), content_type='text/json')
    except:
        return error_response()
