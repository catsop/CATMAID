import json
import sys

from django.http import HttpResponse

from django.shortcuts import get_object_or_404

from catmaid.models import *
from catmaid.control.stack import get_stack_info
from models import *

from celery.task.control import inspect

from celerysopnet.tasks import SliceGuarantorTask, SegmentGuarantorTask
from celerysopnet.tasks import SolutionGuarantorTask, SolveSubvolumeTask
from celerysopnet.tasks import TraceNeuronTask

from djcelery.models import TaskState


# --- JSON conversion ---
def slice_dict(slice):
    sd = {'assembly' : slice.assembly,
          'hash' : slice.hash_value,
          'section' : slice.section,
          'box' : [slice.min_x, slice.min_y, slice.max_x, slice.max_y],
          'ctr' : [slice.ctr_x, slice.ctr_y],
          'value' : slice.value,
          'x' : slice.shape_x,
          'y' : slice.shape_y}
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
          'slices' : block.slices_flag,
          'segments' : block.segments_flag,
          'box' : [block.min_x, block.min_y, block.min_z,
                   block.max_x, block.max_y, block.max_z]}
    return bd

def core_dict(core):
    bd = {'id' : core.id,
          'solutions' : core.solution_set_flag,
          'box' : [core.min_x, core.min_y, core.min_z,
                   core.max_x, core.max_y, core.max_z]}
    return bd

def block_info_dict(block_info, stack):
    bid = {'block_size' : [block_info.bheight, block_info.bwidth, block_info.bdepth],
           'count' : [block_info.num_x, block_info.num_y, block_info.num_z],
           'core_size' : [block_info.cheight, block_info.cwidth, block_info.cdepth],
           'stack_size' : [stack.dimension.x, stack.dimension.y, stack.dimension.z]}
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

def generate_blocks_response(blocks):
    if blocks is not None:
        block_dicts = [block_dict(block) for block in blocks]
        return HttpResponse(json.dumps({'length' : len(block_dicts), 'blocks' : block_dicts}))
    else:
        return HttpResponse(json.dumps({'length' : 0}))

def generate_core_response(core):
    if core:
        return HttpResponse(json.dumps(core_dict(core)), mimetype = 'text/json')
    else:
        return HttpResponse(json.dumps({'id' : -1}), mimetype = 'text/json')

def generate_cores_response(cores):
    if cores is not None:
        core_dicts = [core_dict(core) for core in cores]
        return HttpResponse(json.dumps({'length' : len(core_dicts), 'cores' : core_dicts}))
    else:
        return HttpResponse(json.dumps({'length' : 0}))


def generate_block_info_response(block_info, stack):
    if block_info:
        return HttpResponse(json.dumps(block_info_dict(block_info, stack)), mimetype = 'text/json')
    else:
        return HttpResponse(json.dumps({'id' : -1}), mimetype = 'text/json')

def generate_conflict_response(conflicts, stack):
    conflict_dicts = []
    for conflict in conflicts:
        rels = SliceConflictRelation.filter(conflict__in = conflict)
        conflict_dict = [{'conflict_hashes' : rel.slice.hash_value}
                        for rel in rels]
        conflict_dicts.add(conflict_dict)
    return HttpResponse(json.dumps({'conflict', conflict_dicts}))

# --- Blocks and Cores ---
def setup_blocks(request, project_id = None, stack_id = None):
    '''
    Initialize and store the blocks and block info in the db, associated with
    the given stack, if these things don't already exist.
    '''
    try:
        width = int(request.GET.get('width'))
        height = int(request.GET.get('height'))
        depth = int(request.GET.get('depth'))
        # core height, width, and depth in blocks
        corewib = int(request.GET.get('cwidth'))
        corehib = int(request.GET.get('cheight'))
        coredib = int(request.GET.get('cdepth'))
    except TypeError:
        return HttpResponse(json.dumps({'ok' : False, 'reason' : 'malformed'}), mimetype='text/json')

    s = get_object_or_404(Stack, pk=stack_id)
    p = get_object_or_404(Project, pk=project_id)
    u = User.objects.get(id=1)

    nx = s.dimension.x / width
    ny = s.dimension.y / height
    nz = s.dimension.z / depth

    # If stack size is not equally divisible by block size...
    if nx * width < s.dimension.z:
        nx = nx + 1

    if ny * height < s.dimension.y:
        ny = ny + 1

    if nz * depth < s.dimension.z:
        nz = nz + 1

    try:
        info = BlockInfo.objects.get(stack=s)
        return HttpResponse(json.dumps({'ok': False, 'reason' : 'already setup'}), mimetype='text/json')
    except BlockInfo.DoesNotExist:

        info = BlockInfo(user = u, project = p, stack = s,
                         bheight = height, bwidth = width, bdepth = depth,
                         cheight = corehib, cwidth = corewib, cdepth = coredib,
                         num_x = nx, num_y = ny, num_z = nz)
        info.save()

    # Create new Blocks

    for z in range(0, s.dimension.z, depth):
        for y in range(0, s.dimension.y, height):
            for x in range(0, s.dimension.x, width):
                x_ub = min(x + width, s.dimension.x + 1)
                y_ub = min(y + height, s.dimension.y + 1)
                z_ub = min(z + depth, s.dimension.z + 1)
                block = Block(user=u, project=p, stack=s, min_x = x, min_y = y, min_z = z,
                              max_x = x_ub, max_y = y_ub, max_z = z_ub,
                              slices_flag = False, segments_flag = False, solution_cost_flag = False)
                # TODO: figure out how to use bulk_create instead.
                block.save()

    # Create new Cores
    cWidth = width * corewib
    cHeight = height * corehib
    cDepth = depth * coredib
    for z in range(0, s.dimension.z, cDepth):
        for y in range(0, s.dimension.y, cHeight):
            for x in range(0, s.dimension.x, cWidth):
                x_ub = min(x + cWidth, s.dimension.x + 1)
                y_ub = min(y + cHeight, s.dimension.y + 1)
                z_ub = min(z + cDepth, s.dimension.z + 1)
                core = Core(user=u, project=p, stack=s, min_x = x, min_y = y, min_z = z,
                            max_x = x_ub, max_y = y_ub, max_z = z_ub, solution_set_flag = False)
                core.save()

    return HttpResponse(json.dumps({'ok': True}), mimetype='text/json')

# Query, agnostic to Model class
def location_query(model, s, request):
    x = int(request.GET.get('x'))
    y = int(request.GET.get('y'))
    z = int(request.GET.get('z'))
    return model.objects.get(stack = s,
                      min_x__lte = x,
                      min_y__lte = y,
                      min_z__lte = z,
                      max_x__gt = x,
                      max_y__gt = y,
                      max_z__gt = z)

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
    return model.objects.filter(stack = s,
                                max_x__gt = xmin,
                                max_y__gt = ymin,
                                max_z__gt = zmin,
                                min_x__lte = xmax,
                                min_y__lte = ymax,
                                min_z__lte = zmax)

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
        return HttpResponse(json.dumps({'ok' : True}), mimetype='text/json')
    except type.DoesNotExist:
        return HttpResponse(json.dumps({'ok' : False}), mimetype='text/json')

def get_flag(s, request, flag_name, id_field = 'block_id', type = Block):
    id = int(request.GET.get(id_field))
    try:
        box = type.objects.get(stack = s, id = id)
        flag = getattr(box, flag_name)
        return HttpResponse(json.dumps({flag_name : flag}), mimetype='text/json')
    except type.DoesNotExist:
        return HttpResponse(json.dumps({flag_name : False, 'ok' : False}), mimetype='text/json')

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

def do_insert_slices(stack, project, user, dict):
    try:
        n = int(dict.get('n'))
        for i in range(n):
            i_str = str(i)
            section = int(dict.get('section_' + i_str))
            hash_value = dict.get('hash_' + i_str)
            ctr_x = float(dict.get('cx_' + i_str))
            ctr_y = float(dict.get('cy_' + i_str))
            xlist = dict.get('x_' + i_str)
            ylist = dict.get('y_' + i_str)
            x = [int(xstr) for xstr in xlist.split(',')]
            y = [int(ystr) for ystr in ylist.split(',')]
            value = float(dict.get('value_' + i_str))
            if x and y and len(x) > 0 and len(y) > 0:
                min_x = min(x)
                min_y = min(y)
                max_x = max(x)
                max_y = max(y)
            else:
                min_x = -1
                min_y = -1
                max_x = -1
                max_y = -1
            slice = Slice(project = project, stack = stack, user = user,
                  assembly = None, hash_value = hash_value, section = section,
                  min_x = min_x, min_y = min_y, max_x = max_x, max_y = max_y,
                  ctr_x = ctr_x, ctr_y = ctr_y, value = value,
                  shape_x = x, shape_y = y, size = len(x))
            slice.save()
        return HttpResponse(json.dumps({'ok': True}), mimetype='text/json')
    except:
        return HttpResponse(json.dumps({'ok' : False, 'reason' : str(sys.exc_info()[0])}), mimetype='text/json')

def insert_slices(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    p = get_object_or_404(Project, pk = project_id)
    u = User.objects.get(id = 1)

    if (request.method == 'GET'):
        return do_insert_slices(s, p, u, request.GET)
    else:
        return do_insert_slices(s, p, u, request.POST)

def associate_slices_to_block(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)

    try:
        slice_hashes = request.GET.get('hash').split(',')
        block_id = int(request.GET.get('block'))

        block = Block.objects.get(id = block_id)

        slices = Slice.objects.filter(stack = s, hash_value__in = slice_hashes)

        # TODO: use bulk_create
        for slice in slices:
            bsr = SliceBlockRelation(block = block, slice = slice)
            bsr.save()

        return HttpResponse(json.dumps({'ok' : True}), mimetype='text/json')

    except Block.DoesNotExist:
        return HttpResponse(json.dumps({'ok' : False}), mimetype='text/json')


def retrieve_slices_by_hash(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    hash_values = request.GET.get('hash').split(',')
    slices = Slice.objects.filter(stack = s, hash_value__in = hash_values)
    return generate_slices_response(slices)


# Retrieve Slices associated to any ConflictSet that is associated to the Blocks with the given ids.
def retrieve_slices_by_blocks_and_conflict(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    try:
        block_id_list = request.GET.get('block_ids')
        block_ids = [int(id) for id in block_id_list.split(',')]
        # filter Blocks by id
        blocks = Block.objects.get(stack=s, id__in=block_ids)
        # filter Block <--> Conflict relationships by Block
        block_conflict_relations = BlockConflictRelation.objects.filter(stack=s, block__in=blocks)
        # collect a set of conflicts. List is ok, because we don't expect duplication.
        conflicts = [bcr.conflict for bcr in block_conflict_relations]
        # filter Slice <--> Conflict relationships by Conflict
        slice_conflict_relations = SliceConflictRelation.objects.filter(stack=s, conflict__in = conflicts)
        # now, collect a set of the resulting Slices, then generate a response for the client.
        slices = {scr.slice for scr in slice_conflict_relations}
        return generate_slices_response(slices)
    except:
        return generate_slices_response(Slice.objects.none())

def store_conflict_set(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    try:
        u = User.objects.get(id=1)
        slice_hashes = request.GET.get('hash').split(',')

        # Collect slices from ids, then blocks from slices.
        slices = Slice.objects.filter(stack = s, hash_value__in = slice_hashes)
        bsrs = SliceBlockRelation.objects.filter(slice__in = slices)
        blocks = [bsr.block for bsr in bsrs]

        # no exception, so far. create the conflict set
        conflict = SliceConflictSet()
        conflict.save()

        # associate each slice and block to the conflict set
        for slice in slices:
            sliceConflict = SliceConflictRelation(slice = slice, conflict = conflict, user = u)
            sliceConflict.save()
        for block in blocks:
            blockConflict = BlockConflictRelation(block = block, conflict = conflict, user = u)
            blockConflict.save()
        return HttpResponse(json.dumps({'ok' : True}), mimetype='text/json')
    except:
        return HttpResponse(json.dumps({'ok' : False}), mimetype='text/json')

def retrieve_conflict_sets(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    try:
        slice_hashes = request.GET.get('hash').split(',')

        slices = Slice.objects.filter(stack = s, hash_value__in = slice_hashes)
        conflict_relations = SliceConflictRelation.objects.filter(slice__in = slices)
        conflicts = {cr.conflict for cr in conflict_relations}

        return generate_conflict_response(conflicts, s)
    except:
        return generate_conflict_response(SliceConflictSet.objects.none(), s)

def retrieve_associated_block_ids(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    try:
        slice_hashes = request.GET.get('hash').split(',')

        slices = Slice.objects.filter(stack = s, hash_value__in = slice_hashes)
        block_relations = SliceBlockRelation.objects.filter(slice__in = slices)
        blocks = {br.block for br in block_relations}
        block_ids = [block.id for block in blocks]

        return HttpResponse(json.dumps({'ok' : True, 'block_ids' : block_ids}), mimetype='text/json')
    except:
        return HttpResponse(json.dumps({'ok' : False}), mimetype='text/json')

# --- Segments ---

def insert_end_segment(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)

    try:
        hash_value = int(request.GET.get('hash'))
        slice_id = int(request.GET.get('slice_id'))
        direction = int(request.GET.get('direction'))
        ctr_x = float(request.GET.get('cx'))
        ctr_y = float(request.GET.get('cy'))

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

    try:
        hash_value = int(request.GET.get('hash'))
        slice_a_id = int(request.GET.get('slice_a_id'))
        slice_b_id = int(request.GET.get('slice_b_id'))
        direction = int(request.GET.get('direction'))
        ctr_x = float(request.GET.get('cx'))
        ctr_y = float(request.GET.get('cy'))

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

    try:
        hash_value = int(request.GET.get('hash'))
        slice_a_id = int(request.GET.get('slice_a_id'))
        slice_b_id = int(request.GET.get('slice_b_id'))
        slice_c_id = int(request.GET.get('slice_c_id'))
        direction = int(request.GET.get('direction'))
        ctr_x = float(request.GET.get('cx'))
        ctr_y = float(request.GET.get('cy'))

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

def set_segments_block(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)

    segment_ids_str = request.GET.getlist('segment[]')
    block_id = int(request.GET.get('block'))

    segment_ids = map(int, segment_ids_str)

    try:
        block = Block.objects.get(id = block_id)

        segments = Segment.objects.filter(stack = s, id__in = segment_ids)

        ok_segment_ids = [qsegment.id for qsegment in segments]

        block.segments.extend(ok_segment_ids)

        block.save();

        return HttpResponse(json.dumps({'ok' : True}), mimetype='text/json')

    except Block.DoesNotExist:
        return HttpResponse(json.dumps({'ok' : False}), mimetype='text/json')

def retrieve_segments_by_hash(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    hash_values_str = request.GET.getlist('hash[]')
    hash_values = map(int, hash_values_str)
    segments = Segment.objects.filter(stack = s, hash_value__in = hash_values)
    return generate_segments_response(segments)

def retrieve_segments_by_dbid(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    ids_str = request.GET.getlist('id[]')
    ids = map(int, ids_str)
    segments = Segment.objects.filter(stack = s, id__in = ids)
    return generate_segments_response(segments)

def retrieve_segments_by_block(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    block_id = int(request.GET.get('block_id'))
    try:
        block = Block.objects.get(stack = s, id = block_id)
        segment_ids = block.segments
        segments = Segment.objects.filter(stack = s, id__in = segment_ids)
        return generate_segments_response(segments)
    except:
        return generate_segments_response(Segment.objects.none())

# --- convenience code for debug purposes ---
def clear_slices(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    sure = request.GET.get('sure')
    if sure == 'yes':
        Slice.objects.filter(stack = s).delete()
        return HttpResponse(json.dumps({'ok' : True}), mimetype='text/json')
    else:
        HttpResponse(json.dumps({'ok' : False}), mimetype='text/json')

def clear_segments(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    sure = request.GET.get('sure')
    if sure == 'yes':
        Segment.objects.filter(stack = s).delete()
        return HttpResponse(json.dumps({'ok' : True}), mimetype='text/json')
    else:
        HttpResponse(json.dumps({'ok' : False}), mimetype='text/json')

def clear_blocks(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    sure = request.GET.get('sure')
    if sure == 'yes':
        Block.objects.filter(stack = s).delete()
        Core.objects.filter(stack = s).delete()
        BlockInfo.objects.filter(stack = s).delete()
        return HttpResponse(json.dumps({'ok' : True}), mimetype='text/json')
    else:
        HttpResponse(json.dumps({'ok' : False}), mimetype='text/json')

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

def test_sliceguarantor_task(request, x, y, z):
    async_result = SliceGuarantorTask.delay(x, y, z)
    return HttpResponse(json.dumps({
        'success': "Successfully queued slice guarantor task.",
        'task_id': async_result.id
    }))

def test_segmentguarantor_task(request, x, y, z):
    async_result = SegmentGuarantorTask.delay(x, y, z)
    return HttpResponse(json.dumps({
        'success': "Successfully queued segment guarantor task.",
        'task_id': async_result.id
    }))

def test_solutionguarantor_task(request, x, y, z):
    async_result = SolutionGuarantorTask.delay(x, y, z)
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
