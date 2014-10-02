from django.db import models
from datetime import datetime

from django.contrib.auth.models import User
from catmaid.fields import IntegerArrayField, DoubleArrayField
from catmaid.models import ClassInstance, Stack, UserFocusedModel

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

class Slice(models.Model):
    id = models.BigIntegerField(primary_key=True)
    stack = models.ForeignKey(Stack)
    assembly = models.ForeignKey(Assembly, null=True)
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
    shape_x = IntegerArrayField(null=True)
    shape_y = IntegerArrayField(null=True)

    size = models.IntegerField(db_index=True)

class Segment(models.Model):
    id = models.BigIntegerField(primary_key=True)
    stack = models.ForeignKey(Stack)
    assembly = models.ForeignKey(Assembly, null=True)
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

class SegmentSlice(models.Model):
    slice = models.ForeignKey(Slice)
    segment = models.ForeignKey(Segment)
    direction = models.BooleanField() # true for left, false for right

    class Meta:
        unique_together = ('slice', 'segment')

class Block(models.Model):
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

class Core(models.Model):
    stack = models.ForeignKey(Stack)

    # bounding box
    min_x = models.IntegerField(db_index=True)
    min_y = models.IntegerField(db_index=True)
    max_x = models.IntegerField(db_index=True)
    max_y = models.IntegerField(db_index=True)
    min_z = models.IntegerField(db_index=True)
    max_z = models.IntegerField(db_index=True)

    solution_set_flag = models.BooleanField(default=False)

class SegmentSolution(models.Model):
    core = models.ForeignKey(Core)
    segment = models.ForeignKey(Segment)

    class Meta:
        unique_together = ('core', 'segment')

class SegmentFeatures(models.Model):
    segment = models.OneToOneField(Segment)
    features = DoubleArrayField()

class SliceBlockRelation(models.Model):
    block = models.ForeignKey(Block)
    slice = models.ForeignKey(Slice)

    class Meta:
        unique_together = ('block', 'slice')

class SegmentBlockRelation(models.Model):
    block = models.ForeignKey(Block)
    segment = models.ForeignKey(Segment)

    class Meta:
        unique_together = ('block', 'segment')

class BlockInfo(models.Model):
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

class FeatureInfo(models.Model):
    stack = models.OneToOneField(Stack, unique=True)
    size = models.IntegerField(default=0)
    name_ids = IntegerArrayField()
    weights = DoubleArrayField()

class SliceConflictSet(models.Model):
    slice_a = models.ForeignKey(Slice, related_name='conflicts_as_a')
    slice_b = models.ForeignKey(Slice, related_name='conflicts_as_b')

    class Meta:
        unique_together = ('slice_a', 'slice_b')

class BlockConflictRelation(models.Model):
    block = models.ForeignKey(Block)
    conflict = models.ForeignKey(SliceConflictSet)

    class Meta:
        unique_together = ('block', 'conflict')

class Constraint(UserFocusedModel):

    pass

    # the skeleton that defined the constraint
    # skeleton = models.ForeignKey(ClassInstance, null=True, default=None)

    # TODO: remove this property
    # associated_skeleton_nodes = IntegerArrayField(null=True, default=None)

class BlockConstraintRelation(models.Model):
    constraint = models.ForeignKey(Constraint)
    block = models.ForeignKey(Block)

class ConstraintSegmentRelation(models.Model):
    constraint = models.ForeignKey(Constraint)
    segment = models.ForeignKey(Segment)
