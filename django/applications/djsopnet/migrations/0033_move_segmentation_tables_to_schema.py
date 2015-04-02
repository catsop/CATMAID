# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
import os


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Removing unique constraint on 'AssemblyRelation', fields ['assembly_a', 'assembly_b', 'relation']
        db.delete_unique(u'djsopnet_assemblyrelation', ['assembly_a_id', 'assembly_b_id', 'relation'])

        # Removing unique constraint on 'SegmentSlice', fields ['slice', 'segment']
        db.delete_unique(u'djsopnet_segmentslice', ['slice_id', 'segment_id'])

        # Removing unique constraint on 'Core', fields ['stack', 'coordinate_x', 'coordinate_y', 'coordinate_z']
        db.delete_unique(u'djsopnet_core', ['stack_id', 'coordinate_x', 'coordinate_y', 'coordinate_z'])

        # Removing unique constraint on 'SegmentSolution', fields ['solution', 'segment']
        db.delete_unique(u'djsopnet_segmentsolution', ['solution_id', 'segment_id'])

        # Removing unique constraint on 'SliceBlockRelation', fields ['block', 'slice']
        db.delete_unique(u'djsopnet_sliceblockrelation', ['block_id', 'slice_id'])

        # Removing unique constraint on 'SliceConflict', fields ['slice_a', 'slice_b']
        db.delete_unique(u'djsopnet_sliceconflict', ['slice_a_id', 'slice_b_id'])

        # Removing unique constraint on 'Correction', fields ['constraint', 'mistake']
        db.delete_unique(u'djsopnet_correction', ['constraint_id', 'mistake_id'])

        # Removing unique constraint on 'SegmentBlockRelation', fields ['block', 'segment']
        db.delete_unique(u'djsopnet_segmentblockrelation', ['block_id', 'segment_id'])

        # Removing unique constraint on 'BlockConflictRelation', fields ['block', 'slice_conflict']
        db.delete_unique(u'djsopnet_blockconflictrelation', ['block_id', 'slice_conflict_id'])

        # Removing unique constraint on 'Block', fields ['stack', 'coordinate_x', 'coordinate_y', 'coordinate_z']
        db.delete_unique(u'djsopnet_block', ['stack_id', 'coordinate_x', 'coordinate_y', 'coordinate_z'])

        # Deleting model 'Block'
        db.delete_table(u'djsopnet_block')

        # Deleting model 'TreenodeSlice'
        db.delete_table(u'djsopnet_treenodeslice')

        # Deleting model 'SegmentFeatures'
        db.delete_table(u'djsopnet_segmentfeatures')

        # Deleting model 'BlockConflictRelation'
        db.delete_table(u'djsopnet_blockconflictrelation')

        # Deleting model 'SegmentBlockRelation'
        db.delete_table(u'djsopnet_segmentblockrelation')

        # Deleting model 'Correction'
        db.delete_table(u'djsopnet_correction')

        # Deleting model 'SolutionPrecedence'
        db.delete_table(u'djsopnet_solutionprecedence')

        # Deleting model 'Constraint'
        db.delete_table(u'djsopnet_constraint')

        # Deleting model 'Assembly'
        db.delete_table(u'djsopnet_assembly')

        # Deleting model 'Solution'
        db.delete_table(u'djsopnet_solution')

        # Deleting model 'Segment'
        db.delete_table(u'djsopnet_segment')

        # Deleting model 'Slice'
        db.delete_table(u'djsopnet_slice')

        # Deleting model 'SliceConflict'
        db.delete_table(u'djsopnet_sliceconflict')

        # Deleting model 'ConflictClique'
        db.delete_table(u'djsopnet_conflictclique')

        # Removing M2M table for field edges on 'ConflictClique'
        db.delete_table('djsopnet_conflictcliqueedge')

        # Deleting model 'SliceBlockRelation'
        db.delete_table(u'djsopnet_sliceblockrelation')

        # Deleting model 'SegmentSolution'
        db.delete_table(u'djsopnet_segmentsolution')

        # Deleting model 'ConstraintSegmentRelation'
        db.delete_table(u'djsopnet_constraintsegmentrelation')

        # Deleting model 'Core'
        db.delete_table(u'djsopnet_core')

        # Deleting model 'SegmentSlice'
        db.delete_table(u'djsopnet_segmentslice')

        # Deleting model 'AssemblyRelation'
        db.delete_table(u'djsopnet_assemblyrelation')

        # Deleting model 'AssemblyEquivalence'
        db.delete_table(u'djsopnet_assemblyequivalence')

        # Deleting model 'BlockConstraintRelation'
        db.delete_table(u'djsopnet_blockconstraintrelation')

        # Adding model 'SegmentationStack'
        db.create_table('segmentation_stack', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('configuration', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.SegmentationConfiguration'])),
            ('project_stack', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['catmaid.ProjectStack'])),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=128)),
        ))
        db.send_create_signal(u'djsopnet', ['SegmentationStack'])

        # Adding model 'SegmentationConfiguration'
        db.create_table('segmentation_configuration', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['catmaid.Project'])),
        ))
        db.send_create_signal(u'djsopnet', ['SegmentationConfiguration'])

        # Deleting field 'FeatureInfo.id'
        db.delete_column(u'djsopnet_featureinfo', u'id')

        # Deleting field 'FeatureInfo.stack'
        db.delete_column(u'djsopnet_featureinfo', 'stack_id')

        db.rename_table('djsopnet_featureinfo', 'segmentation_feature_info')
        db.rename_table('djsopnet_featurename', 'segmentation_feature_name')
        db.execute('TRUNCATE TABLE segmentation_feature_info;')
        # Adding field 'FeatureInfo.segmentation_stack'
        db.add_column('segmentation_feature_info', 'segmentation_stack',
                      self.gf('django.db.models.fields.related.OneToOneField')(default=0, to=orm['djsopnet.SegmentationStack'], unique=True, primary_key=True),
                      keep_default=False)

        # Deleting field 'BlockInfo.id'
        db.delete_column(u'djsopnet_blockinfo', u'id')

        # Deleting field 'BlockInfo.stack'
        db.delete_column(u'djsopnet_blockinfo', 'stack_id')

        db.rename_table('djsopnet_blockinfo', 'segmentation_block_info')
        db.execute('TRUNCATE TABLE segmentation_block_info;')

        # Adding field 'BlockInfo.configuration'
        db.add_column('segmentation_block_info', 'configuration',
                      self.gf('django.db.models.fields.related.OneToOneField')(default=0, to=orm['djsopnet.SegmentationConfiguration'], unique=True, primary_key=True),
                      keep_default=False)

        with open(os.path.join(os.path.dirname(__file__), '..', 'sql', 'segmentation_schema_initial.sql'), 'r') as sqlfile:
            db.execute(sqlfile.read())


    def backwards(self, orm):
        # Adding model 'Block'
        db.create_table(u'djsopnet_block', (
            ('slices_flag', self.gf('django.db.models.fields.BooleanField')(default=False)),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('segments_flag', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('stack', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['catmaid.Stack'])),
            ('coordinate_z', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('coordinate_y', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('coordinate_x', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
        ))
        db.send_create_signal(u'djsopnet', ['Block'])

        # Adding unique constraint on 'Block', fields ['stack', 'coordinate_x', 'coordinate_y', 'coordinate_z']
        db.create_unique(u'djsopnet_block', ['stack_id', 'coordinate_x', 'coordinate_y', 'coordinate_z'])

        # Adding model 'TreenodeSlice'
        db.create_table(u'djsopnet_treenodeslice', (
            ('slice', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.Slice'])),
            ('treenode', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['catmaid.Treenode'])),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal(u'djsopnet', ['TreenodeSlice'])

        # Adding model 'SegmentFeatures'
        db.create_table(u'djsopnet_segmentfeatures', (
            ('segment', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['djsopnet.Segment'], unique=True, primary_key=True)),
            ('features', self.gf('catmaid.fields.DoubleArrayField')()),
        ))
        db.send_create_signal(u'djsopnet', ['SegmentFeatures'])

        # Adding model 'BlockConflictRelation'
        db.create_table(u'djsopnet_blockconflictrelation', (
            ('slice_conflict', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.SliceConflict'])),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('block', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.Block'])),
        ))
        db.send_create_signal(u'djsopnet', ['BlockConflictRelation'])

        # Adding unique constraint on 'BlockConflictRelation', fields ['block', 'slice_conflict']
        db.create_unique(u'djsopnet_blockconflictrelation', ['block_id', 'slice_conflict_id'])

        # Adding model 'SegmentBlockRelation'
        db.create_table(u'djsopnet_segmentblockrelation', (
            ('segment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.Segment'])),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('block', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.Block'])),
        ))
        db.send_create_signal(u'djsopnet', ['SegmentBlockRelation'])

        # Adding unique constraint on 'SegmentBlockRelation', fields ['block', 'segment']
        db.create_unique(u'djsopnet_segmentblockrelation', ['block_id', 'segment_id'])

        # Adding model 'Correction'
        db.create_table(u'djsopnet_correction', (
            ('mistake', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.SegmentSolution'])),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('constraint', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.Constraint'])),
        ))
        db.send_create_signal(u'djsopnet', ['Correction'])

        # Adding unique constraint on 'Correction', fields ['constraint', 'mistake']
        db.create_unique(u'djsopnet_correction', ['constraint_id', 'mistake_id'])

        # Adding model 'SolutionPrecedence'
        db.create_table(u'djsopnet_solutionprecedence', (
            ('core', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['djsopnet.Core'], unique=True, primary_key=True)),
            ('solution', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['djsopnet.Solution'], unique=True)),
        ))
        db.send_create_signal(u'djsopnet', ['SolutionPrecedence'])

        # Adding model 'Constraint'
        db.create_table(u'djsopnet_constraint', (
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['catmaid.Project'])),
            ('value', self.gf('django.db.models.fields.FloatField')(default=1.0)),
            ('relation', self.gf('djsopnet.fields.ConstraintRelationEnumField')(default='Equal')),
            ('skeleton', self.gf('django.db.models.fields.related.ForeignKey')(default=None, to=orm['catmaid.ClassInstance'], null=True)),
            ('creation_time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('edition_time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
        ))
        db.send_create_signal(u'djsopnet', ['Constraint'])

        # Adding model 'Assembly'
        db.create_table(u'djsopnet_assembly', (
            ('equivalence', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.AssemblyEquivalence'], null=True)),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('solution', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.Solution'])),
        ))
        db.send_create_signal(u'djsopnet', ['Assembly'])

        # Adding model 'Solution'
        db.create_table(u'djsopnet_solution', (
            ('core', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.Core'])),
            ('creation_time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal(u'djsopnet', ['Solution'])

        # Adding model 'Segment'
        db.create_table(u'djsopnet_segment', (
            ('cost', self.gf('django.db.models.fields.FloatField')(default=None, null=True)),
            ('stack', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['catmaid.Stack'])),
            ('min_x', self.gf('django.db.models.fields.IntegerField')()),
            ('min_y', self.gf('django.db.models.fields.IntegerField')()),
            ('ctr_y', self.gf('django.db.models.fields.FloatField')()),
            ('ctr_x', self.gf('django.db.models.fields.FloatField')()),
            ('id', self.gf('django.db.models.fields.BigIntegerField')(primary_key=True)),
            ('section_sup', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('type', self.gf('django.db.models.fields.IntegerField')()),
            ('max_x', self.gf('django.db.models.fields.IntegerField')()),
            ('max_y', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal(u'djsopnet', ['Segment'])

        # Adding model 'Slice'
        db.create_table(u'djsopnet_slice', (
            ('stack', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['catmaid.Stack'])),
            ('size', self.gf('django.db.models.fields.IntegerField')()),
            ('min_x', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('min_y', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('section', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('ctr_y', self.gf('django.db.models.fields.FloatField')()),
            ('ctr_x', self.gf('django.db.models.fields.FloatField')()),
            ('value', self.gf('django.db.models.fields.FloatField')()),
            ('id', self.gf('django.db.models.fields.BigIntegerField')(primary_key=True)),
            ('max_x', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('max_y', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
        ))
        db.send_create_signal(u'djsopnet', ['Slice'])

        # Adding model 'SliceConflict'
        db.create_table(u'djsopnet_sliceconflict', (
            ('slice_a', self.gf('django.db.models.fields.related.ForeignKey')(related_name='conflicts_as_a', to=orm['djsopnet.Slice'])),
            ('slice_b', self.gf('django.db.models.fields.related.ForeignKey')(related_name='conflicts_as_b', to=orm['djsopnet.Slice'])),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal(u'djsopnet', ['SliceConflict'])

        # Adding unique constraint on 'SliceConflict', fields ['slice_a', 'slice_b']
        db.create_unique(u'djsopnet_sliceconflict', ['slice_a_id', 'slice_b_id'])

        # Adding model 'ConflictClique'
        db.create_table(u'djsopnet_conflictclique', (
            ('maximal_clique', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('id', self.gf('django.db.models.fields.BigIntegerField')(primary_key=True)),
        ))
        db.send_create_signal(u'djsopnet', ['ConflictClique'])

        # Adding M2M table for field edges on 'ConflictClique'
        m2m_table_name = 'djsopnet_conflictcliqueedge'
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('conflictclique', models.ForeignKey(orm[u'djsopnet.conflictclique'], null=False)),
            ('sliceconflict', models.ForeignKey(orm[u'djsopnet.sliceconflict'], null=False))
        ))
        db.create_unique(m2m_table_name, ['conflictclique_id', 'sliceconflict_id'])

        # Adding model 'SliceBlockRelation'
        db.create_table(u'djsopnet_sliceblockrelation', (
            ('slice', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.Slice'])),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('block', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.Block'])),
        ))
        db.send_create_signal(u'djsopnet', ['SliceBlockRelation'])

        # Adding unique constraint on 'SliceBlockRelation', fields ['block', 'slice']
        db.create_unique(u'djsopnet_sliceblockrelation', ['block_id', 'slice_id'])

        # Adding model 'SegmentSolution'
        db.create_table(u'djsopnet_segmentsolution', (
            ('segment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.Segment'])),
            ('assembly', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.Assembly'], null=True)),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('solution', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.Solution'])),
        ))
        db.send_create_signal(u'djsopnet', ['SegmentSolution'])

        # Adding unique constraint on 'SegmentSolution', fields ['solution', 'segment']
        db.create_unique(u'djsopnet_segmentsolution', ['solution_id', 'segment_id'])

        # Adding model 'ConstraintSegmentRelation'
        db.create_table(u'djsopnet_constraintsegmentrelation', (
            ('coefficient', self.gf('django.db.models.fields.FloatField')(default=1.0)),
            ('segment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.Segment'])),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('constraint', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.Constraint'])),
        ))
        db.send_create_signal(u'djsopnet', ['ConstraintSegmentRelation'])

        # Adding model 'Core'
        db.create_table(u'djsopnet_core', (
            ('solution_set_flag', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('coordinate_z', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('coordinate_y', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('coordinate_x', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('stack', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['catmaid.Stack'])),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal(u'djsopnet', ['Core'])

        # Adding unique constraint on 'Core', fields ['stack', 'coordinate_x', 'coordinate_y', 'coordinate_z']
        db.create_unique(u'djsopnet_core', ['stack_id', 'coordinate_x', 'coordinate_y', 'coordinate_z'])

        # Adding model 'SegmentSlice'
        db.create_table(u'djsopnet_segmentslice', (
            ('slice', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.Slice'])),
            ('direction', self.gf('django.db.models.fields.BooleanField')()),
            ('segment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.Segment'])),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal(u'djsopnet', ['SegmentSlice'])

        # Adding unique constraint on 'SegmentSlice', fields ['slice', 'segment']
        db.create_unique(u'djsopnet_segmentslice', ['slice_id', 'segment_id'])

        # Adding model 'AssemblyRelation'
        db.create_table(u'djsopnet_assemblyrelation', (
            ('assembly_b', self.gf('django.db.models.fields.related.ForeignKey')(related_name='relations_as_b', to=orm['djsopnet.Assembly'])),
            ('assembly_a', self.gf('django.db.models.fields.related.ForeignKey')(related_name='relations_as_a', to=orm['djsopnet.Assembly'])),
            ('relation', self.gf('djsopnet.fields.AssemblyRelationEnumField')(default='Conflict')),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal(u'djsopnet', ['AssemblyRelation'])

        # Adding unique constraint on 'AssemblyRelation', fields ['assembly_a', 'assembly_b', 'relation']
        db.create_unique(u'djsopnet_assemblyrelation', ['assembly_a_id', 'assembly_b_id', 'relation'])

        # Adding model 'AssemblyEquivalence'
        db.create_table(u'djsopnet_assemblyequivalence', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('skeleton', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['catmaid.ClassInstance'], null=True)),
        ))
        db.send_create_signal(u'djsopnet', ['AssemblyEquivalence'])

        # Adding model 'BlockConstraintRelation'
        db.create_table(u'djsopnet_blockconstraintrelation', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('block', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.Block'])),
            ('constraint', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.Constraint'])),
        ))
        db.send_create_signal(u'djsopnet', ['BlockConstraintRelation'])

        # Deleting model 'SegmentationStack'
        db.delete_table('segmentation_stack')

        # Deleting model 'SegmentationConfiguration'
        db.delete_table('segmentation_configuration')

        # Adding field 'FeatureInfo.id'
        db.add_column(u'djsopnet_featureinfo', u'id',
                      self.gf('django.db.models.fields.AutoField')(default=1, primary_key=True),
                      keep_default=False)

        # Adding field 'FeatureInfo.stack'
        db.add_column(u'djsopnet_featureinfo', 'stack',
                      self.gf('django.db.models.fields.related.OneToOneField')(default=1, to=orm['catmaid.Stack'], unique=True),
                      keep_default=False)

        # Deleting field 'FeatureInfo.segmentation_stack'
        db.delete_column('segmentation_feature_info', 'segmentation_stack_id')


        # User chose to not deal with backwards NULL issues for 'BlockInfo.id'
        raise RuntimeError("Cannot reverse this migration. 'BlockInfo.id' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration        # Adding field 'BlockInfo.id'
        db.add_column(u'djsopnet_blockinfo', u'id',
                      self.gf('django.db.models.fields.AutoField')(primary_key=True),
                      keep_default=False)


        # User chose to not deal with backwards NULL issues for 'BlockInfo.stack'
        raise RuntimeError("Cannot reverse this migration. 'BlockInfo.stack' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration        # Adding field 'BlockInfo.stack'
        db.add_column(u'djsopnet_blockinfo', 'stack',
                      self.gf('django.db.models.fields.related.OneToOneField')(to=orm['catmaid.Stack'], unique=True),
                      keep_default=False)

        # Deleting field 'BlockInfo.configuration'
        db.delete_column('segmentation_block_info', 'configuration_id')


    models = {
        u'catmaid.project': {
            'Meta': {'object_name': 'Project', 'db_table': "'project'"},
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'stacks': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['catmaid.Stack']", 'through': u"orm['catmaid.ProjectStack']", 'symmetrical': 'False'}),
            'title': ('django.db.models.fields.TextField', [], {})
        },
        u'catmaid.projectstack': {
            'Meta': {'object_name': 'ProjectStack', 'db_table': "'project_stack'"},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'orientation': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'stack': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Stack']"}),
            'translation': ('catmaid.fields.Double3DField', [], {'default': '(0, 0, 0)'})
        },
        u'catmaid.stack': {
            'Meta': {'object_name': 'Stack', 'db_table': "'stack'"},
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'dimension': ('catmaid.fields.Integer3DField', [], {}),
            'file_extension': ('django.db.models.fields.TextField', [], {'default': "'jpg'", 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image_base': ('django.db.models.fields.TextField', [], {}),
            'metadata': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'num_zoom_levels': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'resolution': ('catmaid.fields.Double3DField', [], {}),
            'tile_height': ('django.db.models.fields.IntegerField', [], {'default': '256'}),
            'tile_source_type': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'tile_width': ('django.db.models.fields.IntegerField', [], {'default': '256'}),
            'title': ('django.db.models.fields.TextField', [], {}),
            'trakem2_project': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'djsopnet.blockinfo': {
            'Meta': {'object_name': 'BlockInfo', 'db_table': "'segmentation_block_info'"},
            'block_dim_x': ('django.db.models.fields.IntegerField', [], {'default': '256'}),
            'block_dim_y': ('django.db.models.fields.IntegerField', [], {'default': '256'}),
            'block_dim_z': ('django.db.models.fields.IntegerField', [], {'default': '16'}),
            'configuration': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['djsopnet.SegmentationConfiguration']", 'unique': 'True', 'primary_key': 'True'}),
            'core_dim_x': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'core_dim_y': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'core_dim_z': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'num_x': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_y': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_z': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'scale': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'djsopnet.featureinfo': {
            'Meta': {'object_name': 'FeatureInfo', 'db_table': "'segmentation_feature_info'"},
            'name_ids': ('catmaid.fields.IntegerArrayField', [], {}),
            'segmentation_stack': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['djsopnet.SegmentationStack']", 'unique': 'True', 'primary_key': 'True'}),
            'size': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'weights': ('catmaid.fields.DoubleArrayField', [], {})
        },
        u'djsopnet.featurename': {
            'Meta': {'object_name': 'FeatureName', 'db_table': "'segmentation_feature_name'"},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'djsopnet.segmentationconfiguration': {
            'Meta': {'object_name': 'SegmentationConfiguration', 'db_table': "'segmentation_configuration'"},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"})
        },
        u'djsopnet.segmentationstack': {
            'Meta': {'object_name': 'SegmentationStack', 'db_table': "'segmentation_stack'"},
            'configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.SegmentationConfiguration']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project_stack': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.ProjectStack']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        }
    }

    complete_apps = ['djsopnet']