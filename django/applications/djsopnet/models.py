from django.db import models
from datetime import datetime

from django.contrib.auth.models import User
from catmaid.fields import IntegerArrayField, FloatArrayField
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
    hash_value = models.CharField(max_length=20, primary_key=True)
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

class Segment(UserFocusedModel):
    stack = models.ForeignKey(Stack)
    assembly = models.ForeignKey(Assembly, null=True)
    hash_value = models.CharField(max_length=20, primary_key = True)
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
    slice_a_hash = models.CharField(Slice, max_length=20, null=True, db_index=True)
    slice_b_hash = models.CharField(Slice, max_length=20, null=True, db_index=True)
    slice_c_hash = models.CharField(Slice, max_length=20, null=True, db_index=True)

class Block(UserFocusedModel):
    stack = models.ForeignKey(Stack)

    # bounding box
    min_x = models.IntegerField(db_index=True)
    min_y = models.IntegerField(db_index=True)
    max_x = models.IntegerField(db_index=True)
    max_y = models.IntegerField(db_index=True)
    min_z = models.IntegerField(db_index=True)
    max_z = models.IntegerField(db_index=True)

    slices_flag = models.BooleanField(default=False)
    segments_flag = models.BooleanField(default=False)
    solution_cost_flag = models.BooleanField(default=False)

class Core(UserFocusedModel):
    stack = models.ForeignKey(Stack)

    # bounding box
    min_x = models.IntegerField(db_index=True)
    min_y = models.IntegerField(db_index=True)
    max_x = models.IntegerField(db_index=True)
    max_y = models.IntegerField(db_index=True)
    min_z = models.IntegerField(db_index=True)
    max_z = models.IntegerField(db_index=True)

    solution_set_flag = models.BooleanField(default=False)

class SegmentSolution(UserFocusedModel):
    core = models.ForeignKey(Core, db_index=True)
    segment = models.ForeignKey(Segment, db_index=True)
    solution = models.BooleanField()

class SegmentCost(UserFocusedModel):
    segment = models.OneToOneField(Segment, db_index=True)
    cost = models.FloatField()

class SegmentFeatures(UserFocusedModel):
    segment = models.OneToOneField(Segment, db_index=True)
    features = FloatArrayField()

class SliceBlockRelation(UserFocusedModel):
    block = models.ForeignKey(Block, db_index=True)
    slice = models.ForeignKey(Slice, db_index=True)

class SegmentBlockRelation(UserFocusedModel):
    block = models.ForeignKey(Block, db_index=True)
    segment = models.ForeignKey(Segment, db_index=True)

class BlockInfo(UserFocusedModel):
    stack = models.ForeignKey(Stack)

    # Block height, width, depth, measured units of pixels
    bheight = models.IntegerField(default=256)
    bwidth = models.IntegerField(default=256)
    bdepth = models.IntegerField(default=16)

    # Core height, width, depth, measured in units of Blocks
    cheight = models.IntegerField(default=1)
    cwidth = models.IntegerField(default=1)
    cdepth = models.IntegerField(default=1)

    # Number of blocks in x, y and z

    num_x = models.IntegerField(default=0)
    num_y = models.IntegerField(default=0)
    num_z = models.IntegerField(default=0)

class FeatureName(models.Model):
    name = models.CharField(max_length=128)

class FeatureNameInfo(UserFocusedModel):
    stack = models.ForeignKey(Stack)
    name_ids = IntegerArrayField()
    size = models.IntegerField(default = 0)

class SliceConflictSet(models.Model):
    pass

class SliceConflictRelation(UserFocusedModel):
    slice = models.ForeignKey(Slice)
    conflict = models.ForeignKey(SliceConflictSet)

class BlockConflictRelation(UserFocusedModel):
    block = models.ForeignKey(Block)
    conflict = models.ForeignKey(SliceConflictSet)

class ViewProperties(models.Model):
    assembly = models.ForeignKey(Assembly)
    color = models.TextField(default='#0000ff')
    opacity = models.FloatField(default=0.5)