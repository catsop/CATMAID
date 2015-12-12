from django.conf.urls import patterns
from django.views.generic import TemplateView

# Sopnet API
urlpatterns = patterns('djsopnet.views',
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/configurations$', 'segmentation_configurations'),

    (r'^(?P<project_id>\d+)/segmentation/(?P<segmentation_stack_id>\d+)/core/(?P<core_id>\d+)/solve$', 'solve_core'),

    # Models
    (r'^tasks$', 'get_task_list'),

    # Front-end
    (r'^$', TemplateView.as_view(template_name='djsopnet/index.html')),
    (r'^overview$', TemplateView.as_view(template_name='djsopnet/partials/overview.html')),

    # Tests
    (r'^(?P<project_id>\d+)/configuration/(?P<configuration_id>\d+)/segmentguarantor/(?P<x>\d+)/(?P<y>\d+)/(?P<z>\d+)/test$',
            'test_segmentguarantor_task'),
    (r'^(?P<project_id>\d+)/configuration/(?P<configuration_id>\d+)/sliceguarantor/(?P<x>\d+)/(?P<y>\d+)/(?P<z>\d+)/test$',
            'test_sliceguarantor_task'),
    (r'^(?P<project_id>\d+)/configuration/(?P<configuration_id>\d+)/solutionguarantor/(?P<x>\d+)/(?P<y>\d+)/(?P<z>\d+)/test$',
            'test_solutionguarantor_task'),
    (r'^solvesubvolume/test$', 'test_solvesubvolume_task'),
    (r'^traceneuron/test$', 'test_traceneuron_task'),
)

urlpatterns += patterns('djsopnet.control.assembly',
    (r'^(?P<project_id>\d+)/segmentation/(?P<segmentation_stack_id>\d+)/assembly_equivalence/(?P<equivalence_id>\d+)/map_to_skeleton$',
        'map_assembly_equivalence_to_skeleton')
)

urlpatterns += patterns('djsopnet.control.block',
    (r'^(?P<project_id>\d+)/configuration/(?P<configuration_id>\d+)/setup_blocks$', 'setup_blocks'),
    (r'^(?P<project_id>\d+)/segmentation/(?P<segmentation_stack_id>\d+)/(?P<unit_type>core|block)_at_location$', 'spatial_unit_at_location'),
    (r'^(?P<project_id>\d+)/segmentation/(?P<segmentation_stack_id>\d+)/(?P<unit_type>core|block)s/by_bounding_box$', 'retrieve_spatial_units_by_bounding_box'),
    (r'^(?P<project_id>\d+)/configuration/(?P<configuration_id>\d+)/block$', 'get_block_info'),
)

urlpatterns += patterns('djsopnet.control.segment',
    (r'^(?P<project_id>\d+)/segmentation/(?P<segmentation_stack_id>\d+)/segment_and_conflicts$', 'retrieve_segment_and_conflicts'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/features_by_segments$', 'get_segment_features'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/solutions_by_core_and_segments$', 'retrieve_segment_solutions'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/set_feature_names$', 'set_feature_names'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/feature_names$', 'retrieve_feature_names'),
    (r'^(?P<project_id>\d+)/segmentation/(?P<segmentation_stack_id>\d+)/segment/create_for_slices$', 'create_segment_for_slices'),
    (r'^(?P<project_id>\d+)/segmentation/(?P<segmentation_stack_id>\d+)/segment/(?P<segment_hash>\d+)/constrain$', 'constrain_segment'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/user_constraints_by_blocks$', 'retrieve_user_constraints_by_blocks'),
)

urlpatterns += patterns('djsopnet.control.skeleton_intersection',
    (r'^(?P<project_id>\d+)/segmentation/(?P<segmentation_stack_id>\d+)/skeleton/(?P<skeleton_id>\d+)/generate_user_constraints$', 'generate_user_constraints'),
)

urlpatterns += patterns('djsopnet.control.slice',
    (r'^(?P<project_id>\d+)/segmentation/(?P<segmentation_stack_id>\d+)/slices_by_blocks_and_conflict$',
        'retrieve_slices_by_blocks_and_conflict'),
    (r'^(?P<project_id>\d+)/segmentation/(?P<segmentation_stack_id>\d+)/slices/by_location$', 'retrieve_slices_by_location'),
    (r'^(?P<project_id>\d+)/segmentation/(?P<segmentation_stack_id>\d+)/slices/by_bounding_box$', 'retrieve_slices_by_bounding_box'),
    (r'^(?P<project_id>\d+)/segmentation/(?P<segmentation_stack_id>\d+)/conflict_sets_by_slice$', 'retrieve_conflict_sets'),
)

# urlpatterns += patterns('djsopnet.control.slice',
#     # 3D Viewer retrieval methods for debugging
#     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/slices_for_skeleton/(?P<skeleton_id>\d+)$', 'retrieve_slices_for_skeleton'),
# )
