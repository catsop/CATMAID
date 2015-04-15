import json
import math
from collections import namedtuple

from django.db import connection
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from djsopnet.models import BlockInfo, SegmentationStack


def block_dict(block):
    bd = {'id': block.id,
          'slices': block.slices_flag,
          'segments': block.segments_flag,
          'box': block.box}
    return bd


def core_dict(core):
    bd = {'id': core.id,
          'solutions': core.solution_set_flag,
          'box': core.box}
    return bd


def block_info_dict(block_info):
    bid = {'block_size': [block_info.block_dim_x, block_info.block_dim_y, block_info.block_dim_z],
           'count': [block_info.num_x, block_info.num_y, block_info.num_z],
           'core_size': [block_info.core_dim_x, block_info.core_dim_y, block_info.core_dim_z],
           'scale': block_info.scale}
    return bid


def generate_block_response(block):
    if block:
        return HttpResponse(json.dumps(block_dict(block)), content_type='text/json')
    else:
        return HttpResponse(json.dumps({'id': None}), content_type='text/json')


def generate_blocks_response(blocks):
    if blocks is not None:
        block_dicts = [block_dict(block) for block in blocks]
        return HttpResponse(json.dumps({'ok': True, 'length': len(block_dicts), 'blocks': block_dicts}))
    else:
        return HttpResponse(json.dumps({'ok': True, 'length': 0}))


def generate_core_response(core):
    if core:
        return HttpResponse(json.dumps(core_dict(core)), content_type='text/json')
    else:
        return HttpResponse(json.dumps({'id': None}), content_type='text/json')


def generate_cores_response(cores):
    if cores is not None:
        core_dicts = [core_dict(core) for core in cores]
        return HttpResponse(json.dumps({'length': len(core_dicts), 'cores' : core_dicts}))
    else:
        return HttpResponse(json.dumps({'length': 0}))


def generate_block_info_response(block_info):
    return HttpResponse(json.dumps(block_info_dict(block_info)), content_type='text/json')


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
        return HttpResponse(json.dumps({'ok': False, 'reason': 'malformed'}), content_type='text/json')
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
                         block_dim_y=height, block_dim_x=width, block_dim_z=depth,
                         core_dim_y=corehib, core_dim_x=corewib, core_dim_z=coredib,
                         num_x=nx, num_y=ny, num_z=nz)
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
                'box': [s*c for s, c in zip(size, coords)] + [s*(c+1) for s,c in zip(size, coords)]
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


def block_info(request, configuration_id=None):
    block_info = get_object_or_404(BlockInfo, configuration_id=configuration_id)
    return generate_block_info_response(block_info)
