from django.db import models
from datetime import datetime

from catmaid.fields import IntegerArrayField, DoubleArrayField
from catmaid.models import ClassInstance, Stack, UserFocusedModel, Treenode
from djsopnet.fields import *

class AssemblyEquivalence(models.Model):
    skeleton = models.ForeignKey(ClassInstance)

class Assembly(models.Model):
    equivalence = models.ForeignKey(AssemblyEquivalence, null=True)
    solution = models.ForeignKey('Solution')

class AssemblyRelation(models.Model):
    assembly_a = models.ForeignKey(Assembly, related_name='relations_as_a')
    assembly_b = models.ForeignKey(Assembly, related_name='relations_as_b')
    relation = AssemblyRelationEnumField(default='Conflict')

    class Meta:
        unique_together = ('assembly_a', 'assembly_b', 'relation')

class Slice(models.Model):
    id = models.BigIntegerField(primary_key=True)
    stack = models.ForeignKey(Stack)
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
            SELECT ssol.id AS id, ssol.solution_id AS solution_id, ssol.segment_id AS segment_id
            FROM djsopnet_segmentsolution ssol
            JOIN djsopnet_solutionprecedence sp ON (sp.solution_id = ssol.solution_id)
            JOIN djsopnet_segmentslice ss ON (ss.segment_id = ssol.segment_id)
            WHERE ss.slice_id = %s
            ''', [self.id])))
    in_solution = property(_get_in_solution)

    def _get_segment_summaries(self):
        return self.segmentslice_set.values('segment_id', 'direction')
    segment_summaries = property(_get_segment_summaries)

class TreenodeSlice(models.Model):
    treenode = models.ForeignKey(Treenode)
    slice = models.ForeignKey(Slice)

class Segment(models.Model):
    id = models.BigIntegerField(primary_key=True)
    stack = models.ForeignKey(Stack)
    # section supremum, i.e., the larger of the two sections bounding this
    # inter-section interval
    section_sup = models.IntegerField(db_index=True)

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

    cost = models.FloatField(null=True, default=None)

    def _get_in_solution(self):
        return 0 < len(list(SegmentSolution.objects.raw('''
            SELECT ssol.id AS id, ssol.solution_id AS solution_id, ssol.segment_id AS segment_id
            FROM djsopnet_segmentsolution ssol
            JOIN djsopnet_solutionprecedence sp ON (sp.solution_id = ssol.solution_id)
            WHERE ssol.segment_id = %s
            ''', [self.id])))
    in_solution = property(_get_in_solution)

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
        zoom = 2**bi.scale
        return {'x': zoom * bi.block_dim_x,
                'y': zoom * bi.block_dim_y,
                'z': bi.block_dim_z}

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
        zoom = 2**bi.scale
        return {'x': zoom * bi.core_dim_x * bi.block_dim_x,
                'y': zoom * bi.core_dim_y * bi.block_dim_y,
                'z': bi.core_dim_z * bi.block_dim_z}

    def _get_box(self):
        size = Core.size_for_stack(self.stack)
        size = [size['x'], size['y'], size['z']]
        coords = [self.coordinate_x, self.coordinate_y, self.coordinate_z]
        return [s*c for s,c in zip(size, coords)] + \
                [s*(c+1) for s,c in zip(size, coords)]
    box = property(_get_box)

    class Meta:
        unique_together = ('stack', 'coordinate_x', 'coordinate_y', 'coordinate_z')

class Solution(models.Model):
    core = models.ForeignKey(Core)
    creation_time = models.DateTimeField(default=datetime.now)

class SolutionPrecedence(models.Model):
    core = models.ForeignKey(Core, unique=True)
    solution = models.OneToOneField(Solution)

class SegmentSolution(models.Model):
    solution = models.ForeignKey(Solution)
    segment = models.ForeignKey(Segment)
    assembly = models.ForeignKey(Assembly, null=True)

    class Meta:
        unique_together = ('solution', 'segment')

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
    name = models.CharField(max_length=128)

class FeatureInfo(models.Model):
    stack = models.OneToOneField(Stack, unique=True)
    size = models.IntegerField(default=0)
    name_ids = IntegerArrayField()
    weights = DoubleArrayField()

class SliceConflict(models.Model):
    slice_a = models.ForeignKey(Slice, related_name='conflicts_as_a')
    slice_b = models.ForeignKey(Slice, related_name='conflicts_as_b')

    class Meta:
        unique_together = ('slice_a', 'slice_b')

class ConflictClique(models.Model):
    id = models.BigIntegerField(primary_key=True)
    maximal_clique = models.BooleanField(default=True)
    edges = models.ManyToManyField(SliceConflict, db_table='djsopnet_conflictcliqueedge')

class BlockConflictRelation(models.Model):
    block = models.ForeignKey(Block)
    slice_conflict = models.ForeignKey(SliceConflict)

    class Meta:
        unique_together = ('block', 'slice_conflict')

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

class Correction(models.Model):
    constraint = models.ForeignKey(Constraint)
    mistake = models.ForeignKey(SegmentSolution)

    class Meta:
        unique_together = ('constraint', 'mistake')
