import logging
import os
import re

from django.conf import settings
from django.db import connection, models
from django.db.models.signals import post_save
from django.dispatch import receiver

import pysopnet

from catmaid.fields import IntegerArrayField, DoubleArrayField
from catmaid.models import Project, ProjectStack
from djsopnet.fields import *

logger = logging.getLogger(__name__)

class SegmentationConfiguration(models.Model):
    class Meta:
        db_table = 'segmentation_configuration'

    project = models.ForeignKey(Project)

    def __unicode__(self):
        return u'%s (%s)' % (self.project, self.pk)

    def to_pysopnet_configuration(self):
        bi = self.block_info
        conf = pysopnet.ProjectConfiguration()
        conf.setBackendType(pysopnet.BackendType.PostgreSql)
        min_depth = float('inf')

        for segstack in self.segmentationstack_set.all():
            stack = segstack.project_stack.stack
            stack_desc = pysopnet.StackDescription()
            # Strings require special handling to convert from unicode to std::string
            stack_desc.imageBase = stack.image_base.encode('utf8')
            stack_desc.fileExtension = stack.file_extension.encode('utf8')
            stack_desc.width = stack.dimension.x
            stack_desc.height = stack.dimension.y
            stack_desc.depth = stack.dimension.z
            min_depth = min(stack_desc.depth, min_depth)
            stack.resX = stack.resolution.x
            stack.resY = stack.resolution.y
            stack.resZ = stack.resolution.z
            stack_desc.scale = bi.scale
            stack_desc.id = stack.id
            stack_desc.segmentationId = segstack.id
            for name in ['tile_source_type', 'tile_width', 'tile_height']:
                camel_name = re.sub(r'(?!^)_([a-zA-Z])', lambda m: m.group(1).upper(), name)
                setattr(stack_desc, camel_name, getattr(stack, name))

            stack_type = pysopnet.StackType.names[segstack.type]
            conf.setCatmaidStack(stack_type, stack_desc)

        conf.setComponentDirectory(settings.SOPNET_COMPONENT_DIR)
        conf.setBlockSize(pysopnet.point3(bi.block_dim_x, bi.block_dim_y, bi.block_dim_z))
        conf.setVolumeSize(pysopnet.point3(bi.block_dim_x*bi.num_x,
                bi.block_dim_y*bi.num_y,
                min(bi.block_dim_z*bi.num_z, min_depth)))
        conf.setCoreSize(pysopnet.point3(bi.core_dim_x, bi.core_dim_y, bi.core_dim_z))
        conf.setPostgreSqlDatabase(settings.SOPNET_DATABASE['NAME'])
        conf.setPostgreSqlHost(settings.SOPNET_DATABASE['HOST'])
        conf.setPostgreSqlPort(settings.SOPNET_DATABASE['PORT'])
        conf.setPostgreSqlUser(settings.SOPNET_DATABASE['USER'])
        conf.setPostgreSqlPassword(settings.SOPNET_DATABASE['PASSWORD'])

        return conf


class SegmentationStack(models.Model):
    class Meta:
        db_table = 'segmentation_stack'

    configuration = models.ForeignKey(SegmentationConfiguration)
    project_stack = models.ForeignKey(ProjectStack)
    type = models.CharField(max_length=128)

    def __unicode__(self):
        return u'Segstack %s: %s' % (self.pk, self.project_stack)


@receiver(post_save, sender=SegmentationStack)
def create_segmentation_stack_schema(sender, instance, created, **kwargs):
    if created:
        cursor = connection.cursor()
        cursor.execute('''
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name = 'segstack_%s';
            ''' % instance.id)
        if cursor.rowcount:
            logger.warning('''
                Schema for segmentation stack %s already exists. No schema changes made.
                ''' % instance.id)
        else:
            with open(os.path.join(os.path.dirname(__file__), 'sql', 'instantiate_segmentation.sql'), 'r') as sqlfile:
                cursor.execute(('''
                    CREATE SCHEMA segstack_%(segstack_id)s;
                    SET search_path TO segstack_%(segstack_id)s,public;
                    ''' % {'segstack_id': instance.id}) + \
                    sqlfile.read() +\
                    'RESET search_path;')


class BlockInfo(models.Model):
    class Meta:
        db_table = 'segmentation_block_info'

    configuration = models.OneToOneField(SegmentationConfiguration, primary_key=True,
            related_name='block_info')

    scale = models.IntegerField(default=0, help_text='''
        Zoom level for segmentation data relative to raw stack.''')

    # Block height, width, depth, measured units of scaled pixels
    block_dim_x = models.IntegerField(default=256)
    block_dim_y = models.IntegerField(default=256)
    block_dim_z = models.IntegerField(default=16)

    # Core height, width, depth, measured in units of Blocks
    core_dim_x = models.IntegerField(default=1)
    core_dim_y = models.IntegerField(default=1)
    core_dim_z = models.IntegerField(default=1)

    # Number of blocks in x, y and z
    num_x = models.IntegerField(default=0)
    num_y = models.IntegerField(default=0)
    num_z = models.IntegerField(default=0)

    def __unicode__(self):
        return u'%s block info' % (self.configuration,)

    def save(self, *args, **kwargs):
        # Set the number of blocks based on the size of the raw stack.
        if not kwargs.get('raw', False):
            stack = SegmentationStack.objects.get(
                            configuration_id=self.configuration_id,
                            type='Raw').project_stack.stack

            # The number of blocks is the ceiling of the stack size divided by block dimension
            def int_ceil(num, den): return ((num - 1) // den) + 1
            self.num_x = int_ceil(stack.dimension.x, self.block_dim_x * 2**self.scale)
            self.num_y = int_ceil(stack.dimension.y, self.block_dim_y * 2**self.scale)
            self.num_z = int_ceil(stack.dimension.z, self.block_dim_z)

        super(BlockInfo, self).save(*args, **kwargs)

        self.setup_blocks()

    def setup_blocks(self):
        """Creates blocks and cores in each segmentation stack schema."""
        cursor = connection.cursor()
        for segstack in self.configuration.segmentationstack_set.all():
            cursor.execute('SELECT 1 FROM segstack_%s.block LIMIT 1' % segstack.id)
            if cursor.rowcount > 0:
                logger.warning('Blocks for SegmentationStack %s are already setup.', segstack.id)
                continue

            cursor.execute('''
                    INSERT INTO segstack_{0}.block
                      (slices_flag, segments_flag, coordinate_x, coordinate_y, coordinate_z)
                        SELECT false, false, x.id, y.id, z.id FROM
                          generate_series(0, %s - 1) AS x (id),
                          generate_series(0, %s - 1) AS y (id),
                          generate_series(0, %s - 1) AS z (id);
                    '''.format(segstack.id), (self.num_x, self.num_y, self.num_z))

            # Create new Cores, round up if number of blocks is not divisible by core size
            nzc = (self.num_z + self.core_dim_z - 1)/self.core_dim_z
            nyc = (self.num_y + self.core_dim_y - 1)/self.core_dim_y
            nxc = (self.num_x + self.core_dim_x - 1)/self.core_dim_x
            cursor.execute('''
                    INSERT INTO segstack_{0}.core
                      (solution_set_flag, coordinate_x, coordinate_y, coordinate_z)
                        SELECT false, x.id, y.id, z.id FROM
                          generate_series(0, %s - 1) AS x (id),
                          generate_series(0, %s - 1) AS y (id),
                          generate_series(0, %s - 1) AS z (id);
                    '''.format(segstack.id), (nxc, nyc, nzc))

    @staticmethod
    def update_or_create(configuration_id, scale, width, height, depth, corewib, corehib, coredib):
        """Updates or creates a segmentation configuration block decomposition.
        """
        # TODO: this method should be removed once upgraded to Django 1.7,
        # since it provides this functionality with a different signature.
        try:
            info = BlockInfo.objects.get(configuration_id=configuration_id)
            info.block_dim_x = width
            info.block_dim_y = height
            info.block_dim_z = depth
            info.core_dim_x = corewib
            info.core_dim_y = corehib
            info.core_dim_z = coredib
            info.save()
        except BlockInfo.DoesNotExist:
            info = BlockInfo(configuration_id=configuration_id, scale=scale,
                             block_dim_y=height, block_dim_x=width, block_dim_z=depth,
                             core_dim_y=corehib, core_dim_x=corewib, core_dim_z=coredib)
            info.save()

    def size_for_unit(self, table):
        if table == 'block':
            zoom = 2**self.scale
            return {'x': zoom * self.block_dim_x,
                    'y': zoom * self.block_dim_y,
                    'z': self.block_dim_z}
        elif table == 'core':
            zoom = 2**self.scale
            return {'x': zoom * self.core_dim_x * self.block_dim_x,
                    'y': zoom * self.core_dim_y * self.block_dim_y,
                    'z': self.core_dim_z * self.block_dim_z}
        else:
            raise ValueError('%s is not a blockwise unit' % table)


class FeatureName(models.Model):
    class Meta:
        db_table = 'segmentation_feature_name'

    name = models.CharField(max_length=128)

    def __unicode__(self):
        return self.name


class FeatureInfo(models.Model):
    class Meta:
        db_table = 'segmentation_feature_info'

    segmentation_stack = models.OneToOneField(SegmentationStack, primary_key=True)
    size = models.IntegerField(default=0)
    name_ids = IntegerArrayField()
    weights = DoubleArrayField()

    def __unicode__(self):
        return u'%s feature info' % (self.segmentation_stack,)
