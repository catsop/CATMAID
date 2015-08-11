from django.contrib import admin

from djsopnet.models import BlockInfo, FeatureInfo, FeatureName, \
		SegmentationConfiguration, SegmentationStack

class BlockInfoAdmin(admin.ModelAdmin):
    fields = ('configuration',
              'scale',
              ('block_dim_x', 'block_dim_y', 'block_dim_z'),
              ('core_dim_x', 'core_dim_y', 'core_dim_z'),
              ('num_x', 'num_y', 'num_z'),)
    readonly_fields = ('num_x', 'num_y', 'num_z')

# Add basic model admin views
admin.site.register(BlockInfo, BlockInfoAdmin)
admin.site.register(FeatureInfo)
admin.site.register(FeatureName)
admin.site.register(SegmentationConfiguration)
admin.site.register(SegmentationStack)
