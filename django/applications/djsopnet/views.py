import json
import math
import os
import sys

from collections import namedtuple
import networkx as nx
from numpy import int64, uint64
from pgmagick import Image, Blob, Color, CompositeOperator

import pysopnet

from django.http import HttpResponse

from django.shortcuts import get_object_or_404
from django.db import connection
from django.db import IntegrityError
from django.conf import settings
from django.templatetags.static import static

from catmaid.models import *
from catmaid.control.stack import get_stack_info
from catmaid.control.authentication import requires_user_role
from models import *

from celery.task.control import inspect

from celerysopnet.tasks import SliceGuarantorTask, SegmentGuarantorTask
from celerysopnet.tasks import SolutionGuarantorTask, SolveSubvolumeTask
from celerysopnet.tasks import TraceNeuronTask

from djcelery.models import TaskState

from StringIO import StringIO
import traceback

from djsopnet.control.slice import retrieve_slices_for_skeleton
from djsopnet.control.skeleton_intersection import generate_user_constraints

def safe_split(tosplit, name='data', delim=','):
    """ Tests if $tosplit evaluates to true and if not, raises a value error.
    Otherwise, it the result of splitting it is returned.
    """
    if not tosplit:
        raise ValueError("No %s provided" % name)
    return tosplit.split(delim)


def hash_to_id(hash_uint64):
    """ Casts a string or uint representation of an unsigned 64-bit hash value
    to a signed long long value that matches Postgres' bigint. E.g.,
      >>> hash_to_id("9223372036854775808")
      -9223372036854775808
    """
    return int64(uint64(hash_uint64))


def id_to_hash(id_int64):
    """ Casts a string or int representation of an signed 64-bit hash value to a
    unsigned long value that matches sopnet's size_t hash,
      >>> id_to_hash("-9223372036854775808")
      9223372036854775808
    """
    return str(uint64(int64(id_int64)))

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
        summary.update({'segment_id': id_to_hash(summary['segment_id'])})

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
    size = block.stack.blockinfo
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

def block_info_dict(block_info, stack):
    bid = {'block_size' : [block_info.block_dim_x, block_info.block_dim_y, block_info.block_dim_z],
           'count' : [block_info.num_x, block_info.num_y, block_info.num_z],
           'core_size' : [block_info.core_dim_x, block_info.core_dim_y, block_info.core_dim_z],
           'stack_size' : [stack.dimension.x, stack.dimension.y, stack.dimension.z]}
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


def generate_block_info_response(block_info, stack):
    if block_info:
        return HttpResponse(json.dumps(block_info_dict(block_info, stack)), content_type = 'text/json')
    else:
        return HttpResponse(json.dumps({'id' : None}), content_type = 'text/json')

def generate_conflict_response(conflicts, stack):
    conflict_dicts = []
    for conflict in conflicts:
        rel = SliceConflict.objects.get(id = conflict)
        conflict_dicts.append({'conflict_hashes' : map(id_to_hash, [rel.slice_a_id, rel.slice_b_id])})
    return HttpResponse(json.dumps({'ok' : True, 'conflict' : conflict_dicts}))

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

# --- Blocks and Cores ---
def setup_blocks(request, project_id = None, stack_id = None):
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
        _setup_blocks(stack_id, scale, width, height, depth,
                      corewib, corehib, coredib)
    except ValueError as e:
        return HttpResponse(json.dumps({'ok': False, 'reason' : str(e)}), content_type='text/json')

    return HttpResponse(json.dumps({'ok': True}), content_type='text/json')

def _setup_blocks(stack_id, scale, width, height, depth, corewib, corehib, coredib):
    s = get_object_or_404(Stack, pk=stack_id)

    # The number of blocks is the ceiling of the stack size divided by block dimension
    def int_ceil(num, den): return ((num - 1) // den) + 1
    nx = int_ceil(s.dimension.x, width * 2**scale)
    ny = int_ceil(s.dimension.y, height * 2**scale)
    nz = int_ceil(s.dimension.z, depth * 2**scale)

    try:
        info = BlockInfo.objects.get(stack=s)
        raise ValueError("already setup")
    except BlockInfo.DoesNotExist:

        info = BlockInfo(stack=s, scale=scale,
                         block_dim_y = height, block_dim_x = width, block_dim_z = depth,
                         core_dim_y = corehib, core_dim_x = corewib, core_dim_z = coredib,
                         num_x = nx, num_y = ny, num_z = nz)
        info.save()

    # Create new Blocks
    blocks = []
    for z in range(0, nz):
        for y in range(0, ny):
            for x in range(0, nx):
                blocks.append(Block(stack=s, slices_flag=False, segments_flag=False,
                                    coordinate_x=x, coordinate_y=y, coordinate_z=z))
    Block.objects.bulk_create(blocks)

    # Create new Cores, round up if number of blocks is not divisible by core size
    cores = []
    for z in range(0, (nz + coredib - 1)/coredib):
        for y in range(0, (ny + corehib - 1)/corehib):
            for x in range(0, (nx + corewib - 1)/corewib):
                cores.append(Core(stack=s, solution_set_flag = False,
                                  coordinate_x=x, coordinate_y=y, coordinate_z=z))
    Core.objects.bulk_create(cores)

# Query, agnostic to Model class for Core, Block
def location_query(model, s, request):
    x = int(float(request.GET.get('x')))
    y = int(float(request.GET.get('y')))
    z = int(float(request.GET.get('z')))
    size = model.size_for_stack(s)
    return model.objects.get(stack = s,
                      coordinate_x = math.floor(x/size['x']),
                      coordinate_y = math.floor(y/size['y']),
                      coordinate_z = math.floor(z/size['z']))

def bound_query(model, s, request):
    xmin = int(request.GET.get('xmin', -1))
    ymin = int(request.GET.get('ymin', -1))
    zmin = int(request.GET.get('zmin', -1))
    width = int(request.GET.get('width', 0))
    height = int(request.GET.get('height', 0))
    depth = int(request.GET.get('depth', 0))

    xmax = xmin + width
    ymax = ymin + height
    zmax = zmin + depth
    size = model.size_for_stack(s)
    return model.objects.filter(stack = s,
                                coordinate_x__gt = math.floor(xmin),
                                coordinate_y__gt = math.floor(ymin),
                                coordinate_z__gt = math.floor(zmin),
                                coordinate_x__lt = math.ceil(xmax),
                                coordinate_y__lt = math.ceil(ymax),
                                coordinate_z__lt = math.ceil(zmax))

def block_at_location(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk=stack_id)
    try:
        block = location_query(Block, s, request)
        return generate_block_response(block)
    except Block.DoesNotExist:
        return generate_block_response(None)

def blocks_in_bounding_box(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk=stack_id)
    blocks = bound_query(Block, s, request)

    return generate_blocks_response(blocks)

def core_at_location(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk=stack_id)
    try:
        core = location_query(Core, s, request)
        return generate_core_response(core)
    except Core.DoesNotExist:
        return generate_core_response(None)

def cores_in_bounding_box(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk=stack_id)
    cores = bound_query(Core, s, request)
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

def block_info(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk=stack_id)
    try:
        block_info = BlockInfo.objects.get(stack = s)
        print >> sys.stderr, 'got block info'
        return generate_block_info_response(block_info, s)
    except BlockInfo.DoesNotExist:
        print >> sys.stderr, 'found no stack info for that stack'
        return generate_block_info_response(None, None)

def set_flag(s, request, flag_name, id_field = 'block_id', type = Block):
    id = int(request.GET.get(id_field))
    flag = int(request.GET.get('flag'))
    try:
        box = type.objects.get(stack = s, id = id)
        setattr(box, flag_name, flag)
        box.save()
        return HttpResponse(json.dumps({'ok' : True}), content_type='text/json')
    except type.DoesNotExist:
        return HttpResponse(json.dumps({'ok' : False}), content_type='text/json')

def get_flag(s, request, flag_name, id_field = 'block_id', type = Block):
    id = int(request.GET.get(id_field))
    try:
        box = type.objects.get(stack = s, id = id)
        flag = getattr(box, flag_name)
        return HttpResponse(json.dumps({flag_name : flag}), content_type='text/json')
    except type.DoesNotExist:
        return HttpResponse(json.dumps({flag_name : False, 'ok' : False}), content_type='text/json')

def set_block_slice_flag(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk=stack_id)
    return set_flag(s, request, 'slices_flag')

def set_block_segment_flag(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk=stack_id)
    return set_flag(s, request, 'segments_flag')

def set_block_solution_flag(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk=stack_id)
    return set_flag(s, request, 'solution_cost_flag')

def set_core_solution_flag(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk=stack_id)
    return set_flag(s, request, 'solution_set_flag', 'core_id', Core)

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
                  ctr_x = ctr_x, ctr_y = ctr_y, value = value,
                  shape_x = [], shape_y = [], size = size)
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

def _slice_select_query(slice_id_query):
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
              ARRAY_AGG(DISTINCT ssol.core_id) AS in_solution_core_ids,
              ARRAY_AGG(DISTINCT ssol.assembly_id) AS in_solution_assembly_ids
            FROM djsopnet_slice s
            JOIN (%s) AS slice_id_query
              ON (slice_id_query.slice_id = s.id)
            LEFT JOIN djsopnet_sliceconflict scs_as_a ON (scs_as_a.slice_a_id = s.id)
            LEFT JOIN djsopnet_sliceconflict scs_as_b ON (scs_as_b.slice_b_id = s.id)
            JOIN djsopnet_segmentslice ss ON (ss.slice_id = s.id)
            LEFT JOIN
              (SELECT ssol.segment_id, ssol.solution_id, ssol.assembly_id, sp.core_id
                  FROM djsopnet_segmentsolution ssol
                  JOIN djsopnet_solutionprecedence sp ON sp.solution_id = ssol.solution_id)
              AS ssol
                ON (ssol.segment_id = ss.segment_id)
            GROUP BY s.id
            ''' % slice_id_query

def _slicecursor_to_namedtuple(cursor):
    """Create a namedtuple list stubbing for Slice objects from a cursor.

    Assumes the cursor has been executed and has at least the following columns:
    conflicts_as_a, conflicts_as_b, in_solution_core_ids, segment_summaries.
    """
    cols = [col[0] for col in cursor.description]

    SliceTuple = namedtuple('SliceTuple', cols + ['conflict_slice_ids', 'in_solution'])

    def slicerow_to_namedtuple(row):
        rowdict = dict(zip(cols, row))
        # In PostgreSQL 9.4 it will be possible to preserve column names in JSON
        # aggregated ROW columns without subqueries or CTEs. For now manually
        # map from default field names to original column names.
        segment_map = {'f1': 'segment_id', 'f2': 'direction'}
        rowdict.update({
                'conflict_slice_ids': filter(None, rowdict['conflicts_as_a'] + rowdict['conflicts_as_b']),
                'in_solution': rowdict['in_solution_assembly_ids'] if any(rowdict['in_solution_core_ids']) else False,
                'segment_summaries': [
                    {segment_map[k]: v for k,v in summary.items()}
                    for summary in json.loads(rowdict['segment_summaries'])
                ]
            })
        return SliceTuple(**rowdict)

    return [slicerow_to_namedtuple(row) for row in cursor.fetchall()]

def retrieve_slices_by_blocks_and_conflict(request, project_id = None, stack_id = None):
    """Retrieve slices and slices in conflict sets for a set of blocks.

    Retrieve Slices associated to the Blocks with the given ids or to any
    ConflictSet that is associated with those Blocks.
    """
    s = get_object_or_404(Stack, pk = stack_id)
    try:
        block_ids = ','.join([str(int(id)) for id in safe_split(request.POST.get('block_ids'), 'block IDs')])

        cursor = connection.cursor()
        cursor.execute(_slice_select_query('''
                SELECT sbr.slice_id
                  FROM djsopnet_sliceblockrelation sbr
                  WHERE sbr.block_id IN (%(block_ids)s)
                UNION SELECT scs_cbr_a.slice_a_id AS slice_id
                  FROM djsopnet_blockconflictrelation bcr
                  JOIN djsopnet_sliceconflict scs_cbr_a ON (scs_cbr_a.id = bcr.slice_conflict_id)
                  WHERE bcr.block_id IN (%(block_ids)s)
                UNION SELECT scs_cbr_b.slice_b_id AS slice_id
                  FROM djsopnet_blockconflictrelation bcr
                  JOIN djsopnet_sliceconflict scs_cbr_b ON (scs_cbr_b.id = bcr.slice_conflict_id)
                  WHERE bcr.block_id IN (%(block_ids)s)
                ''' % {'block_ids': block_ids}))

        slices = _slicecursor_to_namedtuple(cursor)

        return generate_slices_response(slices=slices,
                with_conflicts=True, with_solutions=True)
    except:
        return error_response()

def retrieve_slices_by_location(request, project_id=None, stack_id=None):
    """Retrieve slices and their conflicts for a given location in stack coordinates."""
    s = get_object_or_404(Stack, pk=stack_id)
    try:
        x = int(float(request.POST.get('x', None)))
        y = int(float(request.POST.get('y', None)))
        z = int(float(request.POST.get('z', None)))

        cursor = connection.cursor()
        cursor.execute(_slice_select_query('''
                SELECT s.id AS slice_id
                  FROM djsopnet_slice s
                  WHERE s.section = %(z)s
                    AND s.min_x <= %(x)s
                    AND s.max_x >= %(x)s
                    AND s.min_y <= %(y)s
                    AND s.max_y >= %(y)s
                ''' % {'z': z, 'x': x, 'y': y}))

        slices = _slicecursor_to_namedtuple(cursor)

        return generate_slices_response(slices=slices,
                with_conflicts=True, with_solutions=True)
    except:
        return error_response()

def retrieve_slices_by_bounding_box(request, project_id=None, stack_id=None):
    s = get_object_or_404(Stack, pk=stack_id)
    try:
        min_x = int(float(request.POST.get('min_x', None)))
        min_y = int(float(request.POST.get('min_y', None)))
        max_x = int(float(request.POST.get('max_x', None)))
        max_y = int(float(request.POST.get('max_y', None)))
        z = int(float(request.POST.get('z', None)))

        cursor = connection.cursor()
        cursor.execute(_slice_select_query('''
                SELECT s.id AS slice_id
                  FROM djsopnet_segmentsolution ssol
                  JOIN djsopnet_solutionprecedence sp ON (sp.solution_id = ssol.solution_id)
                  JOIN djsopnet_segmentslice ss ON (ss.segment_id = ssol.segment_id)
                  JOIN djsopnet_slice s ON (s.id = ss.slice_id)
                  WHERE s.section = %(z)s
                    AND s.min_x <= %(max_x)s
                    AND s.max_x >= %(min_x)s
                    AND s.min_y <= %(max_y)s
                    AND s.max_y >= %(min_y)s
                ''' % {'z': z, 'max_x': max_x, 'min_x': min_x, 'max_y': max_y, 'min_y': min_y}))

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

def retrieve_conflict_sets(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    try:
        slice_ids = map(hash_to_id, safe_split(request.POST.get('hash'), 'slice hashes'))

        conflict_relations = SliceConflict.objects.filter(slice_a__in = slice_ids) | \
                             SliceConflict.objects.filter(slice_b__in = slice_ids)
        conflicts = {cr.id for cr in conflict_relations}

        return generate_conflict_response(conflicts, s)
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

def retrieve_segment_and_conflicts(request, project_id = None, stack_id = None):
    """
    Retrieve a segment (or set of co-section conflicting segments), its slices,
    their first-order conflict slices, and segments involving these slices in
    the same section.
    """
    s = get_object_or_404(Stack, pk=stack_id)
    try:
        segment_id = ','.join([str(hash_to_id(x)) for x in safe_split(request.POST.get('hash'), 'segment hashes')])

        cursor = connection.cursor()
        cursor.execute(('''
                WITH req_seg_slices AS (
                    SELECT slice_id FROM djsopnet_segmentslice
                      WHERE segment_id IN (%(segment_id)s))
                ''' % {'segment_id': segment_id}) + \
                _slice_select_query('''
                        SELECT ss2.slice_id
                            FROM djsopnet_segmentslice ss1
                            JOIN djsopnet_segment ss1_seg
                                ON (ss1.segment_id = ss1_seg.id
                                    AND ss1_seg.section_sup = (
                                        SELECT section_sup FROM djsopnet_segment
                                        WHERE id IN (%(segment_id)s) LIMIT 1))
                            JOIN djsopnet_segmentslice ss2
                                ON (ss2.segment_id = ss1.segment_id)
                            WHERE ss1.slice_id IN
                                (SELECT slice_id FROM req_seg_slices
                                UNION SELECT scs_a.slice_a_id AS slice_id
                                  FROM djsopnet_sliceconflict scs_a, req_seg_slices
                                  WHERE scs_a.slice_b_id = req_seg_slices.slice_id
                                UNION SELECT scs_b.slice_b_id AS slice_id
                                  FROM djsopnet_sliceconflict scs_b, req_seg_slices
                                  WHERE scs_b.slice_a_id = req_seg_slices.slice_id)
                        ''' % {'segment_id': segment_id}))

        slices = _slicecursor_to_namedtuple(cursor)

        expanded_segment_ids = sum([
            [summary['segment_id'] for summary in slice.segment_summaries]
            for slice in slices if slice.segment_summaries], [])

        segments = Segment.objects.filter(stack=s, id__in=expanded_segment_ids)

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
def create_segment_for_slices(request, project_id=None, stack_id=None):
    """Creates a segment joining a specified set of slices. Ends must specify section supremum."""
    s = get_object_or_404(Stack, pk=stack_id)
    try:
        slice_ids = map(hash_to_id, safe_split(request.POST.get('hash'), 'slice hashes'))
        if len(slice_ids) == 0:
            return HttpResponseBadRequest(json.dumps({'error': 'Must specify at least one slices for a segment'}), content_type='application/json')

        slices = Slice.objects.filter(stack=s, id__in=slice_ids)
        if len(slices) != len(slice_ids):
            return HttpResponseBadRequest(json.dumps({'error': 'Segment referes to non-existent slices'}), content_type='application/json')

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
        if Segment.objects.filter(id=segment_id).exists():
            return HttpResponse(json.dumps(
                    {'error': 'Segment already exists with hash: %s id: %s' % (segment_hash, segment_id)}),
                    status=409, content_type='application/json')

        type = len(slices) - 1
        segment = Segment(id=segment_id, stack=s, section_sup=section_sup,
                type=type, ctr_x=ctr_x, ctr_y=ctr_y,
                min_x=min_x, min_y=min_y, max_x=max_x, max_y=max_y)
        segment.save()

        # Associate slices to segment
        SegmentSlice.objects.bulk_create([
            SegmentSlice(segment=segment, slice=slice, direction=(slice.section != section_sup))
            for slice in slices])

        # Associate segment to blocks
        slice_block_relations = SliceBlockRelation.objects.filter(slice__in=slices)
        block_ids = frozenset([sbr.block_id for sbr in slice_block_relations])
        SegmentBlockRelation.objects.bulk_create([
            SegmentBlockRelation(segment=segment, block_id=block_id)
            for block_id in block_ids])

        return generate_segment_response(segment)
    except:
        return error_response()

@requires_user_role(UserRole.Annotate)
def constrain_segment(request, project_id=None, stack_id=None, segment_hash=None):
    try:
        segment_id = hash_to_id(segment_hash)

        segment = get_object_or_404(Segment, pk=segment_id)
        constraint = Constraint(project_id=project_id, user=request.user, relation='Equal', value=1.0)
        constraint.save()
        csr = ConstraintSegmentRelation(constraint=constraint, segment=segment, coefficient=1.0)
        csr.save()

        BlockConstraintRelation.objects.bulk_create([
            BlockConstraintRelation(constraint=constraint, block_id=sbr.block_id)
            for sbr in segment.segmentblockrelation_set.all()])

        # Mark explicitly conflicting segments (segments with slices in conflict
        # sets with the constrained segment, or segments in the same section
        # with slices in common with the constrained segment) as mistakes being
        # corrected. The latter condition is needed to mark end segments, which
        # may not involve a conflicting slice.
        cursor = connection.cursor()
        cursor.execute('''
            WITH req_seg_slices AS (
                SELECT slice_id, direction FROM djsopnet_segmentslice
                  WHERE segment_id = %(segment_id)s)
            INSERT INTO djsopnet_correction (constraint_id, mistake_id)
            SELECT c.id, conflict.id FROM (VALUES (%(constraint_id)s)) AS c (id),
                (SELECT DISTINCT ssol.id AS id FROM djsopnet_solutionprecedence sp
                    JOIN djsopnet_segmentsolution ssol
                      ON (sp.solution_id = ssol.solution_id AND ssol.segment_id <> %(segment_id)s)
                    JOIN djsopnet_segmentslice ss ON (ssol.segment_id = ss.segment_id)
                    WHERE ss.slice_id IN (
                            SELECT scs_a.slice_a_id AS slice_id
                              FROM djsopnet_sliceconflict scs_a, req_seg_slices
                              WHERE scs_a.slice_b_id = req_seg_slices.slice_id
                            UNION SELECT scs_b.slice_b_id AS slice_id
                              FROM djsopnet_sliceconflict scs_b, req_seg_slices
                              WHERE scs_b.slice_a_id = req_seg_slices.slice_id)
                      OR ((ss.slice_id, ss.direction) IN (SELECT * FROM req_seg_slices)))
                    AS conflict
            ''' % {'segment_id': segment_id, 'constraint_id': constraint.id})

        return HttpResponse(json.dumps({'ok': True, 'constraint_id': constraint.id}), content_type='text/json')
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

# --- Assembly ---

@requires_user_role(UserRole.Annotate)
def generate_assemblies_for_core(request, project_id=None, stack_id=None, core_id=None):
    c = get_object_or_404(Core, id=core_id)
    if not c.solution_set_flag:
        return HttpResponse(json.dumps(
                {'error': 'Solution flag is not set for core'}),
                status=409, content_type='application/json')

    cursor = connection.cursor()
    # Fetch all segments and the segments to which they are connected in the
    # core's precedent solution.
    cursor.execute('''
        SELECT
          ssol.segment_id AS segment_id,
          ARRAY_TO_JSON(ARRAY_AGG(DISTINCT ss2.segment_id)) AS segment_neighbors,
          ssol.id AS ssol_id
        FROM djsopnet_segmentsolution ssol
        JOIN djsopnet_solutionprecedence sp
          ON (sp.solution_id = ssol.solution_id AND sp.core_id = %s)
        JOIN djsopnet_segmentslice ss
          ON (ss.segment_id = ssol.segment_id)
        JOIN djsopnet_segmentslice ss2
          ON (ss2.slice_id = ss.slice_id
              AND ss2.segment_id <> ss.segment_id
              AND ss2.direction <> ss.direction)
        JOIN djsopnet_segmentsolution ssol2
          ON (ssol2.segment_id = ss2.segment_id AND ssol2.solution_id = ssol.solution_id)
        GROUP BY ssol.segment_id, ssol.id
        ''' % core_id)
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
        INSERT INTO djsopnet_assembly (user_id, creation_time, edition_time)
        SELECT v.user_id, v.creation_time, v.edition_time
        FROM (VALUES (%(user_id)s, TIMESTAMP '%(creation_time)s', TIMESTAMP '%(edition_time)s'))
          AS v (user_id, creation_time, edition_time), generate_series(1, %(num_assemblies)s)
        RETURNING djsopnet_assembly.id
        ''' % {'user_id': request.user.id,
               'creation_time': datetime.now(),
               'edition_time': datetime.now(),
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

    return HttpResponse(json.dumps({'ok' : True}), content_type='text/json')

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

def _clear_djsopnet(project_id = None, stack_id = None, delete_slices=True,
        delete_segments=True):
    s = get_object_or_404(Stack, pk = stack_id)
    delete_config = delete_slices and delete_segments

    all_blocks = Block.objects.filter(stack = s)
    all_segments = Segment.objects.filter(stack = s)

    # TODO: Assemblies are no longer cleared, but this function will be
    # deprecated soon.

    if delete_slices:
        all_block_conflict_relations = BlockConflictRelation.objects.filter(block__in = all_blocks)
        all_conflicts = {bcr.slice_conflict for bcr in all_block_conflict_relations}
        SliceConflict.objects.filter(id__in = (conflict.id for conflict in all_conflicts)).delete()

    if delete_segments:
        SegmentBlockRelation.objects.filter(block__in = all_blocks).delete()
        SegmentFeatures.objects.filter(segment__in = all_segments).delete()
        SegmentSolution.objects.filter(segment__in = all_segments).delete()

    if delete_config:
        all_blocks.delete()

    if delete_segments:
        all_segments.delete()

    if delete_slices:
        Slice.objects.filter(stack = s).delete()

    if delete_config:
        Core.objects.filter(stack = s).delete()
        BlockInfo.objects.filter(stack = s).delete()

    if delete_slices:
        Block.objects.filter(stack=s).update(slices_flag=False)

    if delete_segments:
        Block.objects.filter(stack=s).update(segments_flag=False)

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

def create_project_config(project_id, raw_stack_id, membrane_stack_id):
    """
    Creates a configuration dictionary for Sopnet.
    """
    config = {
        'catmaid_project_id': project_id,
        'catmaid_raw_stack_id': raw_stack_id,
        'catmaid_membrane_stack_id': membrane_stack_id,
    }

    bi = BlockInfo.objects.get(stack_id=raw_stack_id)

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
