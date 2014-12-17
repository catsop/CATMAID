# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        db.rename_table(u'djsopnet_sliceconflictset', u'djsopnet_sliceconflict')

        # Adding model 'ConflictClique'
        db.create_table(u'djsopnet_conflictclique', (
            (u'id', self.gf('django.db.models.fields.BigIntegerField')(primary_key=True)),
            ('maximal_clique', self.gf('django.db.models.fields.BooleanField')(default=True)),
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

        db.rename_column(u'djsopnet_blockconflictrelation', 'conflict_id', 'slice_conflict_id')


    def backwards(self, orm):
        # Deleting model 'SliceConflictSet'
        db.rename_table(u'djsopnet_sliceconflict', u'djsopnet_sliceconflictset')

        # Deleting model 'ConflictClique'
        db.delete_table(u'djsopnet_conflictclique')

        # Removing M2M table for field edges on 'ConflictClique'
        db.delete_table('djsopnet_conflictcliqueedge')

        db.rename_column(u'djsopnet_blockconflictrelation', 'slice_conflict_id', 'conflict_id')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'catmaid.class': {
            'Meta': {'object_name': 'Class', 'db_table': "'class'"},
            'class_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'catmaid.classinstance': {
            'Meta': {'object_name': 'ClassInstance', 'db_table': "'class_instance'"},
            'class_column': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Class']", 'db_column': "'class_id'"}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
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
        u'catmaid.treenode': {
            'Meta': {'object_name': 'Treenode', 'db_table': "'treenode'"},
            'confidence': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'editor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'treenode_editor'", 'db_column': "'editor_id'", 'to': u"orm['auth.User']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location_x': ('django.db.models.fields.FloatField', [], {}),
            'location_y': ('django.db.models.fields.FloatField', [], {}),
            'location_z': ('django.db.models.fields.FloatField', [], {}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'children'", 'null': 'True', 'to': u"orm['catmaid.Treenode']"}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'radius': ('django.db.models.fields.FloatField', [], {}),
            'skeleton': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.ClassInstance']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'djsopnet.assembly': {
            'Meta': {'object_name': 'Assembly'},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'equivalence': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.AssemblyEquivalence']", 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'djsopnet.assemblyequivalence': {
            'Meta': {'object_name': 'AssemblyEquivalence'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'skeleton': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.ClassInstance']"})
        },
        u'djsopnet.block': {
            'Meta': {'unique_together': "(('stack', 'coordinate_x', 'coordinate_y', 'coordinate_z'),)", 'object_name': 'Block'},
            'coordinate_x': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'coordinate_y': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'coordinate_z': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'segments_flag': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slices_flag': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'stack': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Stack']"})
        },
        u'djsopnet.blockconflictrelation': {
            'Meta': {'unique_together': "(('block', 'slice_conflict'),)", 'object_name': 'BlockConflictRelation'},
            'block': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Block']"}),
            'slice_conflict': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.SliceConflict']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'djsopnet.blockconstraintrelation': {
            'Meta': {'object_name': 'BlockConstraintRelation'},
            'block': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Block']"}),
            'constraint': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Constraint']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'djsopnet.blockinfo': {
            'Meta': {'object_name': 'BlockInfo'},
            'block_dim_x': ('django.db.models.fields.IntegerField', [], {'default': '256'}),
            'block_dim_y': ('django.db.models.fields.IntegerField', [], {'default': '256'}),
            'block_dim_z': ('django.db.models.fields.IntegerField', [], {'default': '16'}),
            'core_dim_x': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'core_dim_y': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'core_dim_z': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_x': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_y': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_z': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'stack': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['catmaid.Stack']", 'unique': 'True'})
        },
        u'djsopnet.conflictclique': {
            'Meta': {'object_name': 'ConflictClique'},
            'edges': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['djsopnet.SliceConflict']", 'db_table': "'djsopnet_conflictcliqueedge'", 'symmetrical': 'False'}),
            u'id': ('django.db.models.fields.BigIntegerField', [], {'primary_key': 'True'}),
            'maximal_clique': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        u'djsopnet.constraint': {
            'Meta': {'object_name': 'Constraint'},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'relation': ('djsopnet.fields.ConstraintRelationEnumField', [], {'default': "'Equal'"}),
            'skeleton': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': u"orm['catmaid.ClassInstance']", 'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'value': ('django.db.models.fields.FloatField', [], {'default': '1.0'})
        },
        u'djsopnet.constraintsegmentrelation': {
            'Meta': {'object_name': 'ConstraintSegmentRelation'},
            'coefficient': ('django.db.models.fields.FloatField', [], {'default': '1.0'}),
            'constraint': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Constraint']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'segment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Segment']"})
        },
        u'djsopnet.core': {
            'Meta': {'unique_together': "(('stack', 'coordinate_x', 'coordinate_y', 'coordinate_z'),)", 'object_name': 'Core'},
            'coordinate_x': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'coordinate_y': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'coordinate_z': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'solution_set_flag': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'stack': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Stack']"})
        },
        u'djsopnet.correction': {
            'Meta': {'unique_together': "(('constraint', 'mistake'),)", 'object_name': 'Correction'},
            'constraint': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Constraint']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mistake': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.SegmentSolution']"})
        },
        u'djsopnet.featureinfo': {
            'Meta': {'object_name': 'FeatureInfo'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name_ids': ('catmaid.fields.IntegerArrayField', [], {}),
            'size': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'stack': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['catmaid.Stack']", 'unique': 'True'}),
            'weights': ('catmaid.fields.DoubleArrayField', [], {})
        },
        u'djsopnet.featurename': {
            'Meta': {'object_name': 'FeatureName'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'djsopnet.segment': {
            'Meta': {'object_name': 'Segment'},
            'ctr_x': ('django.db.models.fields.FloatField', [], {}),
            'ctr_y': ('django.db.models.fields.FloatField', [], {}),
            'id': ('django.db.models.fields.BigIntegerField', [], {'primary_key': 'True'}),
            'max_x': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'max_y': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'min_x': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'min_y': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'section_inf': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'stack': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Stack']"}),
            'type': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'})
        },
        u'djsopnet.segmentblockrelation': {
            'Meta': {'unique_together': "(('block', 'segment'),)", 'object_name': 'SegmentBlockRelation'},
            'block': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Block']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'segment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Segment']"})
        },
        u'djsopnet.segmentfeatures': {
            'Meta': {'object_name': 'SegmentFeatures'},
            'features': ('catmaid.fields.DoubleArrayField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'segment': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['djsopnet.Segment']", 'unique': 'True'})
        },
        u'djsopnet.segmentslice': {
            'Meta': {'unique_together': "(('slice', 'segment'),)", 'object_name': 'SegmentSlice'},
            'direction': ('django.db.models.fields.BooleanField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'segment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Segment']"}),
            'slice': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Slice']"})
        },
        u'djsopnet.segmentsolution': {
            'Meta': {'unique_together': "(('solution', 'segment'),)", 'object_name': 'SegmentSolution'},
            'assembly': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Assembly']", 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'segment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Segment']"}),
            'solution': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Solution']"})
        },
        u'djsopnet.slice': {
            'Meta': {'object_name': 'Slice'},
            'ctr_x': ('django.db.models.fields.FloatField', [], {}),
            'ctr_y': ('django.db.models.fields.FloatField', [], {}),
            'id': ('django.db.models.fields.BigIntegerField', [], {'primary_key': 'True'}),
            'max_x': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'max_y': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'min_x': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'min_y': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'section': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'shape_x': ('catmaid.fields.IntegerArrayField', [], {'null': 'True'}),
            'shape_y': ('catmaid.fields.IntegerArrayField', [], {'null': 'True'}),
            'size': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'stack': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Stack']"}),
            'value': ('django.db.models.fields.FloatField', [], {})
        },
        u'djsopnet.sliceblockrelation': {
            'Meta': {'unique_together': "(('block', 'slice'),)", 'object_name': 'SliceBlockRelation'},
            'block': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Block']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slice': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Slice']"})
        },
        u'djsopnet.sliceconflict': {
            'Meta': {'unique_together': "(('slice_a', 'slice_b'),)", 'object_name': 'SliceConflict'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slice_a': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'conflicts_as_a'", 'to': u"orm['djsopnet.Slice']"}),
            'slice_b': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'conflicts_as_b'", 'to': u"orm['djsopnet.Slice']"})
        },
        u'djsopnet.solution': {
            'Meta': {'object_name': 'Solution'},
            'core': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Core']"}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'djsopnet.solutionprecedence': {
            'Meta': {'object_name': 'SolutionPrecedence'},
            'core': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Core']", 'unique': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'solution': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['djsopnet.Solution']", 'unique': 'True'})
        },
        u'djsopnet.treenodeslice': {
            'Meta': {'object_name': 'TreenodeSlice'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slice': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Slice']"}),
            'treenode': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Treenode']"})
        }
    }

    complete_apps = ['djsopnet']