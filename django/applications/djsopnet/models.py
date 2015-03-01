from django.db import connection, models
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import datetime
import os

from catmaid.fields import IntegerArrayField, DoubleArrayField
from catmaid.models import ClassInstance, Project, ProjectStack, UserFocusedModel, Treenode
from djsopnet.fields import *

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

    configuration = models.OneToOneField(SegmentationConfiguration, primary_key=True)

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
