from django.conf.urls import patterns, url
from django.views.generic import TemplateView

# Sopnet API
urlpatterns = patterns('djsopnet.views',
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/setup_blocks$', 'setup_blocks'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/block_at_location$', 'block_at_location'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/blocks_in_box$', 'blocks_in_bounding_box'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/core_at_location$', 'core_at_location'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/cores_in_box$', 'cores_in_bounding_box'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/cores_by_id$', 'retrieve_cores_by_id'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/blocks_by_id$', 'retrieve_blocks_by_id'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/block$', 'block_info'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/stack_info$', 'stack_info'),

    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/set_segments_flag$', 'set_block_segment_flag'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/set_slices_flag$', 'set_block_slice_flag'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/set_solution_cost_flag$', 'set_block_solution_flag'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/set_solution_set_flag$', 'set_core_solution_flag'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/get_segments_flag$', 'get_block_segment_flag'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/get_slices_flag$', 'get_block_slice_flag'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/get_solution_cost_flag$', 'get_block_solution_flag'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/get_solution_set_flag$', 'get_core_solution_flag'),

    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/insert_slices$', 'insert_slices'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/slices_block$', 'associate_slices_to_block'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/slices_by_hash$', 'retrieve_slices_by_hash'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/slices_by_blocks_and_conflict$',
        'retrieve_slices_by_blocks_and_conflict'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/store_conflict_set$', 'store_conflict_set'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/conflict_sets_by_slice$', 'retrieve_conflict_sets'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/blocks_by_slice$', 'retrieve_block_ids_by_slices'),

    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/insert_segments$', 'insert_segments'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/segments_block$', 'associate_segments_to_block'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/segments_by_hash$', 'retrieve_segments_by_hash'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/segments_by_blocks$', 'retrieve_segments_by_blocks'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/store_segment_features$', 'set_segment_features'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/features_by_segments$', 'get_segment_features'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/store_segment_costs$', 'set_segment_costs'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/costs_by_segments$', 'retrieve_segment_costs'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/store_segment_solutions$', 'set_segment_solutions'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/solutions_by_core_and_segments$', 'retrieve_segment_solutions'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/set_feature_names$', 'set_feature_names'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/feature_names$', 'retrieve_feature_names'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/user_constraints_by_blocks$', 'retrieve_user_constraints_by_blocks'),

    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/clear_segments$', 'clear_segments'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/clear_slices$', 'clear_slices'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/clear_blocks$', 'clear_blocks'),
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/clear_djsopnet$', 'clear_djsopnet'),

    # 3D Viewer retrieval methods for debugging
    (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/slices_for_skeleton/(?P<skeleton_id>\d+)$', 'retrieve_slices_for_skeleton'),

    # Models
    (r'^tasks$', 'get_task_list'),

    # Front-end
    (r'^$', TemplateView.as_view(template_name='djsopnet/index.html')),
    (r'^overview$', TemplateView.as_view(template_name='djsopnet/partials/overview.html')),

    # Tests
    (r'^segmentguarantor/(?P<pid>\d+)/(?P<raw_sid>\d+)/(?P<membrane_sid>\d+)/(?P<x>\d+)/(?P<y>\d+)/(?P<z>\d+)/test$',
            'test_segmentguarantor_task'),
    (r'^sliceguarantor/(?P<pid>\d+)/(?P<raw_sid>\d+)/(?P<membrane_sid>\d+)/(?P<x>\d+)/(?P<y>\d+)/(?P<z>\d+)/test$',
            'test_sliceguarantor_task'),
    (r'^solutionguarantor/(?P<pid>\d+)/(?P<raw_sid>\d+)/(?P<membrane_sid>\d+)/(?P<x>\d+)/(?P<y>\d+)/(?P<z>\d+)/test$',
            'test_solutionguarantor_task'),
    (r'^solvesubvolume/test$', 'test_solvesubvolume_task'),
    (r'^traceneuron/test$', 'test_traceneuron_task'),
)
