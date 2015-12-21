from django.conf.urls import patterns, include, url
from django.conf import settings

from catmaid.views import *
from catmaid.control.authentication import ObtainAuthToken

import catmaid
import djsopnet

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
from adminplus.sites import AdminSitePlus
admin.site = AdminSitePlus()
admin.autodiscover()

# CATMAID
urlpatterns = patterns('',
    url(r'^', include('catmaid.urls')),
)

# Admin site
urlpatterns += patterns('',
    url(r'^admin/', include(admin.site.urls))
)

# API Documentation
urlpatterns += patterns('',
    url(r'^apis/', include('rest_framework_swagger.urls')),
    url(r'^api-token-auth/', ObtainAuthToken.as_view()),
)

# Sopnet
urlpatterns += patterns('',
    url(r'^sopnet/', include('djsopnet.urls')),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.STATIC_ROOT}),
        # Access to static estensions in debug mode, remove leading slash.
        (r'^%s(?P<path>.*)$' % settings.STATIC_EXTENSION_URL[1:],
            'django.views.static.serve', {'document_root': settings.STATIC_EXTENSION_ROOT}),
        (r'^%s(?P<path>.*)$' % settings.MEDIA_URL.replace(settings.CATMAID_URL, ''),
            'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
    )
