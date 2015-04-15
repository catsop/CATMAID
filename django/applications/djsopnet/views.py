import json
import math
import os

from collections import namedtuple

from pgmagick import Image, Blob, Color, CompositeOperator

import pysopnet

from django.http import Http404, HttpResponse, HttpResponseNotAllowed

from django.shortcuts import get_object_or_404
from django.db import connection
from django.conf import settings
from django.templatetags.static import static

from catmaid.models import *
from catmaid.control.stack import get_stack_info
from catmaid.control.authentication import requires_user_role
from models import *

from djsopnet.control.common import safe_split, hash_to_id, id_to_hash

from celerysopnet.tasks import SliceGuarantorTask, SegmentGuarantorTask
from celerysopnet.tasks import SolutionGuarantorTask, SolveSubvolumeTask
from celerysopnet.tasks import TraceNeuronTask

from djcelery.models import TaskState

from StringIO import StringIO
import traceback

# from djsopnet.control.slice import retrieve_slices_for_skeleton
# from djsopnet.control.skeleton_intersection import generate_user_constraints

# --- JSON conversion ---
def slice_dict(slice, with_conflicts=False, with_solution=False):
    sd = {'hash' : id_to_hash(slice.id),
          'section' : slice.section,
          'box' : [slice.min_x, slice.min_y, slice.max_x, slice.max_y],
          'ctr' : [slice.ctr_x, slice.ctr_y],
          'value' : slice.value,
          'size' : slice.size,
          'mask' : static('slicemasks/' + str(slice.id) + '.png'),
          'segment_summaries' : slice.segment_summaries}

    for summary in sd['segment_summaries']:
        summary.update({'segment_hash': id_to_hash(summary['segment_id'])})
        summary.pop('segment_id', None)

    if with_conflicts:
        sd['conflicts'] = ','.join(map(id_to_hash, slice.conflict_slice_ids))

    if with_solution:
        sd['in_solution'] = slice.in_solution

    return sd

def segment_dict(segment, with_solution=False):
    sd = {'hash' : id_to_hash(segment.id),
          'section' : segment.section_sup,
          'box' : [segment.min_x, segment.min_y, segment.max_x, segment.max_y],
          'ctr' : [segment.ctr_x, segment.ctr_y],
          'type' : segment.type}

    if with_solution:
        sd['in_solution'] = segment.in_solution

    return sd

def block_dict(block):
    bd = {'id' : block.id,
          'slices' : block.slices_flag,
          'segments' : block.segments_flag,
          'box' : block.box}
    return bd

def core_dict(core):
    bd = {'id' : core.id,
          'solutions' : core.solution_set_flag,
          'box' : core.box}
    return bd

def block_info_dict(block_info):
    bid = {'block_size' : [block_info.block_dim_x, block_info.block_dim_y, block_info.block_dim_z],
           'count' : [block_info.num_x, block_info.num_y, block_info.num_z],
           'core_size' : [block_info.core_dim_x, block_info.core_dim_y, block_info.core_dim_z],
           'scale': block_info.scale}
    return bid

def generate_slice_response(slice):
    if slice:
        return HttpResponse(json.dumps(slice_dict(slice)), content_type = 'text/json')
    else:
        return HttpResponse(json.dumps({'hash' : 'nope'}), content_type = 'text/json')

def generate_segment_response(segment):
    if segment:
        return HttpResponse(json.dumps(segment_dict(segment)), content_type = 'text/json')
    else:
        return HttpResponse(json.dumps({'id' : None}), content_type = 'text/json')


def generate_slices_response(slices, with_conflicts=False, with_solutions=False):
    slice_list = [slice_dict(slice, with_conflicts, with_solutions) for slice in slices]
    return HttpResponse(json.dumps({'ok' : True, 'slices' : slice_list}), content_type = 'text/json')

def generate_segments_response(segments, with_solutions=False):
    segment_list = [segment_dict(segment, with_solutions) for segment in segments]
    return HttpResponse(json.dumps({'ok' : True, 'segments' : segment_list}), content_type = 'text/json')

def generate_block_response(block):
    if block:
        return HttpResponse(json.dumps(block_dict(block)), content_type = 'text/json')
    else:
        return HttpResponse(json.dumps({'id' : None}), content_type = 'text/json')

def generate_blocks_response(blocks):
    if blocks is not None:
        block_dicts = [block_dict(block) for block in blocks]
        return HttpResponse(json.dumps({'ok' : True, 'length' : len(block_dicts), 'blocks' : block_dicts}))
    else:
        return HttpResponse(json.dumps({'ok' : True, 'length' : 0}))

def generate_core_response(core):
    if core:
        return HttpResponse(json.dumps(core_dict(core)), content_type = 'text/json')
    else:
        return HttpResponse(json.dumps({'id' : None}), content_type = 'text/json')

def generate_cores_response(cores):
    if cores is not None:
        core_dicts = [core_dict(core) for core in cores]
        return HttpResponse(json.dumps({'length' : len(core_dicts), 'cores' : core_dicts}))
    else:
        return HttpResponse(json.dumps({'length' : 0}))


def generate_block_info_response(block_info):
    return HttpResponse(json.dumps(block_info_dict(block_info)), content_type='text/json')


def generate_features_response(features):
    features_dicts = []
    for feature in features:
        segment_hash = id_to_hash(feature.segment_id)
        feature_values = feature.features
        features_dicts.append({'hash' : segment_hash, 'fv': feature_values})
    return HttpResponse(json.dumps({'ok':True, 'features' : features_dicts}), content_type='text/json')

def error_response():
    sio = StringIO()
    traceback.print_exc(file = sio)
    res = HttpResponse(json.dumps({'ok': False, 'error' : sio.getvalue()}))
    sio.close()
    return res

# --- Configuration ---
def segmentation_configurations(request, project_id, stack_id):
    if request.method == 'GET':
        ps = get_object_or_404(ProjectStack, project_id=project_id, stack_id=stack_id)
        cursor = connection.cursor()
        cursor.execute('''
                SELECT row_to_json(config) FROM (
                SELECT sc.id AS id, json_agg(ss.*) AS stacks FROM segmentation_configuration sc
                JOIN segmentation_stack ss ON ss.configuration_id = sc.id
                WHERE sc.project_id = %s
                  AND EXISTS (
                    SELECT 1 FROM segmentation_stack sse
                    WHERE sse.configuration_id = sc.id AND sse.project_stack_id = %s)
                GROUP BY sc.id) config
                ''', [project_id, stack_id])
        configs = [r[0] for r in cursor.fetchall()]
        if len(configs) == 0:
            raise Http404('No segmentation is configured involving this project and stack.')
        return HttpResponse('[' + ','.join(map(str, configs)) + ']', content_type='text/json')

    return HttpResponseNotAllowed(['GET'])

# --- Blocks and Cores ---
def setup_blocks(request, project_id, segmentation_stack_id):
    '''
    Initialize and store the blocks and block info in the db, associated with
    the given stack, if these things don't already exist.
    '''
    try:
        scale = int(request.GET.get('scale'))
        width = int(request.GET.get('width'))
        height = int(request.GET.get('height'))
        depth = int(request.GET.get('depth'))
        # core height, width, and depth in blocks
        corewib = int(request.GET.get('core_dim_x'))
        corehib = int(request.GET.get('core_dim_y'))
        coredib = int(request.GET.get('core_dim_z'))
    except TypeError:
        return HttpResponse(json.dumps({'ok' : False, 'reason' : 'malformed'}), content_type='text/json')
    try:
        _setup_blocks(segmentation_stack_id, scale, width, height, depth,
                      corewib, corehib, coredib)
    except ValueError as e:
        return HttpResponse(json.dumps({'ok': False, 'reason' : str(e)}), content_type='text/json')

    return HttpResponse(json.dumps({'ok': True}), content_type='text/json')

def _setup_blocks(segmentation_stack_id, scale, width, height, depth, corewib, corehib, coredib):
    segstack = get_object_or_404(SegmentationStack, pk=segmentation_stack_id)
    s = segstack.project_stack.stack

    # The number of blocks is the ceiling of the stack size divided by block dimension
    def int_ceil(num, den): return ((num - 1) // den) + 1
    nx = int_ceil(s.dimension.x, width * 2**scale)
    ny = int_ceil(s.dimension.y, height * 2**scale)
    nz = int_ceil(s.dimension.z, depth)

    try:
        info = BlockInfo.objects.get(configuration=segstack.configuration)
    except BlockInfo.DoesNotExist:
        info = BlockInfo(configuration=segstack.configuration, scale=scale,
                         block_dim_y = height, block_dim_x = width, block_dim_z = depth,
                         core_dim_y = corehib, core_dim_x = corewib, core_dim_z = coredib,
                         num_x = nx, num_y = ny, num_z = nz)
        info.save()

    # Create new Blocks
    cursor = connection.cursor()
    cursor.execute('SELECT 1 FROM segstack_%s.block LIMIT 1' % segstack.id)
    if cursor.rowcount > 0:
        raise ValueError('Blocks for SegmentationStack %s are already setup.' % segstack.id)

    cursor.execute('''
            INSERT INTO segstack_%(segstack_id)s.block
              (slices_flag, segments_flag, coordinate_x, coordinate_y, coordinate_z)
                SELECT false, false, x.id, y.id, z.id FROM
                  generate_series(0, %(nx)s - 1) AS x (id),
                  generate_series(0, %(ny)s - 1) AS y (id),
                  generate_series(0, %(nz)s - 1) AS z (id);
            ''' % {'segstack_id': segstack.id, 'nx': nx, 'ny': ny, 'nz': nz})

    # Create new Cores, round up if number of blocks is not divisible by core size
    nzc = (nz + coredib - 1)/coredib
    nyc = (ny + corehib - 1)/corehib
    nxc = (nx + corewib - 1)/corewib
    cursor.execute('''
            INSERT INTO segstack_%(segstack_id)s.core
              (solution_set_flag, coordinate_x, coordinate_y, coordinate_z)
                SELECT false, x.id, y.id, z.id FROM
                  generate_series(0, %(nx)s - 1) AS x (id),
                  generate_series(0, %(ny)s - 1) AS y (id),
                  generate_series(0, %(nz)s - 1) AS z (id);
            ''' % {'segstack_id': segstack.id, 'nx': nxc, 'ny': nyc, 'nz': nzc})

def _blockcursor_to_namedtuple(cursor, size):
    """Create a namedtuple list stubbing for Block or Core objects from a cursor.

    Assumes the cursor has been executed.
    """
    cols = [col[0] for col in cursor.description]

    BlockTuple = namedtuple('BlockTuple', cols + ['box'])
    size = [size['x'], size['y'], size['z']]

    def blockrow_to_namedtuple(row):
        rowdict = dict(zip(cols, row))
        coords = [rowdict['coordinate_x'], rowdict['coordinate_y'], rowdict['coordinate_z']]
        rowdict.update({
                'box': [s*c for s,c in zip(size, coords)] + [s*(c+1) for s,c in zip(size, coords)]
            })
        return BlockTuple(**rowdict)

    return [blockrow_to_namedtuple(row) for row in cursor.fetchall()]

# Query, agnostic to Model class for Core, Block
def location_query(table, segmentation_stack, request):
    x = int(float(request.GET.get('x')))
    y = int(float(request.GET.get('y')))
    z = int(float(request.GET.get('z')))

    size = segmentation_stack.configuration.block_info.size_for_unit(table)
    cursor = connection.cursor()
    cursor.execute('''
            SELECT * FROM segstack_%(segstack_id)s.%(table)s
            WHERE coordinate_x = %(x)s
              AND coordinate_y = %(y)s
              AND coordinate_z = %(z)s
            ''' % {'segstack_id': segmentation_stack.id,
                'table': table,
                'x': math.floor(x/size['x']),
                'y': math.floor(y/size['y']),
                'z': math.floor(z/size['z'])})
    if cursor.rowcount == 0:
        return None
    else:
        return _blockcursor_to_namedtuple(cursor, size)[0]

def bound_query(table, segmentation_stack, request):
    min_x = int(float(request.POST.get('min_x', None)))
    min_y = int(float(request.POST.get('min_y', None)))
    min_z = int(float(request.POST.get('min_z', None)))
    max_x = int(float(request.POST.get('max_x', None)))
    max_y = int(float(request.POST.get('max_y', None)))
    max_z = int(float(request.POST.get('max_z', None)))

    size = segmentation_stack.configuration.block_info.size_for_unit(table)
    cursor = connection.cursor()
    cursor.execute('''
            SELECT * FROM segstack_%(segstack_id)s.%(table)s
            WHERE coordinate_x >= %(min_x)s
              AND coordinate_y >= %(min_y)s
              AND coordinate_z >= %(min_z)s
              AND coordinate_x <= %(max_x)s
              AND coordinate_y <= %(max_y)s
              AND coordinate_z <= %(max_z)s
            ''' % {'segstack_id': segmentation_stack.id,
                'table': table,
                'min_x': math.floor(min_x/size['x']),
                'min_y': math.floor(min_y/size['y']),
                'min_z': math.floor(min_z/size['z']),
                'max_x': math.ceil(max_x/size['x']),
                'max_y': math.ceil(max_y/size['y']),
                'max_z': math.ceil(max_z/size['z'])})
    if cursor.rowcount == 0:
        return None
    else:
        return _blockcursor_to_namedtuple(cursor, size)

def block_at_location(request, project_id, segmentation_stack_id):
    segstack = get_object_or_404(SegmentationStack, pk=segmentation_stack_id)
    try:
        block = location_query('block', segstack, request)
        return generate_block_response(block)
    except:
        return generate_block_response(None)

def retrieve_blocks_by_bounding_box(request, project_id, segmentation_stack_id):
    segstack = get_object_or_404(SegmentationStack, pk=segmentation_stack_id)
    blocks = bound_query('block', segstack, request)

    return generate_blocks_response(blocks)

def core_at_location(request, project_id, segmentation_stack_id):
    segstack = get_object_or_404(SegmentationStack, pk=segmentation_stack_id)
    try:
        core = location_query('core', segstack, request)
        return generate_core_response(core)
    except:
        return generate_core_response(None)

def retrieve_cores_by_bounding_box(request, project_id, segmentation_stack_id):
    segstack = get_object_or_404(SegmentationStack, pk=segmentation_stack_id)
    cores = bound_query('core', segstack, request)
    return generate_cores_response(cores)

def retrieve_blocks_by_id(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk=stack_id)
    try:
        ids = [int(id) for id in safe_split(request.POST.get('ids'), 'block IDs')]
        blocks = Block.objects.filter(id__in = ids)
        return generate_blocks_response(blocks)
    except:
        return error_response()

def retrieve_cores_by_id(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk=stack_id)
    try:
        ids = [int(id) for id in safe_split(request.POST.get('ids'), 'core IDs')]
        cores = Core.objects.filter(id__in = ids)
        return generate_cores_response(cores)
    except:
        return error_response()

def stack_info(request, project_id = None, stack_id = None):
    # TODO: circumventing user role requirements in CATMAID
    result=get_stack_info(project_id, stack_id, request.user)
    return HttpResponse(json.dumps(result, sort_keys=True, indent=4), content_type="text/json")

def block_info(request, configuration_id=None):
    block_info = get_object_or_404(BlockInfo, configuration_id=configuration_id)
    return generate_block_info_response(block_info)

def get_flag(s, request, flag_name, id_field = 'block_id', type = 'block'):
    id = int(request.GET.get(id_field))
    try:
        box = type.objects.get(stack = s, id = id)
        flag = getattr(box, flag_name)
        return HttpResponse(json.dumps({flag_name : flag}), content_type='text/json')
    except type.DoesNotExist:
        return HttpResponse(json.dumps({flag_name : False, 'ok' : False}), content_type='text/json')

def set_block_segment_flag(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk=stack_id)
    return set_flag(s, request, 'segments_flag')

def get_block_slice_flag(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk=stack_id)
    return get_flag(s, request, 'slices_flag')

def get_block_segment_flag(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk=stack_id)
    return get_flag(s, request, 'segments_flag')

def get_block_solution_flag(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk=stack_id)
    return get_flag(s, request, 'solution_cost_flag')

def get_core_solution_flag(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk=stack_id)
    return get_flag(s, request, 'solution_set_flag', 'core_id', Core)

# --- Slices ---

def slice_alpha_mask(request, project_id=None, stack_id=None, slice_hash=None):
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

def do_insert_slices(stack, req_dict):
    try:
        n = int(req_dict.get('n'))
        slices = []
        for i in range(n):
            i_str = str(i)
            section = int(req_dict['section_' + i_str])
            hash_value = req_dict['hash_' + i_str]
            ctr_x = float(req_dict['cx_' + i_str])
            ctr_y = float(req_dict['cy_' + i_str])
            value = float(req_dict['value_' + i_str])
            min_x = float(req_dict['minx_' + i_str])
            min_y = float(req_dict['miny_' + i_str])
            max_x = float(req_dict['maxx_' + i_str])
            max_y = float(req_dict['maxy_' + i_str])
            size = int(req_dict['size_' + i_str])
            slice = Slice(stack = stack,
                  assembly = None, id = hash_to_id(hash_value), section = section,
                  min_x = min_x, min_y = min_y, max_x = max_x, max_y = max_y,
                  ctr_x = ctr_x, ctr_y = ctr_y, value = value, size = size)
            try:
                slice.save()
            except IntegritryError:
                # An IntegritryError is raised if a slice already exists. This can happen
                # during normal operation.
                pass

        return HttpResponse(json.dumps({'ok': True}), content_type='text/json')
    except:
        return error_response()

def insert_slices(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)

    if request.method == 'GET':
        return do_insert_slices(s, request.GET)
    else:
        return do_insert_slices(s, request.POST)

def associate_slices_to_block(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk=stack_id)

    try:
        slice_ids = map(hash_to_id, safe_split(request.POST.get('hash'), 'slice hashes'))

        block_id = int(request.POST.get('block'))
        if not block_id:
            raise ValueError("No block ID provided")
        block_id = int(block_id)

        # TODO: use bulk_create
        for slice_id in slice_ids:
            bsr = SliceBlockRelation(block_id = block_id, slice_id = slice_id)
            bsr.save()

        return HttpResponse(json.dumps({'ok' : True}), content_type='text/json')

    except Block.DoesNotExist:
        return HttpResponse(json.dumps({'ok' : False, 'reason' : 'Block does not exist'}), content_type='text/json')
    except:
        return error_response()

def retrieve_slices_by_hash(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    slice_ids = map(hash_to_id, safe_split(request.POST.get('hash'), 'hash values'))

    slices = Slice.objects.filter(stack = s, id__in = slice_ids)
    return generate_slices_response(slices)

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
              (SELECT ssol.segment_id, ssol.solution_id, ssol.assembly_id, sp.core_id
                  FROM segstack_%(segstack_id)s.segment_solution ssol
                  JOIN segstack_%(segstack_id)s.solution_precedence sp ON sp.solution_id = ssol.solution_id)
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
                    {segment_map[k]: v for k,v in summary.items()}
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
        if not os.path.isfile(gray_mask_file): raise(Http404)

        gray_mask = Image(gray_mask_file)
        pixel = gray_mask.pixelColor(int(x - min_x), int(y - min_y))
        if pixel.intensity() > 0:
            slice_ids.append(slice_id)

    return slice_ids

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
                  FROM segstack_%(segstack_id)s.segment_solution ssol
                  JOIN segstack_%(segstack_id)s.solution_precedence sp ON (sp.solution_id = ssol.solution_id)
                  JOIN segstack_%(segstack_id)s.segment_slice ss ON (ss.segment_id = ssol.segment_id)
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

def store_conflict_set(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)

    try:

        conflict_sets = safe_split(request.POST.get('hash'), 'conflict set hashes', '|')

        for conflict_set in conflict_sets:

            slice_ids = map(hash_to_id, safe_split(conflict_set, 'slice hashes'))

            # Collect slices from ids, then blocks from slices.
            if 2 != len(slice_ids):
                raise ValueError("Wrong number of slices for conflict set (found %s expected 2): " \
                        "Requested: %s" % (len(slice_ids), slice_ids))

            bsrs = SliceBlockRelation.objects.filter(slice__in = slice_ids)
            if len(bsrs) < len(slice_ids):
                # TODO: This is not an effective check, as 2 bsr's could be found for one slice and
                # none for the other
                raise ValueError("Couldn't find all required slice-block-relations")

            blocks = [bsr.block for bsr in bsrs]

            # no exception, so far. create the conflict set
            slice_order = [0, 1] if id_to_hash(slice_ids[0]) < id_to_hash(slice_ids[1]) else [1, 0]
            sliceConflict = SliceConflict(slice_a_id = slice_ids[slice_order[0]],
                    slice_b_id = slice_ids[slice_order[1]])
            sliceConflict.save()
            for block in blocks:
                blockConflict = BlockConflictRelation(block = block, conflict = sliceConflict)
                blockConflict.save()

        return HttpResponse(json.dumps({'ok' : True}), content_type='text/json')

    except:

        return error_response()

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

        return HttpResponse(json.dumps({'ok' : True, 'conflict' : conflicts}))
    except:
        return error_response()

def retrieve_block_ids_by_slices(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    try:
        slice_ids = map(hash_to_id, safe_split(request.POST.get('hash'), 'slice hashes'))

        slices = Slice.objects.filter(stack = s, id__in = slice_ids)
        block_relations = SliceBlockRelation.objects.filter(slice__in = slices)
        blocks = {br.block for br in block_relations}
        block_ids = [block.id for block in blocks]

        return HttpResponse(json.dumps({'ok' : True, 'block_ids' : block_ids}), content_type='text/json')
    except:
        return error_response()

# --- Segments ---
def setup_feature_names(names, stack, project):
    try:
        FeatureInfo.objects.get(stack = stack)
        return False
    except FeatureInfo.DoesNotExist:
        ids = []
        for name in names:
            feature_name = FeatureName(name = name)
            feature_name.save()
            ids.append(feature_name.id)
        info = FeatureInfo(stack = stack, name_ids = ids, size = len(ids))
        info.save()
        return True

def get_feature_names(stack, project):
    # get feature names, if they exist.
    # throws FeatureNameInfo.DoesNotExist, and possibly FeatureNameInfo.MultipleObjectsReturned
    feature_info = FeatureInfo.objects.get(stack = stack)
    keys = feature_info.name_ids
    feature_name_objects = FeatureName.objects.filter(id__in = keys)
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

def do_insert_segments(stack, dict):
    try:
        n = int(dict.get('n'))
        for i in range(n):
            i_str = str(i)
            section_sup = int(dict.get('sectionsup_' + i_str))
            hash_value = dict.get('hash_' + i_str)
            ctr_x = float(dict.get('cx_' + i_str))
            ctr_y = float(dict.get('cy_' + i_str))
            min_x = float(dict.get('minx_' + i_str))
            min_y = float(dict.get('miny_' + i_str))
            max_x = float(dict.get('maxx_' + i_str))
            max_y = float(dict.get('maxy_' + i_str))
            type = int(dict.get('type_' + i_str))
            direction = int(dict.get('direction_' + i_str))
            slice_a_hash = dict.get('slice_a_' + i_str)

            # type == 0 : End Segment, slice_a only
            # type == 1 : Continuation Segment, slice_a and slice_b
            # type == 2: Branch Segment, slice_a, slice_b, and slice_c
            # we don't check for the existence in the dict first. If the type doesn't match
            # the number of slices, we'll throw an exception, which will be returned to the sopnet
            # code via error_response
            if type > 0:
                slice_b_hash = dict.get('slice_b_' + i_str)
            else:
                slice_b_hash = None

            if type > 1:
                slice_c_hash = dict.get('slice_c_' + i_str)
            else:
                slice_c_hash = None

            segment = Segment(stack = stack, assembly = None,
                              id = hash_to_id(hash_value), section_sup = section_sup,
                              min_x = min_x, min_y = min_y, max_x = max_x, max_y = max_y,
                              ctr_x = ctr_x, ctr_y = ctr_y, type = type, direction = direction,
                              slice_a_id = hash_to_id(slice_a_hash),
                              slice_b_id = hash_to_id(slice_b_hash),
                              slice_c_id = hash_to_id(slice_c_hash))
            segment.save()

        return HttpResponse(json.dumps({'ok': True}), content_type='text/json')
    except:
        return error_response()


def insert_segments(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)

    if request.method == 'GET':
        return do_insert_segments(s, request.GET)
    else:
        return do_insert_segments(s, request.POST)

def associate_segments_to_block(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)

    try:
        segment_ids = map(hash_to_id, safe_split(request.POST.get('hash'), 'segment hashes'))
        block_id = int(request.POST.get('block'))

        block = Block.objects.get(id = block_id)

        segments = Segment.objects.filter(stack = s, id__in = segment_ids)

        for segment in segments:
            bsr = SegmentBlockRelation(block = block, segment = segment)
            bsr.save()

        return HttpResponse(json.dumps({'ok' : True}), content_type='text/json')
    except Block.DoesNotExist:
        return HttpResponse(json.dumps({'ok' : False, 'reason' : 'Block does not exist'}), content_type='text/json')
    except:
        return error_response()

def retrieve_segments_by_hash(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    hash_ids = map(hash_to_id, safe_split(request.POST.get('hash'), 'segment hashes'))
    segments = Segment.objects.filter(stack = s, id__in = hash_ids)
    return generate_segments_response(segments)

def retrieve_segments_by_blocks(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    try:
        block_ids = [int(id) for id in safe_split(request.POST.get('block_ids'), 'block IDs')]
        blocks = Block.objects.filter(stack=s, id__in=block_ids)
        segments = Segment.objects.filter(segmentblockrelation__block_id__in=block_ids)

        return generate_segments_response(segments)
    except:
        return error_response()

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

def set_feature_names(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    p = get_object_or_404(Project, pk = project_id)
    names = []

    try:
        names = safe_split(request.POST.get('names'), 'names')

        existing_names = get_feature_names(s, p)
        if existing_names == names:
            return HttpResponse(json.dumps({'ok' : True}), content_type='text/json')
        else:
            return HttpResponse(json.dumps({'ok' : False,
                                            'reason' : 'tried to set different feature names'}),
                                content_type='text/json')
    except FeatureInfo.DoesNotExist:
        if setup_feature_names(names, s, p):
            return HttpResponse(json.dumps({'ok' : True}), content_type='text/json')
        else:
            return HttpResponse(json.dumps({'ok' : False,
                                            'reason' : 'something went horribly, horribly awry'}),
                                content_type='text/json')
    except:
        return error_response()

def retrieve_feature_names(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    p = get_object_or_404(Project, pk = project_id)
    names = get_feature_names(s, p)
    return HttpResponse(json.dumps({'names' : names}), content_type='text/json')


def do_set_segment_features(stack, req_dict):
    try:
        n = int(req_dict.get('n'))
        feature_size = FeatureInfo.objects.get(stack = stack).size
        hash_values = []
        feature_list_dict = {}
        count = 0

        # Create a list of all hash values from the request
        # Populate the feature_list_dict with the feature lists for the given hash
        for i in range(n):
            i_str = str(i)
            hash_value = req_dict.get('hash_' + i_str)
            hash_values.append(hash_value)
            feature_str_list = req_dict.get('features_' + i_str).split(',')
            feature_list_dict[hash_value] = feature_str_list

        # Grab all segment objects in a single call
        segments = Segment.objects.filter(id__in = map(hash_to_id, hash_values))

        # Now, set the features
        for segment in segments:
            hash_value = str(id_to_hash(segment.id))

            feature_str_list = feature_list_dict[hash_value]

            # check that these features match the size in FeatureNameInfo
            if len(feature_str_list) != feature_size:
                return HttpResponse(
                    json.dumps({'ok': False,
                                'reason' : 'feature list is the wrong size',
                                'count' : count}),
                    content_type='text/json')

            feature_float_list = map(float, feature_str_list)

            try:
                segment_features = SegmentFeatures.objects.get(segment = segment)
                segment_features.features = feature_float_list
            except SegmentFeatures.DoesNotExist:
                segment_features = SegmentFeatures(segment = segment, features = feature_float_list)

            segment_features.save()

            count += 1

        return HttpResponse(json.dumps({'ok': True, 'count' : count}), content_type='text/json')
    except:
        return error_response()

def set_segment_features(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)

    if request.method == 'GET':
        return do_set_segment_features(s, request.GET)
    else:
        return do_set_segment_features(s, request.POST)

def get_segment_features(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    try:
        segment_ids = map(hash_to_id, safe_split(request.POST.get('hash'), 'segment hashes'))
        features = SegmentFeatures.objects.filter(segment__in = segment_ids)
        return generate_features_response(features)
    except:
        return error_response()


def set_segment_solutions(request, project_id = None, stack_id = None):
    p = get_object_or_404(Project, pk = project_id)

    try:
        n = int(request.POST.get('n'))
        core_id = int(request.POST.get('core_id'))
        solution_dict = {}
        hash_values = []
        count = 0

        core = Core.objects.get(id = core_id)

        # Collect all of the solution values and map them to the hash of the segment in question
        # Collect a list of hash values as well
        for i in range(n):
            i_str = str(i)
            hash_value = request.POST.get('hash_' + i_str)
            hash_values.append(hash_value)
            solution_dict[hash_value] = request.POST.get('solution_' + i_str).lower() in ['true', 'yes', '1']

        # filter all of the segments out in a single hit. Note that we might not get a Segment object for every
        # requested hash.
        segments = Segment.objects.filter(id__in = map(hash_to_id, hash_values))

        # Now, set the solution values.
        for segment in segments:
            hash_value = str(id_to_hash(segment.hash_value))
            solution = solution_dict[hash_value]
            # If there is already a SegmentSolution for this segment/core pair, just update it.
            try:
                segment_solution = SegmentSolution.objects.get(core = core, segment = segment)
                segment_solution.solution = solution
            except SegmentSolution.DoesNotExist:
                segment_solution = SegmentSolution(core = core,
                                                   segment = segment, solution = solution)
            segment_solution.save()
            count += 1

        return HttpResponse(json.dumps({'ok' : True, 'count' : count}), content_type='text/json')

    except:
        return error_response()

def retrieve_segment_solutions(request, project_id = None, stack_id = None):
    try:
        segment_ids = map(hash_to_id, safe_split(request.POST.get('hash'), 'segment hashes'))
        core_id = int(request.POST.get('core_id'))
        solutions = SegmentSolution.objects.filter(core_id = core_id, segment__in = segment_ids)

        solution_dicts = [{'hash' : id_to_hash(solution.segment.id),
                           'solution' : solution.solution} for solution in solutions]

        return HttpResponse(json.dumps({'ok' : True, 'solutions' : solution_dicts}),
                            content_type='text/json')
    except:
        return error_response()

def retrieve_block_ids_by_segments(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    try:
        segment_ids = map(hash_to_id, safe_split(request.POST.get('hash'), 'segment hashes'))

        segments = Segment.objects.filter(stack = s, id__in = segment_ids)
        block_relations = SegmentBlockRelation.objects.filter(segment__in = segments)
        blocks = {br.block for br in block_relations}
        block_ids = [block.id for block in blocks]

        return HttpResponse(json.dumps({'ok' : True, 'block_ids' : block_ids}), content_type='text/json')
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

def retrieve_user_constraints_by_blocks(request, project_id = None, stack_id = None):
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

        return HttpResponse(json.dumps({'ok' : True, 'constraints' : constraints}), content_type = 'text/json')
    except:
        return error_response()


# --- convenience code for debug purposes ---
def clear_slices(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    sure = request.GET.get('sure')
    if sure == 'yes':
        Slice.objects.filter(stack = s).delete()
        return HttpResponse(json.dumps({'ok' : True}), content_type='text/json')
    else:
        HttpResponse(json.dumps({'ok' : False}), content_type='text/json')

def clear_segments(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    sure = request.GET.get('sure')
    if sure == 'yes':
        Segment.objects.filter(stack = s).delete()
        return HttpResponse(json.dumps({'ok' : True}), content_type='text/json')
    else:
        HttpResponse(json.dumps({'ok' : False}), content_type='text/json')

def clear_blocks(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    sure = request.GET.get('sure')
    if sure == 'yes':
        Block.objects.filter(stack = s).delete()
        Core.objects.filter(stack = s).delete()
        BlockInfo.objects.filter(stack = s).delete()
        return HttpResponse(json.dumps({'ok' : True}), content_type='text/json')
    else:
        HttpResponse(json.dumps({'ok' : False}), content_type='text/json')

def clear_djsopnet(request, project_id = None, stack_id = None):
    sure = request.GET.get('sure')
    if sure == 'yes':
        _clear_djsopnet(project_id, stack_id)
        return HttpResponse(json.dumps({'ok': True}), content_type='text/json')
    else:
        return HttpResponse(json.dumps({'ok': False}), content_type='text/json')

def _clear_djsopnet(segmentation_stack_id=None, delete_slices=True,
        delete_segments=True):
    segmentation_stack_id = int(segmentation_stack_id)
    s = get_object_or_404(SegmentationStack, pk=segmentation_stack_id)
    delete_config = delete_slices and delete_segments

    cursor = connection.cursor()

    # TODO: Assemblies are no longer cleared, but this function will be
    # deprecated soon.

    if delete_slices:
        cursor.execute('TRUNCATE TABLE segstack_%s.slice CASCADE;' % segmentation_stack_id)
        cursor.execute('UPDATE segstack_%s.block SET slices_flag = FALSE;' % segmentation_stack_id)

    if delete_segments:
        cursor.execute('TRUNCATE TABLE segstack_%s.segment CASCADE;' % segmentation_stack_id)
        cursor.execute('UPDATE segstack_%s.block SET segments_flag = FALSE;' % segmentation_stack_id)

    if delete_config:
        cursor.execute('TRUNCATE TABLE segstack_%s.block CASCADE;' % segmentation_stack_id)
        cursor.execute('TRUNCATE TABLE segstack_%s.core CASCADE;' % segmentation_stack_id)

def get_task_list(request):
    """ Retrieves a list of all tasks that are currently processed.
    """
    tasks = TaskState.objects.all()

    task_data = [{
      'task_id': t.task_id,
      'state': t.state,
      'name': t.name,
    } for t in tasks]

    return HttpResponse(json.dumps(task_data))

def create_project_config(configuration_id):
    """
    Creates a configuration dictionary for Sopnet.
    """
    pc = get_object_or_404(SegmentationConfiguration, pk=configuration_id)
    config = {'catmaid_project_id': pc.project_id, 'catmaid_stack_ids': {}}
    for segstack in pc.segmentationstack_set.all():
        config['catmaid_stack_ids'][segstack.type] = {
            'id': segstack.project_stack.stack.id,
            'segmentation_id': segstack.id
        }

    bi = pc.block_info

    config['catmaid_stack_scale'] = bi.scale
    config['block_size'] = [bi.block_dim_x, bi.block_dim_y, bi.block_dim_z]
    config['core_size'] = [bi.core_dim_x, bi.core_dim_y, bi.core_dim_z]
    config['volume_size'] = [bi.block_dim_x*bi.num_x,
                             bi.block_dim_y*bi.num_y,
                             bi.block_dim_z*bi.num_z]

    optional_params = [
            'backend_type', 'catmaid_host', 'component_dir', 'loglevel',
            'postgresql_database', 'postgresql_host', 'postgresql_port',
            'postgresql_user', 'postgresql_password']
    for param_name in optional_params:
        settings_attr = 'SOPNET_%s' % param_name.upper()
        if hasattr(settings, settings_attr):
            config[param_name] = getattr(settings, settings_attr)

    return config

def test_sliceguarantor_task(request, pid, raw_sid, membrane_sid, x, y, z):
    config = create_project_config(pid, raw_sid, membrane_sid)
    async_result = SliceGuarantorTask.delay(config, x, y, z)
    return HttpResponse(json.dumps({
        'success': "Successfully queued slice guarantor task.",
        'task_id': async_result.id
    }))

def test_segmentguarantor_task(request, pid, raw_sid, membrane_sid, x, y, z):
    config = create_project_config(pid, raw_sid, membrane_sid)
    async_result = SegmentGuarantorTask.delay(config, x, y, z)
    return HttpResponse(json.dumps({
        'success': "Successfully queued segment guarantor task.",
        'task_id': async_result.id
    }))

def test_solutionguarantor_task(request, pid, raw_sid, membrane_sid, x, y, z):
    config = create_project_config(pid, raw_sid, membrane_sid)
    async_result = SolutionGuarantorTask.delay(config, x, y, z)
    return HttpResponse(json.dumps({
        'success': "Successfully queued solution guarantor task.",
        'task_id': async_result.id
    }))

@requires_user_role(UserRole.Annotate)
def solve_core(request, project_id, segmentation_stack_id, core_id):
    """Solve a core synchronously"""
    segstack = get_object_or_404(SegmentationStack, id=segmentation_stack_id)
    cursor = connection.cursor()
    cursor.execute('''
        SELECT * FROM segstack_{0}.core WHERE id = %s LIMIT 1
        '''.format(segstack.id), core_id)
    c = _blockcursor_to_namedtuple(cursor, segstack.configuration.block_info.size_for_unit('core'))[0]
    # SolutionGuarantor does not need to know membrane stack ID
    config = create_project_config(segstack.configuration_id)
    result = SolutionGuarantorTask.apply([config, c.coordinate_x, c.coordinate_y, c.coordinate_z, False])
    return HttpResponse(json.dumps({
        'success': result.result
    }))

def test_solvesubvolume_task(request):
    async_result = SolveSubvolumeTask.delay()
    return HttpResponse(json.dumps({
        'success': "Successfully queued solve subvolume task.",
        'task_id': async_result.id
    }))

def test_traceneuron_task(request):
    async_result = TraceNeuronTask.delay()
    return HttpResponse(json.dumps({
        'success': "Successfully queued trace task.",
        'task_id': async_result.id
    }))
