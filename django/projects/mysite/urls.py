from django.conf.urls.defaults import patterns, include, url
from django.conf import settings

from catmaid.views import *

import catmaid
import vncbrowser

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
from adminplus import AdminSitePlus
admin.site = AdminSitePlus()
admin.autodiscover()

# CATMAID
urlpatterns = patterns('',
    url(r'^', include('catmaid.urls')),
)

# Neuron Catalog
urlpatterns += patterns('',
    url(r'^vncbrowser/', include('vncbrowser.urls')),
)

# Admin site
urlpatterns += patterns('',
    url(r'^admin/', include(admin.site.urls))
)

# Sopnet API
urlpatterns += patterns('',
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/sopnet/setup_blocks$', 'catmaid.control.setup_blocks'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/sopnet/block_at_location$', 'catmaid.control.block_at_location'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/sopnet/block$', 'catmaid.control.block_info'),

     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/sopnet/segment_flag$', 'catmaid.control.set_block_segment_flag'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/sopnet/slice_flag$', 'catmaid.control.set_block_slice_flag'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/sopnet/insert_slice$', 'catmaid.control.insert_slice'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/sopnet/slices_block$', 'catmaid.control.set_slices_block'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/sopnet/slices_by_hash$', 'catmaid.control.retrieve_slices_by_hash'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/sopnet/slices_by_id$', 'catmaid.control.retrieve_slices_by_dbid'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/sopnet/slices_by_block$', 'catmaid.control.retrieve_slices_by_block'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/sopnet/set_parent_slices$', 'catmaid.control.set_parent_slice'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/sopnet/get_parent_slices$', 'catmaid.control.retrieve_parent_slices'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/sopnet/get_child_slices$', 'catmaid.control.retrieve_child_slices'),

     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/sopnet/insert_end_segment$', 'catmaid.control.insert_end_segment'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/sopnet/insert_continuation_segment$', 'catmaid.control.insert_continuation_segment'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/sopnet/insert_branch_segment$', 'catmaid.control.insert_branch_segment'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/sopnet/segments_block$', 'catmaid.control.set_segments_block'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/sopnet/segments_by_hash$', 'catmaid.control.retrieve_segments_by_hash'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/sopnet/segments_by_id$', 'catmaid.control.retrieve_segments_by_dbid'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/sopnet/segments_by_block$', 'catmaid.control.retrieve_segments_by_block'),

     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/sopnet/clear_segments$', 'catmaid.control.clear_segments'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/sopnet/clear_slices$', 'catmaid.control.clear_slices'),
     (r'^(?P<project_id>\d+)/stack/(?P<stack_id>\d+)/sopnet/clear_blocks$', 'catmaid.control.clear_blocks'),

     )

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.STATIC_ROOT}),
        (r'^%s(?P<path>.*)$' % settings.MEDIA_URL.replace(settings.CATMAID_URL, ''),
            'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
    )
