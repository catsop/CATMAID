from django.db import models
from datetime import datetime

from django.contrib.auth.models import User
from catmaid.fields import IntegerArrayField, DoubleArrayField
from catmaid.models import ClassInstance, Stack, UserFocusedModel
from djsopnet.fields import *

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

    def _get_conflict_slice_ids(self):
        return list(self.conflicts_as_a.values_list('slice_b_id', flat=True)) \
             + list(self.conflicts_as_b.values_list('slice_a_id', flat=True))
    conflict_slice_ids = property(_get_conflict_slice_ids)

    def _get_in_solution(self):
        return 0 < len(list(SegmentSolution.objects.raw('''
            SELECT ssol.id AS id, ssol.core_id AS core_id, ssol.segment_id AS segment_id
            FROM djsopnet_segmentsolution ssol
            JOIN djsopnet_segmentslice ss ON (ss.segment_id = ssol.segment_id)
            WHERE ss.slice_id = %s
            ''', [self.id])))
    in_solution = property(_get_in_solution)

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

    # coordinates
    coordinate_x = models.IntegerField(db_index=True)
    coordinate_y = models.IntegerField(db_index=True)
    coordinate_z = models.IntegerField(db_index=True)

    slices_flag = models.BooleanField(default=False)
    segments_flag = models.BooleanField(default=False)

    @staticmethod
    def size_for_stack(s):
        bi = s.blockinfo
        return {'x': bi.block_dim_x, 'y': bi.block_dim_y, 'z': bi.block_dim_z}

    def _get_box(self):
        size = Block.size_for_stack(self.stack)
        size = [size['x'], size['y'], size['z']]
        coords = [self.coordinate_x, self.coordinate_y, self.coordinate_z]
        return [s*c for s,c in zip(size, coords)] + \
                [s*(c+1) for s,c in zip(size, coords)]
    box = property(_get_box)

    class Meta:
        unique_together = ('stack', 'coordinate_x', 'coordinate_y', 'coordinate_z')

class Core(models.Model):
    stack = models.ForeignKey(Stack)

    # coordinates
    coordinate_x = models.IntegerField(db_index=True)
    coordinate_y = models.IntegerField(db_index=True)
    coordinate_z = models.IntegerField(db_index=True)

    solution_set_flag = models.BooleanField(default=False)

    @staticmethod
    def size_for_stack(s):
        bi = s.blockinfo
        return {'x': bi.core_dim_x*bi.block_dim_x,
                'y': bi.core_dim_y*bi.block_dim_y,
                'z': bi.core_dim_z*bi.block_dim_z}

    def _get_box(self):
        size = Core.size_for_stack(self.stack)
        size = [size['x'], size['y'], size['z']]
        coords = [self.coordinate_x, self.coordinate_y, self.coordinate_z]
        return [s*c for s,c in zip(size, coords)] + \
                [s*(c+1) for s,c in zip(size, coords)]
    box = property(_get_box)

    class Meta:
        unique_together = ('stack', 'coordinate_x', 'coordinate_y', 'coordinate_z')

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
    stack = models.OneToOneField(Stack)

    # Block height, width, depth, measured units of pixels
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
    # the skeleton that defined the constraint
    skeleton = models.ForeignKey(ClassInstance, null=True, default=None)
    relation = ConstraintRelationEnumField(default='Equal')
    value = models.FloatField(default=1.0)


class BlockConstraintRelation(models.Model):
    constraint = models.ForeignKey(Constraint)
    block = models.ForeignKey(Block)

class ConstraintSegmentRelation(models.Model):
    constraint = models.ForeignKey(Constraint)
    segment = models.ForeignKey(Segment)
    coefficient = models.FloatField(default=1.0)
