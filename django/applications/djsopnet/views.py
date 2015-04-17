import json

from django.http import Http404, HttpResponse, HttpResponseNotAllowed

from django.shortcuts import get_object_or_404
from django.db import connection
from django.conf import settings

from catmaid.models import *
from catmaid.control.stack import get_stack_info
from catmaid.control.authentication import requires_user_role
from models import *

from celerysopnet.tasks import SliceGuarantorTask, SegmentGuarantorTask
from celerysopnet.tasks import SolutionGuarantorTask, SolveSubvolumeTask
from celerysopnet.tasks import TraceNeuronTask

from djsopnet.control.block import _blockcursor_to_namedtuple
from djcelery.models import TaskState

# from djsopnet.control.slice import retrieve_slices_for_skeleton
# from djsopnet.control.skeleton_intersection import generate_user_constraints


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


def stack_info(request, project_id = None, stack_id = None):
    # TODO: circumventing user role requirements in CATMAID
    result=get_stack_info(project_id, stack_id, request.user)
    return HttpResponse(json.dumps(result, sort_keys=True, indent=4), content_type="text/json")


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
        '''.format(segstack.id), (core_id,))
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
