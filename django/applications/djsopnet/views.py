import json
import sys

from django.http import HttpResponse

from django.shortcuts import get_object_or_404
from django.db import IntegrityError
from django.conf import settings

from catmaid.models import *
from catmaid.control.stack import get_stack_info
from models import *

from celery.task.control import inspect

from celerysopnet.tasks import SliceGuarantorTask, SegmentGuarantorTask
from celerysopnet.tasks import SolutionGuarantorTask, SolveSubvolumeTask
from celerysopnet.tasks import TraceNeuronTask

from djcelery.models import TaskState

from StringIO import StringIO
import traceback


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
    sd = {'assembly' : segment.assembly,
          'hash' : segment.hash_value,
          'section' : segment.section_inf,
          'box' : [segment.min_x, segment.min_y, segment.max_x, segment.max_y],
          'ctr' : [segment.ctr_x, segment.ctr_y],
          'type' : segment.type,
          'direction' : segment.direction,
          'slice_a' : segment.slice_a_hash,
          'slice_b' : -1,
          'slice_c' : -1}

    if segment.slice_b_hash:
        sd['slice_b'] = segment.slice_b_hash
    if segment.slice_c_hash:
        sd['slice_c'] = segment.slice_c_hash

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
    bid = {'block_size' : [block_info.bwidth, block_info.bheight, block_info.bdepth],
           'count' : [block_info.num_x, block_info.num_y, block_info.num_z],
           'core_size' : [block_info.cwidth, block_info.cheight, block_info.cdepth],
           'stack_size' : [stack.dimension.x, stack.dimension.y, stack.dimension.z]}
    return bid

def generate_slice_response(slice):
    if slice:
        return HttpResponse(json.dumps(slice_dict(slice)), mimetype = 'text/json')
    else:
        return HttpResponse(json.dumps({'hash' : 'nope'}), mimetype = 'text/json')

def generate_segment_response(segment):
    if segment:
        return HttpResponse(json.dumps(segment_dict(segment)), mimetype = 'text/json')
    else:
        return HttpResponse(json.dumps({'id' : -1}), mimetype = 'text/json')


def generate_slices_response(slices):
    slice_list = [slice_dict(slice) for slice in slices]
    return HttpResponse(json.dumps({'ok' : True, 'slices' : slice_list}), mimetype = 'text/json')

def generate_segments_response(segments):
    segment_list = [segment_dict(segment) for segment in segments]
    return HttpResponse(json.dumps({'ok' : True, 'segments' : segment_list}), mimetype = 'text/json')

def generate_block_response(block):
    if block:
        return HttpResponse(json.dumps(block_dict(block)), mimetype = 'text/json')
    else:
        return HttpResponse(json.dumps({'id' : -1}), mimetype = 'text/json')

def generate_blocks_response(blocks):
    if blocks is not None:
        block_dicts = [block_dict(block) for block in blocks]
        return HttpResponse(json.dumps({'ok' : True, 'length' : len(block_dicts), 'blocks' : block_dicts}))
    else:
        return HttpResponse(json.dumps({'ok' : True, 'length' : 0}))

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
        rels = SliceConflictRelation.objects.filter(conflict = conflict)
        conflict_hashes = [rel.slice.hash_value for rel in rels]
        conflict_dicts.append({'conflict_hashes' : conflict_hashes})
    return HttpResponse(json.dumps({'ok' : True, 'conflict' : conflict_dicts}))

def generate_features_response(features):
    features_dicts = []
    for feature in features:
        segment_hash = feature.segment.hash_value
        feature_values = feature.features
        features_dicts.append({'hash' : segment_hash, 'fv': feature_values})
    return HttpResponse(json.dumps({'ok':True, 'features' : features_dicts}), mimetype='text/json')

def error_response():
    sio = StringIO()
    traceback.print_exc(file = sio)
    res = HttpResponse(json.dumps({'ok' : False, 'djerror' : sio.getvalue()}))
    sio.close()
    return res

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
    if nx * width < s.dimension.x:
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
                x_ub = min(x + width, s.dimension.x)
                y_ub = min(y + height, s.dimension.y)
                z_ub = min(z + depth, s.dimension.z)
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

def retrieve_blocks_by_id(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk=stack_id)
    try:
        id_list = request.GET.get('ids')
        ids = [int(id) for id in id_list.split(',')]
        blocks = Block.objects.filter(id__in = ids)
        return generate_blocks_response(blocks)
    except:
        return error_response()

def retrieve_cores_by_id(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk=stack_id)
    try:
        id_list = request.GET.get('ids')
        ids = [int(id) for id in id_list.split(',')]
        cores = Core.objects.filter(id__in = ids)
        return generate_cores_response(cores)
    except:
        return error_response()

def stack_info(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk=stack_id)
    stack_dict = {'stack_size' : [s.dimension.x, s.dimension.y, s.dimension.z],
                  'tile_size' : [s.tile_width, s.tile_height],
                  'file_extension' : s.file_extension,
                  'image_base' : s.image_base}
    return HttpResponse(json.dumps(stack_dict), mimetype='text/json')

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

def do_insert_slices(stack, project, user, req_dict):
    try:
        n = int(req_dict.get('n'))
        for i in range(n):
            i_str = str(i)
            section = int(req_dict.get('section_' + i_str))
            hash_value = req_dict.get('hash_' + i_str)
            ctr_x = float(req_dict.get('cx_' + i_str))
            ctr_y = float(req_dict.get('cy_' + i_str))
            xlist = req_dict.get('x_' + i_str)
            ylist = req_dict.get('y_' + i_str)
            x = [int(xstr) for xstr in xlist.split(',')]
            y = [int(ystr) for ystr in ylist.split(',')]
            value = float(req_dict.get('value_' + i_str))
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
            try:
                slice.save()
            except IntegrityError:
                pass

        return HttpResponse(json.dumps({'ok': True}), mimetype='text/json')
    except:
        return error_response()

def insert_slices(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    p = get_object_or_404(Project, pk = project_id)
    u = User.objects.get(id = 1)

    print request

    if request.method == 'GET':
        return do_insert_slices(s, p, u, request.GET)
    else:
        return do_insert_slices(s, p, u, request.POST)

def associate_slices_to_block(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk=stack_id)
    p = get_object_or_404(Project, pk=project_id)
    u = User.objects.get(id = 1)

    try:
        slice_hashes = request.GET.get('hash').split(',')
        block_id = int(request.GET.get('block'))

        block = Block.objects.get(id = block_id)

        slices = Slice.objects.filter(stack = s, hash_value__in = slice_hashes)

        # TODO: use bulk_create
        for slice in slices:
            bsr = SliceBlockRelation(user = u, project = p, block = block, slice = slice)
            bsr.save()

        return HttpResponse(json.dumps({'ok' : True}), mimetype='text/json')

    except Block.DoesNotExist:
        return HttpResponse(json.dumps({'ok' : False, 'reason' : 'Block does not exist'}), mimetype='text/json')
    except:
        return error_response()

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
        blocks = Block.objects.filter(stack=s, id__in=block_ids)

        ## Step 1: Retrieve Slices associated with the Blocks.
        slice_block_relations = SliceBlockRelation.objects.filter(block__in = blocks)
        block_slices = {sbr.slice for sbr in slice_block_relations}

        ## Step 2: Retrieve Slices associated with ConflictSets associated with the Blocks.
        # filter Block <--> Conflict relationships by Block
        block_conflict_relations = BlockConflictRelation.objects.filter(block__in=blocks)
        # collect a set of conflicts. List is ok, because we don't expect duplication.
        conflicts = [bcr.conflict for bcr in block_conflict_relations]
        # filter Slice <--> Conflict relationships by Conflict
        slice_conflict_relations = SliceConflictRelation.objects.filter(conflict__in = conflicts)
        # now, collect a set of the resulting Slices, then generate a response for the client.
        conflict_slices = {scr.slice for scr in slice_conflict_relations}
        slices = block_slices.union(conflict_slices)
        return generate_slices_response(slices)
    except:
        return error_response()

def store_conflict_set(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    p = get_object_or_404(Project, pk = project_id)
    u = User.objects.get(id=1)

    try:

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
            sliceConflict = SliceConflictRelation(slice = slice, conflict = conflict, user = u, project = p)
            sliceConflict.save()
        for block in blocks:
            blockConflict = BlockConflictRelation(block = block, conflict = conflict, user = u, project = p)
            blockConflict.save()
        return HttpResponse(json.dumps({'ok' : True}), mimetype='text/json')
    except:
        return error_response()

def retrieve_conflict_sets(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    try:
        slice_hashes = request.GET.get('hash').split(',')

        slices = Slice.objects.filter(stack = s, hash_value__in = slice_hashes)
        conflict_relations = SliceConflictRelation.objects.filter(slice__in = slices)
        conflicts = {cr.conflict for cr in conflict_relations}

        return generate_conflict_response(conflicts, s)
    except:
        return error_response()

def retrieve_block_ids_by_slices(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    try:
        slice_hashes = request.GET.get('hash').split(',')

        slices = Slice.objects.filter(stack = s, hash_value__in = slice_hashes)
        block_relations = SliceBlockRelation.objects.filter(slice__in = slices)
        blocks = {br.block for br in block_relations}
        block_ids = [block.id for block in blocks]

        return HttpResponse(json.dumps({'ok' : True, 'block_ids' : block_ids}), mimetype='text/json')
    except:
        return error_response()

# --- Segments ---
def setup_feature_names(names, stack, project):
    try:
        FeatureNameInfo.objects.get(stack = stack, project = project)
        return False
    except FeatureNameInfo.DoesNotExist:
        ids = []
        user = User.objects.get(id = 1)
        for name in names:
            feature_name = FeatureName(name = name)
            feature_name.save()
            ids.append(feature_name.id)
        info = FeatureNameInfo(stack = stack, project = project, user = user,
                               name_ids = ids, size = len(ids))
        info.save()
        return True

def get_feature_names(stack, project):
    # get feature names, if they exist.
    # throws FeatureNameInfo.DoesNotExist, and possibly FeatureNameInfo.MultipleObjectsReturned
    feature_info = FeatureNameInfo.objects.get(stack = stack, project = project)
    keys = feature_info.name_ids
    feature_name_objects = FeatureName.objects.filter(id__in = keys)
    feature_names = []
    # ensure that the order of the feature_names list corresponds to that of keys
    for id in keys:
        for fno in feature_name_objects:
            if fno.id == id:
                feature_names.append(fno.name)
    return feature_names

def do_insert_segments(stack, project, user, dict):
    try:
        n = int(dict.get('n'))
        for i in range(n):
            i_str = str(i)
            section_inf = int(dict.get('sectioninf_' + i_str))
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

            segment = Segment(project = project, stack = stack, user = user,
                              assembly = None, hash_value = hash_value, section_inf = section_inf,
                              min_x = min_x, min_y = min_y, max_x = max_x, max_y = max_y,
                              ctr_x = ctr_x, ctr_y = ctr_y, type = type, direction = direction,
                              slice_a_hash = slice_a_hash, slice_b_hash = slice_b_hash,
                              slice_c_hash = slice_c_hash)
            segment.save()

        return HttpResponse(json.dumps({'ok': True}), mimetype='text/json')
    except:
        return error_response()


def insert_segments(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    p = get_object_or_404(Project, pk = project_id)
    u = User.objects.get(id = 1)

    if request.method == 'GET':
        return do_insert_segments(s, p, u, request.GET)
    else:
        return do_insert_segments(s, p, u, request.POST)

def associate_segments_to_block(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    p = get_object_or_404(Project, pk=project_id)
    u = User.objects.get(id = 1)

    try:
        segment_hashes = request.GET.get('hash').split(',')
        block_id = int(request.GET.get('block'))

        block = Block.objects.get(id = block_id)

        segments = Segment.objects.filter(stack = s, hash_value__in = segment_hashes)

        for segment in segments:
            bsr = SegmentBlockRelation(user = u, project = p, block = block, segment = segment)
            bsr.save()

        return HttpResponse(json.dumps({'ok' : True}), mimetype='text/json')
    except Block.DoesNotExist:
        return HttpResponse(json.dumps({'ok' : False, 'reason' : 'Block does not exist'}), mimetype='text/json')
    except:
        return error_response()

def retrieve_segments_by_hash(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    hash_values = request.GET.get('hash').split(',')
    segments = Segment.objects.filter(stack = s, hash_value__in = hash_values)
    return generate_segments_response(segments)

def retrieve_segments_by_blocks(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    try:
        block_id_list = request.GET.get('block_ids')
        block_ids = [int(id) for id in block_id_list.split(',')]
        blocks = Block.objects.filter(stack=s, id__in=block_ids)

        segment_block_relations = SegmentBlockRelation.objects.filter(block__in = blocks)
        segments = {sbr.segment for sbr in segment_block_relations}

        return generate_segments_response(segments)
    except:
        return error_response()

def set_feature_names(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    p = get_object_or_404(Project, pk = project_id)
    names = []

    try:
        names = request.GET.get('names').split(',')
        existing_names = get_feature_names(s, p)
        if existing_names == names:
            return HttpResponse(json.dumps({'ok' : True}), mimetype='text/json')
        else:
            return HttpResponse(json.dumps({'ok' : False,
                                            'reason' : 'tried to set different feature names'}),
                                mimetype='text/json')
    except FeatureNameInfo.DoesNotExist:
        if setup_feature_names(names, s, p):
            return HttpResponse(json.dumps({'ok' : True}), mimetype='text/json')
        else:
            return HttpResponse(json.dumps({'ok' : False,
                                            'reason' : 'something went horribly, horribly awry'}),
                                mimetype='text/json')
    except:
        return error_response()

def retrieve_feature_names(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    p = get_object_or_404(Project, pk = project_id)
    names = get_feature_names(s, p)
    return HttpResponse(json.dumps({'names' : names}), mimetype='text/json')


def do_set_segment_features(stack, project, user, req_dict):
    try:
        n = int(req_dict.get('n'))
        feature_size = FeatureNameInfo.objects.get(stack = stack, project = project).size
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
        segments = Segment.objects.filter(hash_value__in = hash_values)

        # Now, set the features
        for segment in segments:
            hash_value = segment.hash_value

            feature_str_list = feature_list_dict[hash_value]

            # check that these features match the size in FeatureNameInfo
            if len(feature_str_list) != feature_size:
                return HttpResponse(
                    json.dumps({'ok': False,
                                'reason' : 'feature list is the wrong size',
                                'count' : count}),
                    mimetype='text/json')

            feature_float_list = map(float, feature_str_list)

            try:
                segment_features = SegmentFeatures.objects.get(segment = segment)
                segment_features.features = feature_float_list
            except SegmentFeatures.DoesNotExist:
                segment_features = SegmentFeatures(user = user, project = project,
                                              segment = segment, features = feature_float_list)

            segment_features.save()

            count += 1

        return HttpResponse(json.dumps({'ok': True, 'count' : count}), mimetype='text/json')
    except:
        return error_response()

def set_segment_features(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    p = get_object_or_404(Project, pk = project_id)
    u = User.objects.get(id = 1)

    if request.method == 'GET':
        return do_set_segment_features(s, p, u, request.GET)
    else:
        return do_set_segment_features(s, p, u, request.POST)

def get_segment_features(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    p = get_object_or_404(Project, pk = project_id)
    try:
        segment_hashes = request.GET.get('hash').split(',')
        segments = Segment.objects.filter(stack = s, hash_value__in = segment_hashes)
        features = SegmentFeatures.objects.filter(project = p, segment__in = segments)
        return generate_features_response(features)
    except:
        return error_response()

def set_segment_costs(request, project_id = None, stack_id = None):
    p = get_object_or_404(Project, pk = project_id)
    u = User.objects.get(id = 1)

    try:
        n = int(request.GET.get('n'))
        cost_dict = {}
        hash_values = []
        count = 0

        for i in range(n):
            i_str = str(i)
            hash_value = request.GET.get('hash_' + i_str)
            hash_values.append(hash_value)
            cost_dict[hash_value] = float(request.GET.get('cost_' + i_str))

        segments = Segment.objects.filter(hash_value__in = hash_values)

        for segment in segments:
            cost = cost_dict[segment.hash_value]
            try:
                segment_cost = SegmentCost.objects.get(segment = segment)
                segment_cost.cost = cost
            except SegmentCost.DoesNotExist:
                segment_cost = SegmentCost(user = u, project = p, segment = segment, cost = cost)
            segment_cost.save()
            count += 1

        return HttpResponse(json.dumps({'ok' : True, 'count' : count}), mimetype='text/json')
    except:
        return error_response()

def retrieve_segment_costs(request, project_id = None, stack_id = None):
    try:
        hash_values = request.GET.get('hash').split(',')
        segments = Segment.objects.filter(hash_value__in = hash_values)
        costs = SegmentCost.objects.filter(segment__in = segments)
        cost_dicts = [{'hash' : cost.segment.hash_value, 'cost' : cost.cost} for cost in costs]
        return HttpResponse(json.dumps({'ok' : True, 'costs' : cost_dicts}), mimetype='text/json')
    except:
        return error_response()

def set_segment_solutions(request, project_id = None, stack_id = None):
    p = get_object_or_404(Project, pk = project_id)
    u = User.objects.get(id = 1)

    try:
        n = int(request.GET.get('n'))
        core_id = int(request.GET.get('core_id'))
        solution_dict = {}
        hash_values = []
        count = 0

        core = Core.objects.get(id = core_id)

        # Collect all of the solution values and map them to the hash of the segment in question
        # Collect a list of hash values as well
        for i in range(n):
            i_str = str(i)
            hash_value = request.GET.get('hash_' + i_str)
            hash_values.append(hash_value)
            solution_dict[hash_value] = request.GET.get('solution_' + i_str).lower() in ['true', 'yes', '1']

        # filter all of the segments out in a single hit. Note that we might not get a Segment object for every
        # requested hash.
        segments = Segment.objects.filter(hash_value__in = hash_values)

        # Now, set the solution values.
        for segment in segments:
            hash_value = segment.hash_value
            solution = solution_dict[hash_value]
            # If there is already a SegmentSolution for this segment/core pair, just update it.
            try:
                segment_solution = SegmentSolution.objects.get(core = core, segment = segment)
                segment_solution.solution = solution
            except SegmentSolution.DoesNotExist:
                segment_solution = SegmentSolution(project = p, user = u, core = core,
                                                   segment = segment, solution = solution)
            segment_solution.save()
            count += 1

        return HttpResponse(json.dumps({'ok' : True, 'count' : count}), mimetype='text/json')

    except:
        return error_response()

def retrieve_segment_solutions(request, project_id = None, stack_id = None):
    try:
        hash_values = request.GET.get('hash').split(',')
        core_id = int(request.GET.get('core_id'))
        segments = Segment.objects.filter(hash_value__in = hash_values)
        core = Core.objects.get(pk = core_id)
        solutions = SegmentSolution.objects.filter(core = core, segment__in = segments)

        solution_dicts = [{'hash' : solution.segment.hash_value,
                           'solution' : solution.solution} for solution in solutions]

        return HttpResponse(json.dumps({'ok' : True, 'solutions' : solution_dicts}),
                            mimetype='text/json')
    except:
        return error_response()

def retrieve_block_ids_by_segments(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    try:
        segment_hashes = request.GET.get('hash').split(',')

        segments = Segment.objects.filter(stack = s, hash_value__in = segment_hashes)
        block_relations = SegmentBlockRelation.objects.filter(segment__in = segments)
        blocks = {br.block for br in block_relations}
        block_ids = [block.id for block in blocks]

        return HttpResponse(json.dumps({'ok' : True, 'block_ids' : block_ids}), mimetype='text/json')
    except:
        return error_response()

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

def clear_djsopnet(request, project_id = None, stack_id = None):
    s = get_object_or_404(Stack, pk = stack_id)
    sure = request.GET.get('sure')
    if sure == 'yes':
        all_blocks = Block.objects.filter(stack = s)
        all_block_conflict_relations = BlockConflictRelation.objects.filter(block__in = all_blocks)
        all_conflicts = {bcr.conflict for bcr in all_block_conflict_relations}
        all_segments = Segment.objects.filter(stack = s)
        all_slices = Slice.objects.filter(stack = s)

        all_slice_assembly = {slice.assembly for slice in all_slices}
        all_segment_assembly = {segment.assembly for segment in all_segments}
        all_assemblies = all_segment_assembly.union(all_slice_assembly)
        assembly_ids = {assembly.id for assembly in all_assemblies if assembly is not None}

        Assembly.objects.filter(id__in = assembly_ids).delete()
        SliceConflictSet.objects.filter(id__in = (conflict.id for conflict in all_conflicts)).delete()

        SliceConflictRelation.objects.filter(conflict__in = all_conflicts).delete()
        SegmentBlockRelation.objects.filter(block__in = all_blocks).delete()
        SegmentFeatures.objects.filter(segment__in = all_segments).delete()
        SegmentCost.objects.filter(segment__in = all_segments).delete()
        SegmentSolution.objects.filter(segment__in = all_segments).delete()

        all_blocks.delete()

        for slice in all_slices:
            slice.delete()

        all_segments.delete()

        Core.objects.filter(stack = s).delete()
        BlockInfo.objects.filter(stack = s).delete()
        return HttpResponse(json.dumps({'ok': True}), mimetype='text/json')
    else:
        return HttpResponse(json.dumps({'ok': False}), mimetype='text/json')

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

def create_project_config(project_id, stack_id):
    """
    Creates a configuration dictionary for Sopnet.
    """
    config = {
        'catmaid_project_id': project_id,
        'catmaid_stack_id': stack_id,
    }
    if hasattr(settings, 'SOPNET_BACKEND_TYPE'):
        config['backend_type'] = settings.SOPNET_BACKEND_TYPE
    if hasattr(settings, 'SOPNET_CATMAID_HOST'):
        config['catmaid_host'] = settings.SOPNET_CATMAID_HOST
    if hasattr(settings, 'SOPNET_BLOCK_SIZE'):
        config['block_size'] = settings.SOPNET_BLOCK_SIZE
    if hasattr(settings, 'SOPNET_VOLUME_SIZE'):
        config['volume_size'] = settings.SOPNET_VOLUME_SIZE
    if hasattr(settings, 'SOPNET_CORE_SIZE'):
        config['core_size'] = settings.SOPNET_CORE_SIZE

    return config

def test_sliceguarantor_task(request, project_id, stack_id, x, y, z):
    config = create_project_config(project_id, stack_id)
    async_result = SliceGuarantorTask.delay(config, x, y, z)
    return HttpResponse(json.dumps({
        'success': "Successfully queued slice guarantor task.",
        'task_id': async_result.id
    }))

def test_segmentguarantor_task(request, project_id, stack_id, x, y, z):
    config = create_project_config(project_id, stack_id)
    async_result = SegmentGuarantorTask.delay(config, x, y, z)
    return HttpResponse(json.dumps({
        'success': "Successfully queued segment guarantor task.",
        'task_id': async_result.id
    }))

def test_solutionguarantor_task(request, project_id, stack_id, x, y, z):
    config = create_project_config(project_id, stack_id)
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
