from django.conf.urls import url
from django.views.generic import TemplateView

from djsopnet import views as djsopnet_views
from djsopnet.control import (assembly, block, segment, skeleton_intersection,
        slice as slice_control)


app_name = 'djsopnet'

# Sopnet API
urlpatterns = [
    url(r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/configurations$', djsopnet_views.segmentation_configurations),

    url(r'^(?P<project_id>\d+)/segmentation/(?P<segmentation_stack_id>\d+)/core/(?P<core_id>\d+)/solve$', djsopnet_views.solve_core),

    # Models
    url(r'^tasks$', djsopnet_views.get_task_list),

    # Front-end
    url(r'^$', TemplateView.as_view(template_name='djsopnet/index.html')),
    url(r'^overview$', TemplateView.as_view(template_name='djsopnet/partials/overview.html')),

    # Tests
    url(r'^(?P<project_id>\d+)/configuration/(?P<configuration_id>\d+)/segmentguarantor/(?P<x>\d+)/(?P<y>\d+)/(?P<z>\d+)/test$',
            djsopnet_views.test_segmentguarantor_task),
    url(r'^(?P<project_id>\d+)/configuration/(?P<configuration_id>\d+)/sliceguarantor/(?P<x>\d+)/(?P<y>\d+)/(?P<z>\d+)/test$',
            djsopnet_views.test_sliceguarantor_task),
    url(r'^(?P<project_id>\d+)/configuration/(?P<configuration_id>\d+)/solutionguarantor/(?P<x>\d+)/(?P<y>\d+)/(?P<z>\d+)/test$',
            djsopnet_views.test_solutionguarantor_task),
    url(r'^solvesubvolume/test$', djsopnet_views.test_solvesubvolume_task),
    url(r'^traceneuron/test$', djsopnet_views.test_traceneuron_task),
]

urlpatterns += [
    url(r'^(?P<project_id>\d+)/segmentation/(?P<segmentation_stack_id>\d+)/assembly_equivalence/(?P<equivalence_id>\d+)/map_to_skeleton$',
        assembly.map_assembly_equivalence_to_skeleton)
]

urlpatterns += [
    url(r'^(?P<project_id>\d+)/configuration/(?P<configuration_id>\d+)/setup_blocks$', block.setup_blocks),
    url(r'^(?P<project_id>\d+)/segmentation/(?P<segmentation_stack_id>\d+)/(?P<unit_type>core|block)_at_location$', block.spatial_unit_at_location),
    url(r'^(?P<project_id>\d+)/segmentation/(?P<segmentation_stack_id>\d+)/(?P<unit_type>core|block)s/by_bounding_box$', block.retrieve_spatial_units_by_bounding_box),
    url(r'^(?P<project_id>\d+)/configuration/(?P<configuration_id>\d+)/block$', block.get_block_info),
]

urlpatterns += [
    url(r'^(?P<project_id>\d+)/segmentation/(?P<segmentation_stack_id>\d+)/segment_and_conflicts$', segment.retrieve_segment_and_conflicts),
    url(r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/features_by_segments$', segment.get_segment_features),
    url(r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/solutions_by_core_and_segments$', segment.retrieve_segment_solutions),
    url(r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/set_feature_names$', segment.set_feature_names),
    url(r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/feature_names$', segment.retrieve_feature_names),
    url(r'^(?P<project_id>\d+)/segmentation/(?P<segmentation_stack_id>\d+)/segment/create_for_slices$', segment.create_segment_for_slices),
    url(r'^(?P<project_id>\d+)/segmentation/(?P<segmentation_stack_id>\d+)/segments/constraints$', segment.retrieve_constraints),
    url(r'^(?P<project_id>\d+)/segmentation/(?P<segmentation_stack_id>\d+)/segment/(?P<segment_hash>\d+)/constrain$', segment.constrain_segment),
    url(r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/user_constraints_by_blocks$', segment.retrieve_user_constraints_by_blocks),
]

urlpatterns += [
    url(r'^(?P<project_id>\d+)/segmentation/(?P<segmentation_stack_id>\d+)/skeleton/(?P<skeleton_id>\d+)/generate_user_constraints$', skeleton_intersection.generate_user_constraints),
]

urlpatterns += [
    url(r'^(?P<project_id>\d+)/segmentation/(?P<segmentation_stack_id>\d+)/slices_by_blocks_and_conflict$',
        slice_control.retrieve_slices_by_blocks_and_conflict),
    url(r'^(?P<project_id>\d+)/segmentation/(?P<segmentation_stack_id>\d+)/slices/mask/(?P<slice_hash>\d+).png$',
        slice_control.slice_mask),
    url(r'^(?P<project_id>\d+)/segmentation/(?P<segmentation_stack_id>\d+)/slices/by_location$', slice_control.retrieve_slices_by_location),
    url(r'^(?P<project_id>\d+)/segmentation/(?P<segmentation_stack_id>\d+)/slices/by_bounding_box$', slice_control.retrieve_slices_by_bounding_box),
    url(r'^(?P<project_id>\d+)/segmentation/(?P<segmentation_stack_id>\d+)/conflict_sets_by_slice$', slice_control.retrieve_conflict_sets),
]

# urlpatterns += patterns('djsopnet.control.slice',
#     # 3D Viewer retrieval methods for debugging
#     url(r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/slices_for_skeleton/(?P<skeleton_id>\d+)$', 'retrieve_slices_for_skeleton'),
# )
