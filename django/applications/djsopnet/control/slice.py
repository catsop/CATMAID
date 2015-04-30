import json
import os
from collections import namedtuple
from pgmagick import Image, Blob, Color, CompositeOperator

from django.conf import settings
from django.db import connection
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.templatetags.static import static

from catmaid.control.authentication import requires_user_role
from catmaid.models import UserRole
from djsopnet.control.common import error_response, safe_split, hash_to_id, id_to_hash
from djsopnet.models import SegmentationStack


def slice_dict(slice, with_conflicts=False, with_solution=False):
    sd = {'hash': id_to_hash(slice.id),
          'section': slice.section,
          'box': [slice.min_x, slice.min_y, slice.max_x, slice.max_y],
          'ctr': [slice.ctr_x, slice.ctr_y],
          'value': slice.value,
          'size': slice.size,
          'mask': static('slicemasks/' + str(slice.id) + '.png'),
          'segment_summaries': slice.segment_summaries}

    for summary in sd['segment_summaries']:
        summary.update({'segment_hash': id_to_hash(summary['segment_id'])})
        summary.pop('segment_id', None)

    if with_conflicts:
        sd['conflicts'] = ','.join(map(id_to_hash, slice.conflict_slice_ids))

    if with_solution:
        sd['in_solution'] = slice.in_solution

    return sd


def generate_slice_response(slice):
    if slice:
        return HttpResponse(json.dumps(slice_dict(slice)), content_type='text/json')
    else:
        return HttpResponse(json.dumps({'hash': 'nope'}), content_type='text/json')


def generate_slices_response(slices, with_conflicts=False, with_solutions=False):
    slice_list = [slice_dict(slice, with_conflicts, with_solutions) for slice in slices]
    return HttpResponse(json.dumps({'ok' : True, 'slices' : slice_list}), content_type='text/json')


# --- Slices ---

def slice_alpha_mask(request, project_id=None, segmentation_stack_id=None, slice_hash=None):
    # For performance the existence of project, stack and slice are not verified.
    slice_id = hash_to_id(slice_hash) # Also effectively sanitizes slice_hash.

    gray_mask_file = os.path.join(settings.SOPNET_COMPONENT_DIR, str(slice_id) + '.png')
    if not os.path.isfile(gray_mask_file): raise(Http404)

    gray_mask = Image(gray_mask_file)
    alpha_mask = Image(gray_mask.size(), Color('#FFF'))
    alpha_mask.composite(gray_mask, 0, 0, CompositeOperator.CopyOpacityCompositeOp)
    response_blob = Blob()
    alpha_mask.magick('PNG')
    alpha_mask.write(response_blob)

    return HttpResponse(response_blob.data, content_type='image/png')


def _slice_select_query(segmentation_stack_id, slice_id_query):
    """Build a querystring to select slices and relationships given an ID query.

    Keyword arguments:
    slice_id_query -- A string SELECT statement returning a slice_id column
    """
    return '''
            SELECT
              s.id, s.section,
              s.min_x, s.min_y, s.max_x, s.max_y,
              s.ctr_x, s.ctr_y, s.value, s.size,
              ARRAY_AGG(DISTINCT scs_as_a.slice_b_id) AS conflicts_as_a,
              ARRAY_AGG(DISTINCT scs_as_b.slice_a_id) AS conflicts_as_b,
              ARRAY_TO_JSON(ARRAY_AGG(DISTINCT ROW(ss.segment_id, ss.direction))) AS segment_summaries,
              ARRAY_TO_JSON(ARRAY_AGG(DISTINCT ROW(ssol.solution_id, ssol.assembly_id))) AS in_solution
            FROM segstack_%(segstack_id)s.slice s
            JOIN (%(slice_id_query)s) AS slice_id_query
              ON (slice_id_query.slice_id = s.id)
            LEFT JOIN segstack_%(segstack_id)s.slice_conflict scs_as_a ON (scs_as_a.slice_a_id = s.id)
            LEFT JOIN segstack_%(segstack_id)s.slice_conflict scs_as_b ON (scs_as_b.slice_b_id = s.id)
            JOIN segstack_%(segstack_id)s.segment_slice ss ON (ss.slice_id = s.id)
            LEFT JOIN
              (SELECT aseg.segment_id, sola.solution_id, sola.assembly_id, sp.core_id
                  FROM segstack_%(segstack_id)s.assembly_segment aseg
                  JOIN segstack_%(segstack_id)s.solution_assembly sola
                    ON sola.assembly_id = aseg.assembly_id
                  JOIN segstack_%(segstack_id)s.solution_precedence sp
                    ON sp.solution_id = sola.solution_id)
              AS ssol
                ON (ssol.segment_id = ss.segment_id)
            GROUP BY s.id
            ''' % {'segstack_id': segmentation_stack_id, 'slice_id_query': slice_id_query}


def _slicecursor_to_namedtuple(cursor):
    """Create a namedtuple list stubbing for Slice objects from a cursor.

    Assumes the cursor has been executed and has at least the following columns:
    conflicts_as_a, conflicts_as_b, in_solution_core_ids, segment_summaries.
    """
    cols = [col[0] for col in cursor.description]

    SliceTuple = namedtuple('SliceTuple', cols + ['conflict_slice_ids'])

    def slicerow_to_namedtuple(row):
        rowdict = dict(zip(cols, row))
        # In PostgreSQL 9.4 it will be possible to preserve column names in JSON
        # aggregated ROW columns without subqueries or CTEs. For now manually
        # map from default field names to original column names.
        segment_map = {'f1': 'segment_id', 'f2': 'direction'}
        rowdict.update({
                'conflict_slice_ids': filter(None, rowdict['conflicts_as_a'] + rowdict['conflicts_as_b']),
                'in_solution': dict([
                    (solution['f1'], solution['f2'])
                    for solution in json.loads(rowdict['in_solution'])
                ]),
                'segment_summaries': [
                    {segment_map[k]: v for k, v in summary.items()}
                    for summary in json.loads(rowdict['segment_summaries'])
                ]
            })
        if not any(rowdict['in_solution'].keys()):
            rowdict['in_solution'] = False
        return SliceTuple(**rowdict)

    return [slicerow_to_namedtuple(row) for row in cursor.fetchall()]


def _retrieve_slices_by_ids(segmentation_stack_id, slice_ids):
    slices = []
    if slice_ids:
        cursor = connection.cursor()
        cursor.execute(_slice_select_query(
                segmentation_stack_id, '''
                SELECT * FROM (VALUES (%s)) AS t (slice_id)
                ''' % '),('.join(map(str, slice_ids))))

        slices = _slicecursor_to_namedtuple(cursor)

    return slices


@requires_user_role([UserRole.Annotate, UserRole.Browse])
def retrieve_slices_by_blocks_and_conflict(request, project_id, segmentation_stack_id):
    """Retrieve slices and slices in conflict sets for a set of blocks.

    Retrieve Slices associated to the Blocks with the given ids or to any
    ConflictSet that is associated with those Blocks.
    """
    segstack = get_object_or_404(SegmentationStack, pk=segmentation_stack_id)
    try:
        block_ids = ','.join([str(int(id)) for id in safe_split(request.POST.get('block_ids'), 'block IDs')])

        cursor = connection.cursor()
        cursor.execute(_slice_select_query(segmentation_stack_id, '''
                SELECT sbr.slice_id
                  FROM segstack_%(segstack_id)s.slice_block_relation sbr
                  WHERE sbr.block_id IN (%(block_ids)s)
                UNION SELECT scs_cbr_a.slice_a_id AS slice_id
                  FROM segstack_%(segstack_id)s.block_conflict_relation bcr
                  JOIN segstack_%(segstack_id)s.slice_conflict scs_cbr_a ON (scs_cbr_a.id = bcr.slice_conflict_id)
                  WHERE bcr.block_id IN (%(block_ids)s)
                UNION SELECT scs_cbr_b.slice_b_id AS slice_id
                  FROM segstack_%(segstack_id)s.block_conflict_relation bcr
                  JOIN segstack_%(segstack_id)s.slice_conflict scs_cbr_b ON (scs_cbr_b.id = bcr.slice_conflict_id)
                  WHERE bcr.block_id IN (%(block_ids)s)
                ''' % {'segstack_id': segstack.id, 'block_ids': block_ids}))

        slices = _slicecursor_to_namedtuple(cursor)

        return generate_slices_response(slices=slices,
                with_conflicts=True, with_solutions=True)
    except:
        return error_response()


@requires_user_role([UserRole.Annotate, UserRole.Browse])
def retrieve_slices_by_location(request, project_id, segmentation_stack_id):
    """Retrieve slices and their conflicts for a given location in stack coordinates."""
    segstack = get_object_or_404(SegmentationStack, pk=segmentation_stack_id)
    bi = segstack.configuration.block_info

    zoom = 2**(-bi.scale)
    x = int(float(request.POST.get('x', None))) * zoom
    y = int(float(request.POST.get('y', None))) * zoom
    z = int(float(request.POST.get('z', None)))

    slice_ids = _slice_ids_intersecting_point(segmentation_stack_id, x, y, z)

    slices = _retrieve_slices_by_ids(segmentation_stack_id, slice_ids)

    return generate_slices_response(slices=slices,
            with_conflicts=True, with_solutions=True)


def _slice_ids_intersecting_point(segmentation_stack_id, x, y, z):
    # Find slices whose bounding box intersects the requested location
    cursor = connection.cursor()
    cursor.execute('''
            SELECT s.id, s.min_x, s.min_y
              FROM segstack_%(segstack_id)s.slice s
              WHERE s.section = %(z)s
                AND s.min_x <= %(x)s
                AND s.max_x >= %(x)s
                AND s.min_y <= %(y)s
                AND s.max_y >= %(y)s
            ''' % {'segstack_id': segmentation_stack_id, 'z': z, 'x': x, 'y': y})

    # Check masks of the candidate slices to check for intersection
    candidates = cursor.fetchall()
    slice_ids = []
    for [slice_id, min_x, min_y] in candidates:
        gray_mask_file = os.path.join(settings.SOPNET_COMPONENT_DIR, str(slice_id) + '.png')
        if not os.path.isfile(gray_mask_file):
            raise Http404

        gray_mask = Image(gray_mask_file)
        pixel = gray_mask.pixelColor(int(x - min_x), int(y - min_y))
        if pixel.intensity() > 0:
            slice_ids.append(slice_id)

    return slice_ids


@requires_user_role([UserRole.Annotate, UserRole.Browse])
def retrieve_slices_by_bounding_box(request, project_id, segmentation_stack_id):
    segstack = get_object_or_404(SegmentationStack, pk=segmentation_stack_id)
    bi = segstack.configuration.block_info
    try:
        zoom = 2**(-bi.scale)
        min_x = int(float(request.POST.get('min_x', None))) * zoom
        min_y = int(float(request.POST.get('min_y', None))) * zoom
        max_x = int(float(request.POST.get('max_x', None))) * zoom
        max_y = int(float(request.POST.get('max_y', None))) * zoom
        z = int(float(request.POST.get('z', None)))

        cursor = connection.cursor()
        cursor.execute(_slice_select_query(segmentation_stack_id, '''
                SELECT s.id AS slice_id
                  FROM segstack_%(segstack_id)s.assembly_segment aseg
                  JOIN segstack_%(segstack_id)s.solution_assembly sola
                    ON sola.assembly_id = aseg.assembly_id
                  JOIN segstack_%(segstack_id)s.solution_precedence sp
                    ON sp.solution_id = sola.solution_id
                  JOIN segstack_%(segstack_id)s.segment_slice ss ON (ss.segment_id = aseg.segment_id)
                  JOIN segstack_%(segstack_id)s.slice s ON (s.id = ss.slice_id)
                  WHERE s.section = %(z)s
                    AND s.min_x <= %(max_x)s
                    AND s.max_x >= %(min_x)s
                    AND s.min_y <= %(max_y)s
                    AND s.max_y >= %(min_y)s
                ''' % {'segstack_id': segstack.id, 'z': z, 'max_x': max_x, 'min_x': min_x, 'max_y': max_y, 'min_y': min_y}))

        slices = _slicecursor_to_namedtuple(cursor)

        return generate_slices_response(slices=slices,
                with_conflicts=True, with_solutions=True)
    except:
        return error_response()


@requires_user_role([UserRole.Annotate, UserRole.Browse])
def retrieve_conflict_sets(request, project_id, segmentation_stack_id):
    segstack = get_object_or_404(SegmentationStack, pk=segmentation_stack_id)
    try:
        slice_ids = map(hash_to_id, safe_split(request.POST.get('hash'), 'slice hashes'))

        cursor = connection.cursor()
        cursor.execute('''
            SELECT slice_a_id, slice_b_id
            FROM segstack_%(segstack_id)s.slice_conflict
            WHERE slice_a_id IN (%(slice_ids)s)
              OR slice_b_id IN (%(slice_ids)s)
            ''' % {'segstack_id': segstack.id, 'slice_ids': ','.join(map(str, slice_ids))})
        conflicts = cursor.fetchall()
        conflicts = [map(id_to_hash, conflict) for conflict in conflicts]

        return HttpResponse(json.dumps({'ok': True, 'conflict': conflicts}))
    except:
        return error_response()


@requires_user_role([UserRole.Annotate, UserRole.Browse])
def retrieve_slices_for_skeleton(request, project_id=None, stack_id=None, skeleton_id=None):
    """To visualize the slices found for a given skeleton, for which UserConstraints and solutions were generated,
    we retrieve all segments with their solution flag, and retrieve all associated slices, and mark the
    selected slices that are in the solution.

    In addition, special locations are found and returned where SOPNET has potentially found a solution segment
    that needs review:
    - Leaf nodes of connected components, e.g. at skeleton branch locations where no user constrait
      could be generated
    - skeleton leaf nodes where SOPNET found additional segments
    - high cost segments that were selected by SOPNET

    For those locations, a segment is associated. Then, a lookup function to retrieve for a given segments the
    associated connected componente, i.e. the traversal along selected segments of the solution, can be called.


    # TOREMOVE: dummy example
    data = {
        'slices': {
            1: {
                'section': 0,
                'min_x': 0, 'min_y': 0,
                'width': 50, 'height': 50,
                'url': 'http://neurocity.janelia.org/l3vnc/slices/0/3.png',
                'color': "rgb(255,0,0)"
            },
        },
        'segments': {
        }
    }
    return HttpResponse(json.dumps((data), separators=(',', ':')))


    """
    data = {
        'slices': {}, 'segments': {}, 'lookup': {}
    }
    # Retrieve the UserConstraints associated with a skeleton, and then all the associated segments
    constraint_ids = Constraint.objects.filter(skeleton=skeleton_id).values('id')

    if len(constraint_ids) == 0:
        return HttpResponse(json.dumps(({'error': 'No UserConstaints were generated for this skeleton.'}), separators=(',', ':')))

    constraint_segment_ids = ConstraintSegmentRelation.objects.filter(constraint__in=constraint_ids).values('segment')

    # Retrieve all continuation and branch Segments associated with these constraints
    segments = Segment.objects.filter(id__in=constraint_segment_ids, type__gt=1).values('id', 'section_inf', 'type')

    for seg in segments:
        data['segments'][seg['id']] = {
            'section': seg['section_inf'],
            'type': seg['type'],
            'left': [], 'right': []
        }

    segment_slices = SegmentSlice.objects.filter(segment__in=data['segments'].keys()).values('slice', 'segment', 'direction')
    for ss in segment_slices:
        if ss['direction']:
            direction = 'left'
        else:
            direction = 'right'
        data['segments'][ss['segment']][direction].append(ss['slice'])

    # add the solution flag to the segments
    segment_solutions = SegmentSolution.objects.filter(segment__in=data['segments'].keys()).value('segment', 'solution')
    slices_to_retrieve = set()
    for sol in segment_solutions:
        seg = data['segments'][sol['segment']]
        seg['solution'] = sol['solution']
        slices_to_retrieve.update(seg['left'] + seg['right']) # add all slices for retrieval

    # Retrieve all Slices associated to those segments. Mark the slices of selected solution segments.
    # On demand retrieval from the client of additional slices of segments that are not part of the solution
    slices = Slice.objects.filter(id__ind=list(slices_to_retrieve)).values('id', 'min_x', 'min_y', 'max_x',
        'max_y', 'section')
    for sli in slices:
        data['slices'][sli['id']] = {
            'section': sli['section'],
            'min_x': sli['min_x'], 'min_y': sli['min_y'],
            'max_x': sli['max_x'], 'max_y': sli['max_y']
        }

    # TODO: lookup locations
    return HttpResponse(json.dumps((data), separators=(',', ':')))


@requires_user_role([UserRole.Annotate, UserRole.Browse])
def retrieve_connected_component_starting_from_initial_slice(request, slice_id=None):
    """ Retrieve slices and segments that are connected from an initial starting slice

    Traverse the slices and segments along segments which are in the solution. If none of the
    outgoing segments are in the solution, return these locations separately with all the associated
    segments.

    Returned data structure can be used for e.g.
        - for visualization of the slices and segments in 3d
        - associate the set of slices and segments with an assembly id
        - iterative expansion of a neuron by processing additional core blocks
          at no_solution_segments locations
    """

    data = {'slices': [], 'segments': [], 'no_solution_segments': {}}

    slices_to_visit = [(slice_id, True), (slice_id, False)]

    for sliceid, direction in slices_to_visit:

        data['slices'].append(sliceid)

        # We want to traverse in direction seen from slice, which is 'not direction', seen from segment
        reverse_direction = not direction
        segments = [s['segment'] for s in SegmentSlice.objects.filter(slice=sliceid, direction=reverse_direction).values('segment', 'slice', 'direction')]
        # any of those segments in the solution?
        solutions = [s['segment'] for s in SegmentSolution.objects.filter(segment__in=segments).values('segment')]

        if len(solutions) == 1:
            # if yes: look up corresponding slices in direction
            solution_segmentid = solutions[0]
            # add solution segment to returned data
            data['segments'].append(solution_segmentid)

            # retrieve slices associated to the solution segmente and add to list for traversal
            associated_slices = [(s['slice'], s['direction']) for s in SegmentSlice.objects.filter(slice=solution_segmentid).values('segment', 'slice', 'direction')]

            for associated_sliceid, associated_direction in associated_slices:
                if associated_slice != sliceid:
                    # only add slice if not yet visited
                    slices_to_visit.extend((associated_sliceid, associated_direction))

        else:
            # if no: add all segments to no_solution_segments
            data['no_solution_segments'][(sliceid, direction)] = {
                segments
            }

    return HttpResponse(json.dumps((data), separators=(',', ':')))
