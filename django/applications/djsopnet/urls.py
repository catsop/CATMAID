from django.conf.urls.defaults import patterns, url
from django.views.generic import TemplateView

# Sopnet API
urlpatterns = patterns('djsopnet.views',
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/setup_blocks$', 'setup_blocks'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/block_at_location$', 'block_at_location'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/block$', 'block_info'),

     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/segment_flag$', 'set_block_segment_flag'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/slice_flag$', 'set_block_slice_flag'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/insert_slice$', 'insert_slice'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/slices_block$', 'set_slices_block'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/slices_by_hash$', 'retrieve_slices_by_hash'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/slices_by_id$', 'retrieve_slices_by_dbid'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/slices_by_block$', 'retrieve_slices_by_block'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/set_parent_slices$', 'set_parent_slice'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/get_parent_slices$', 'retrieve_parent_slices'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/get_child_slices$', 'retrieve_child_slices'),

     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/insert_end_segment$', 'insert_end_segment'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/insert_continuation_segment$', 'insert_continuation_segment'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/insert_branch_segment$', 'insert_branch_segment'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/segments_block$', 'set_segments_block'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/segments_by_hash$', 'retrieve_segments_by_hash'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/segments_by_id$', 'retrieve_segments_by_dbid'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/segments_by_block$', 'retrieve_segments_by_block'),

     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/clear_segments$', 'clear_segments'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/clear_slices$', 'clear_slices'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/clear_blocks$', 'clear_blocks'),

     (r'^trace_neuron$', 'trace_neuron_async'),

     # Models
     (r'^tasks$', 'get_task_list'),

     # Front-end
     (r'^$', TemplateView.as_view(template_name='djsopnet/index.html')),
     (r'^overview$', TemplateView.as_view(template_name='djsopnet/partials/overview.html')),
)
