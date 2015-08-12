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


# --- Configuration ---
@requires_user_role([UserRole.Annotate, UserRole.Browse])
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
                ''', [project_id, ps.id])
        configs = [r[0] for r in cursor.fetchall()]
        if len(configs) == 0:
            raise Http404('No segmentation is configured involving this project and stack.')
        return HttpResponse('[' + ','.join(map(str, configs)) + ']', content_type='text/json')

    return HttpResponseNotAllowed(['GET'])


# --- convenience code for debug purposes ---

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

def test_sliceguarantor_task(request, project_id, configuration_id, x, y, z):
    sc = get_object_or_404(SegmentationConfiguration, pk=configuration_id, project_id=project_id)
    config = sc.to_pysopnet_configuration()
    async_result = SliceGuarantorTask.delay(config, x, y, z, log_level=getattr(settings, 'SOPNET_LOG_LEVEL', None))
    return HttpResponse(json.dumps({
        'success': "Successfully queued slice guarantor task.",
        'task_id': async_result.id
    }))

def test_segmentguarantor_task(request, project_id, configuration_id, x, y, z):
    sc = get_object_or_404(SegmentationConfiguration, pk=configuration_id, project_id=project_id)
    config = sc.to_pysopnet_configuration()
    async_result = SegmentGuarantorTask.delay(config, x, y, z, log_level=getattr(settings, 'SOPNET_LOG_LEVEL', None))
    return HttpResponse(json.dumps({
        'success': "Successfully queued segment guarantor task.",
        'task_id': async_result.id
    }))

def test_solutionguarantor_task(request, project_id, configuration_id, x, y, z):
    sc = get_object_or_404(SegmentationConfiguration, pk=configuration_id, project_id=project_id)
    config = sc.to_pysopnet_configuration()
    async_result = SolutionGuarantorTask.delay(config, x, y, z, log_level=getattr(settings, 'SOPNET_LOG_LEVEL', None))
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
    config = segstack.configuration.to_pysopnet_configuration()
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
