from django.db import connection, models
from django.db.models.signals import post_save
from django.dispatch import receiver
import os
import logging

from catmaid.fields import IntegerArrayField, DoubleArrayField
from catmaid.models import Project, ProjectStack
from djsopnet.fields import *

logger = logging.getLogger(__name__)

class SegmentationConfiguration(models.Model):
    class Meta:
        db_table = 'segmentation_configuration'

    project = models.ForeignKey(Project)


class SegmentationStack(models.Model):
    class Meta:
        db_table = 'segmentation_stack'

    configuration = models.ForeignKey(SegmentationConfiguration)
    project_stack = models.ForeignKey(ProjectStack)
    type = models.CharField(max_length=128)


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

    scale = models.IntegerField(default=0)

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


class FeatureInfo(models.Model):
    class Meta:
        db_table = 'segmentation_feature_info'

    segmentation_stack = models.OneToOneField(SegmentationStack, primary_key=True)
    size = models.IntegerField(default=0)
    name_ids = IntegerArrayField()
    weights = DoubleArrayField()
