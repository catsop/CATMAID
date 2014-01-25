import json
import time

from django.http import HttpResponse

from django.shortcuts import get_object_or_404

from catmaid.models import *
from catmaid.control.stack import get_stack_info

# --- JSON conversion ---
def slice_dict(slice):
    sd = {'id' : slice.id,
          'assembly' : slice.assembly,
          'hash' : slice.hash_value,
          'section' : slice.section,
          'box' : [slice.min_x, slice.min_y, slice.max_x, slice.max_y],
          'ctr' : [slice.ctr_x, slice.ctr_y],
          'value' : slice.value,
          'x' : slice.shape_x,
          'y' : slice.shape_y,
          'parent' : slice.parent.id}
    return sd

def segment_dict(segment):
    sd = {'id' : segment.id,
          'assembly' : segment.assembly,
          'hash' : segment.hash_value,
          'section' : segment.section_inf,
          'box' : [segment.min_x, segment.min_y, segment.max_x, segment.max_y],
          'ctr' : [segment.ctr_x, segment.ctr_y],
          'type' : segment.type,
          'slice_a' : segment.slice_a.id,
          'slice_b' : -1,
          'slice_c' : -1}

    if segment.slice_b:
        sd['slice_b'] = segment.slice_b.id
    if segment.slice_c:
        sd['slice_c'] = segment.slice_c.id

    return sd

def block_dict(block):
    bd = {'id' : block.id,
          'box' : [block.min_x, block.min_y, block.min_z,
                   block.max_x, block.max_y, block.max_z]}
    return bd

def block_info_dict(block_info):
    bid = {'size' : [block_info.height, block_info.width, block_info.depth],
           'count' : [block_info.num_x, block_info.num_y, block_info.num_z]}
    return bid

def generate_slice_response(slice):
    if slice:
        return HttpResponse(json.dumps(slice_dict(slice)), mimetype = 'text/json')
    else:
        return HttpResponse(json.dumps({'id' : -1}), mimetype = 'text/json')

def generate_segment_response(segment):
    if segment:
        return HttpResponse(json.dumps(segment_dict(segment)), mimetype = 'text/json')
    else:
        return HttpResponse(json.dumps({'id' : -1}), mimetype = 'text/json')


def generate_slices_response(slices):
    slice_list = [slice_dict(slice) for slice in slices]
    return HttpResponse(json.dumps({'slices' : slice_list}), mimetype = 'text/json')

def generate_segments_response(segments):
    segment_list = [segment_dict(segment) for segment in segments]
    return HttpResponse(json.dumps({'segments' : segment_list}), mimetype = 'text/json')

def generate_block_response(block):
    if block:
        return HttpResponse(json.dumps(block_dict(block)), mimetype = 'text/json')
    else:
        return HttpResponse(json.dumps({'id' : -1}), mimetype = 'text/json')

def generate_block_info_response(block_info):
    if block_info:
        return HttpResponse(json.dumps(block_info_dict(block_info)), mimetype = 'text/json')
    else:
        return HttpResponse(json.dumps({'id' : -1}), mimetype = 'text/json')

1

# --- Blocks ---

def setup_blocks(request, project_id = None, stack_id = None):
    '''
    Initialize and store the blocks and block info in the db, associated with
    the given stack, if these things don't already exist.
    '''

    width = int(request.POST.get('width'))
    height = int(request.POST.get('height'))
    depth = int(request.POST.get('depth'))

    s = get_object_or_404(Stack, pk=stack_id)
    nx = s.dimension.x / width;
    ny = s.dimension.y / height;
    nz = s.dimension.z / depth;

    # If stack size is not equally divisible by block size...
    if nx * width < s.dimension.z:
        nx = nx + 1;

    if ny * height < s.dimension.y:
        ny = ny + 1;

    if nz * depth < s.dimension.z:
        nz = nz + 1;

    try:
        info = BlockInfo.objects.get(stack=s)
        return HttpResponse(json.dumps({'ok': False}), mimetype='text/json')
    except BlockInfo.DoesNotExist:

        info = BlockInfo(stack = s, height = height, width = width, depth = depth,
                         num_x = nx, num_y = ny, num_z = nz)
        info.save();


    for z in range(0, s.dimension.z, depth):
        for y in range(0, s.dimension.y, height):
            for x in range(0, s.dimension.x, width):
                block = Block(stack=s, min_x = x, min_y = y, min_z = z,
                              max_x = x + width, max_y = y + height, max_z = z + depth,
                              slices = [], segments = [], slices_flag)
                block.save();
    return HttpResponse(json.dumps({'ok': True}), mimetype='text/json')

def block_at_location(request, project_id = None, stack_id = None):

    x = int(request.POST.get('x'))
    y = int(request.POST.get('y'))
    z = int(request.POST.get('z'))

    s = get_object_or_404(Stack, pk=stack_id)
    try:
        # Block are closed-open, thus lte/gt
        block = Block.objects.get(stack = s,
                                 min_x__lte = x,
                                 min_y__lte = y,
                                 min_z__lte = z,
                                 max_x__gt = x,
                                 max_y__gt = y,
                                 max_z__gt = z)
        return generate_block_response(block)
    except:
        return generate_block_response(None)


def block_info(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk=stack_id)
    try:
        block_info = BlockInfo.objects.get(stack = s)
        return generate_block_info_response(block_info)
    except:
        return generate_block_info_response(None)

def set_block_slice_flag(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk=stack_id)
    block_id = int(request.POST.get('block_id'))
    flag = int(request.POST.get('flag'))
    try:
        block = Block.objects.get(stack = s, id = block_id)
        block.slices_flag = flag
        block.save()
        return HttpResponse(json.dumps({'ok': True}), mimetype='text/json')
    except:
        HttpResponse(json.dumps({'ok': False}), mimetype='text/json')

def set_block_segment_flag(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk=stack_id)
    block_id = int(request.POST.get('block_id'))
    flag = int(request.POST.get('flag'))
    try:
        block = Block.objects.get(stack = s, id = block_id)
        block.segments_flag = flag
        block.save()
        return HttpResponse(json.dumps({'ok': True}), mimetype='text/json')
    except:
        HttpResponse(json.dumps({'ok': False}), mimetype='text/json')

# --- Slices ---

def insert_slice(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)

    section = int(request.POST.get('section'))
    hash_value = int(request.POST.get('hash'))
    ctr_x = float(request.POST.get('cx'))
    ctr_y = float(request.POST.get('cy'))
    xstr = request.POST.getlist('x[]')
    ystr = request.POST.getlist('y[]')
    value = float(request.POST.get('value'))

    x = map(int, xstr)
    y = map(int, ystr)

    min_x = min(x)
    min_y = min(y)
    max_x = max(x)
    max_y = max(y)

    slice = Slice(stack = s, assembly = None, hash_value = hash_value, section = section,
                  min_x = min_x, min_y = min_y, max_x = max_x, max_y = max_y,
                  ctr_x = ctr_x, ctr_y = ctr_y, value = value,
                  shape_x = x, shape_y = y, size = len(x), parent = None)
    slice.save()

    return HttpResponse(json.dumps({'id': slice.id}), mimetype='text/json')


def set_slices_block(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)

    slice_ids_str = request.POST.getlist('slice[]')
    block_id = int(request.POST.get('block'))

    slice_ids = map(int, slice_id_str)

    try:
        block = Block.objects.get(id = block_id)

        slices = Slice.objects.filter(stack = s, id__in = slice_ids)

        ok_slice_ids = [qslice.id for qslice in slices]

        block.slices.extend(ok_slice_ids)

        block.save();

        return HttpResponse(json.dumps({'ok' : True}), mimetype='text/json')

    except Block.DoesNotExist:
        return HttpResponse(json.dumps({'ok' : False}), mimetype='text/json')


def retrieve_slices_by_hash(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    hash_values_str = request.POST.getlist('hash[]')
    hash_values = map(int, hash_values_str)
    slices = Slice.object.filter(stack = s, hash_value__in = hash_values)
    return generate_slices_response(slices)

def retrieve_slices_by_dbid(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    ids_str = request.POST.get('id[]')
    ids = map(int, ids_str)
    slices = Slice.object.filter(stack = s, id__in = ids)
    return generate_slices_response(slices)


def retrieve_slices_by_block(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    block_id = int(request.POST.get('block_id'))
    try:
        block = Block.objects.get(stack = s, id = block_id)
        slice_ids = block.slices
        slices = Slice.object.filter(stack = s, id__in = slice_ids)
        return generate_slices_response(slices)
    except:
        return generate_slices_response(Slice.objects.none())

def set_parent_slice(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    child_id = int(request.POST.get('child_id'))
    parent_id = int(reqeust.POST.get('parent_id'))
    try:
        child = Slice.objects.get(stack = s, id = child_id)
        parent = Slice.objects.get(stack = s, id = parent_id)
        child.parent = parent
        child.save()
        return HttpResponse(json.dumps({'ok' : True}), mimetype = 'text/json')
    except:
        return HttpResponse(json.dumps({'ok' : False}), mimetype = 'text/json')

def retrieve_parent_slice(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    id = int(request.POST.get('id'))
    try:
        child = Slice.objects.get(stack = s, id = id)
        return generate_slice_response(child.parent)
    except:
        return generate_slice_response(None)

def retrieve_child_slices(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    id = int(request.POST.get('id'))
    try:
        parent = Slice.objects.get(stack = s, id = id)
        children = Slice.objects.filter(stack = s, parent = parent)
        return generate_slices_response(children)
    except:
        return generate_slices_response(Slice.objects.none())

# --- Segments ---

def insert_end_segment(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    hash_value = int(request.POST.get('hash'))
    slice_id = int(request.POST.get('slice_id'))
    direction = int(request.POST.get('direction'))
    ctr_x = float(request.POST.get('cx'))
    ctr_y = float(request.POST.get('cy'))

    try:
        slice = Slice.objects.get(stack = s, id = slice_id)

        segment = Segment(stack = s, assembly = None, hash_value = hash_value,
                          section_inf = slice.section, min_x = slice.min_x,
                          min_y = slice.min_y, max_x = slice.max_x, max_y = slice.max_y,
                          ctr_x = ctr_x, ctr_y = ctr_y, type = 0, direction = direction,
                          slice_a = slice)
        segment.save()
        return HttpResponse(json.dumps({'id': segment.id}), mimetype='text/json')
    except Slice.DoesNotExist:
        return HttpResponse(json.dumps({'id': -1}), mimetype='text/json')




def insert_continuation_segment(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    hash_value = int(request.POST.get('hash'))
    slice_a_id = int(request.POST.get('slice_a_id'))
    slice_b_id = int(request.POST.get('slice_b_id'))
    direction = int(request.POST.get('direction'))
    ctr_x = float(request.POST.get('cx'))
    ctr_y = float(request.POST.get('cy'))

    try:
        slice_a = Slice.objects.get(stack = s, id = slice_a_id)
        slice_b = Slice.objects.get(stack = s, id = slice_b_id)

        min_x = min(slice_a.min_x, slice_b.min_x)
        min_y = min(slice_a.min_y, slice_b.min_y)
        max_x = max(slice_a.max_x, slice_b.max_x)
        max_y = max(slice_a.max_y, slice_b.max_y)
        section = min(slice_a.section, slice_b.section)

        segment = Segment(stack = s, assembly = None, hash_value = hash_value,
                          section_inf = section, min_x = min_x,
                          min_y = min_y, max_x = max_x, max_y = max_y,
                          ctr_x = ctr_x, ctr_y = ctr_y, type = 1, direction = direction,
                          slice_a = slice_a, slice_b = slice_b)
        segment.save()
        return HttpResponse(json.dumps({'id': segment.id}), mimetype='text/json')
    except Slice.DoesNotExist:
        return HttpResponse(json.dumps({'id': -1}), mimetype='text/json')


def insert_branch_segment(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    hash_value = int(request.POST.get('hash'))
    slice_a_id = int(request.POST.get('slice_a_id'))
    slice_b_id = int(request.POST.get('slice_b_id'))
    slice_c_id = int(request.POST.get('slice_c_id'))
    direction = int(request.POST.get('direction'))
    ctr_x = float(request.POST.get('cx'))
    ctr_y = float(request.POST.get('cy'))

    try:
        slice_a = Slice.objects.get(stack = s, id = slice_a_id)
        slice_b = Slice.objects.get(stack = s, id = slice_b_id)
        slice_c = Slice.objects.get(stack = s, id = slice_c_id)

        min_x = min(min(slice_a.min_x, slice_b.min_x), slice_c.min_x)
        min_y = min(min(slice_a.min_y, slice_b.min_y), slice_c.min_y)
        max_x = max(max(slice_a.max_x, slice_b.max_x), slice_c.max_x)
        max_y = max(max(slice_a.max_y, slice_b.max_y), slice_c.max_y)
        section = min(min(slice_a.section, slice_b.section), slice_c.section)

        segment = Segment(stack = s, assembly = None, hash_value = hash_value,
                          section_inf = section, min_x = min_x,
                          min_y = min_y, max_x = max_x, max_y = max_y,
                          ctr_x = ctr_x, ctr_y = ctr_y, type = 1, direction = direction,
                          slice_a = slice_a, slice_b = slice_b, slice_c = slice_c)
        segment.save()
        return HttpResponse(json.dumps({'id': segment.id}), mimetype='text/json')
    except Slice.DoesNotExist:
        return HttpResponse(json.dumps({'id': -1}), mimetype='text/json')
    pass

def set_segments_block(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)

    segment_ids_str = request.POST.getlist('segment[]')
    block_id = int(request.POST.get('block'))

    segment_ids = map(int, segment_id_str)

    try:
        block = Block.objects.get(id = block_id)

        segments = Segment.objects.filter(stack = s, id__in = segment_ids)

        ok_segment_ids = [qsegment.id for qsegment in segments]

        block.segments.extend(ok_segment_ids)

        block.save();

        return HttpResponse(json.dumps({'ok' : True}), mimetype='text/json')

    except Block.DoesNotExist:
        return HttpResponse(json.dumps({'ok' : False}), mimetype='text/json')
    pass

def retrieve_segments_by_hash(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    hash_values_str = request.POST.getlist('hash[]')
    hash_values = map(int, hash_values_str)
    segments = Segment.object.filter(stack = s, hash_value__in = hash_values)
    return generate_segments_response(segments)

def retrieve_segments_by_id(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    ids_str = request.POST.getlist('id[]')
    ids = map(int, ids_str)
    segments = Segment.object.filter(stack = s, id__in = ids)
    return generate_segments_response(segments)

def retrieve_segments_by_block(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    block_id = int(request.POST.get('block_id'))
    try:
        block = Block.objects.get(stack = s, id = block_id)
        segment_ids = block.segments
        segments = Segment.object.filter(stack = s, id__in = segment_ids)
        return generate_segments_response(segments)
    except:
        return generate_segments_response(Segment.objects.none())

# --- convenience code for debug purposes ---
def clear_slices(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    sure = request.POST.get('sure')
    if sure == 'yes':
        for slice in Slice.object.filter(stack = s):
            slice.delete()
        return HttpResponse(json.dumps({'ok' : True}), mimetype='text/json')
    else:
        HttpResponse(json.dumps({'ok' : False}), mimetype='text/json')


def clear_segments(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    sure = request.POST.get('sure')
    if sure == 'yes':
        for segment in Segment.object.filter(stack = s):
            segment.delete()
        return HttpResponse(json.dumps({'ok' : True}), mimetype='text/json')
    else:
        HttpResponse(json.dumps({'ok' : False}), mimetype='text/json')

def clear_blocks(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    sure = request.POST.get('sure')
    if sure == 'yes':
        for block in Block.object.filter(stack = s):
            block.delete()
        for block_info in BlockInfo.object.filter(stack = s):
            block_info.delete()
        return HttpResponse(json.dumps({'ok' : True}), mimetype='text/json')
    else:
        HttpResponse(json.dumps({'ok' : False}), mimetype='text/json')

