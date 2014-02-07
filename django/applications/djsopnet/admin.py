from django.contrib import admin

from djsopnet.models import Block, BlockInfo, Slice, Segment

# Add basic model admin views
admin.site.register(Block)
admin.site.register(BlockInfo)
admin.site.register(Slice)
admin.site.register(Segment)
