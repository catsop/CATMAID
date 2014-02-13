from django.db import models
from datetime import datetime

from django.contrib.auth.models import User
from catmaid.fields import IntegerArrayField
from catmaid.models import Stack, UserFocusedModel

ASSEMBLY_TYPES = (
    ('neuron', 'Neuron Slices'),
    ('synapse', 'Synapse Slices'),
    ('mitochondrion', 'Mitochondrion Slices'),
    ('glia', 'Glia Slices'),
)

class Assembly(models.Model):
    user = models.ForeignKey(User)
    creation_time = models.DateTimeField(default=datetime.now)
    edition_time = models.DateTimeField(default=datetime.now)
    assembly_type = models.CharField(max_length=32, choices=ASSEMBLY_TYPES,
     db_index=True)
    name = models.CharField(max_length=255)

class Slice(UserFocusedModel):
    stack = models.ForeignKey(Stack)
    assembly = models.ForeignKey(Assembly, null=True)
    hash_value = models.IntegerField(db_index=True)
    section = models.IntegerField(db_index=True)

    # bounding box
    min_x = models.IntegerField(db_index=True)
    min_y = models.IntegerField(db_index=True)
    max_x = models.IntegerField(db_index=True)
    max_y = models.IntegerField(db_index=True)

    # centroid
    ctr_x = models.FloatField()
    ctr_y = models.FloatField()

    # MSER-applied value
    value = models.FloatField()

    # Geometry
    shape_x = IntegerArrayField()
    shape_y = IntegerArrayField()

    size = models.IntegerField(db_index=True)

    # Tree
    parent = models.ForeignKey('self', null=True)

class Segment(UserFocusedModel):
    stack = models.ForeignKey(Stack)
    assembly = models.ForeignKey(Assembly, null=True)
    hash_value = models.IntegerField(db_index=True)
    # section infimum, or rather, the id of the section closest to z = -infinity to which this segment belongs.
    section_inf = models.IntegerField(db_index=True)

    # bounding box
    min_x = models.IntegerField(db_index=True)
    min_y = models.IntegerField(db_index=True)
    max_x = models.IntegerField(db_index=True)
    max_y = models.IntegerField(db_index=True)

    # centroid
    ctr_x = models.FloatField()
    ctr_y = models.FloatField()

    # type
    # 0 - End
    # 1 - Continuation
    # 2 - Branch
    type = models.IntegerField(db_index=True)

    # direction
    # 0 - "Left"
    # 1 - "Right"
    direction = models.IntegerField(db_index=True)

    # Slice relations
    slice_a = models.ForeignKey(Slice, db_index=True, related_name='slice_a')
    slice_b = models.ForeignKey(Slice, null=True, db_index=True, related_name='slice_b')
    slice_c = models.ForeignKey(Slice, null=True, db_index=True, related_name='slice_c')

class Block(UserFocusedModel):
    stack = models.ForeignKey(Stack)

    # bounding box
    min_x = models.IntegerField(db_index=True)
    min_y = models.IntegerField(db_index=True)
    max_x = models.IntegerField(db_index=True)
    max_y = models.IntegerField(db_index=True)
    min_z = models.IntegerField(db_index=True)
    max_z = models.IntegerField(db_index=True)

    slices = IntegerArrayField()
    segments = IntegerArrayField()

    slices_flag = models.BooleanField(default=False)
    segments_flag = models.BooleanField(default=False)

class BlockInfo(UserFocusedModel):
    stack = models.ForeignKey(Stack)

    height = models.IntegerField()
    width = models.IntegerField()
    depth = models.IntegerField()

    num_x = models.IntegerField()
    num_y = models.IntegerField()
    num_z = models.IntegerField()