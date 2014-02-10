from django.conf.urls.defaults import patterns, url

# Sopnet API
urlpatterns = patterns('',
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/setup_blocks$', 'djsopnet.views.setup_blocks'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/block_at_location$', 'djsopnet.views.block_at_location'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/block$', 'djsopnet.views.block_info'),

     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/segment_flag$', 'djsopnet.views.set_block_segment_flag'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/slice_flag$', 'djsopnet.views.set_block_slice_flag'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/insert_slice$', 'djsopnet.views.insert_slice'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/slices_block$', 'djsopnet.views.set_slices_block'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/slices_by_hash$', 'djsopnet.views.retrieve_slices_by_hash'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/slices_by_id$', 'djsopnet.views.retrieve_slices_by_dbid'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/slices_by_block$', 'djsopnet.views.retrieve_slices_by_block'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/set_parent_slices$', 'djsopnet.views.set_parent_slice'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/get_parent_slices$', 'djsopnet.views.retrieve_parent_slices'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/get_child_slices$', 'djsopnet.views.retrieve_child_slices'),

     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/insert_end_segment$', 'djsopnet.views.insert_end_segment'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/insert_continuation_segment$', 'djsopnet.views.insert_continuation_segment'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/insert_branch_segment$', 'djsopnet.views.insert_branch_segment'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/segments_block$', 'djsopnet.views.set_segments_block'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/segments_by_hash$', 'djsopnet.views.retrieve_segments_by_hash'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/segments_by_id$', 'djsopnet.views.retrieve_segments_by_dbid'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/segments_by_block$', 'djsopnet.views.retrieve_segments_by_block'),

     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/clear_segments$', 'djsopnet.views.clear_segments'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/clear_slices$', 'djsopnet.views.clear_slices'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/clear_blocks$', 'djsopnet.views.clear_blocks'),

     (r'^trace_neuron$', 'djsopnet.views.trace_neuron_async'),
)
