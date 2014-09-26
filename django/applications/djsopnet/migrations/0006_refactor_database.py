# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'SegmentCost'
        db.delete_table(u'djsopnet_segmentcost')

        # Deleting model 'SliceConflictRelation'
        db.delete_table(u'djsopnet_sliceconflictrelation')

        # Deleting model 'FeatureNameInfo'
        db.delete_table(u'djsopnet_featurenameinfo')

        # Adding model 'FeatureInfo'
        db.create_table(u'djsopnet_featureinfo', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('stack', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['catmaid.Stack'], unique=True)),
            ('size', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('name_ids', self.gf('catmaid.fields.IntegerArrayField')()),
            ('weights', self.gf('catmaid.fields.DoubleArrayField')()),
        ))
        db.send_create_signal(u'djsopnet', ['FeatureInfo'])

        # Deleting field 'Block.creation_time'
        db.delete_column(u'djsopnet_block', 'creation_time')

        # Deleting field 'Block.edition_time'
        db.delete_column(u'djsopnet_block', 'edition_time')

        # Deleting field 'Block.project'
        db.delete_column(u'djsopnet_block', 'project_id')

        # Deleting field 'Block.user'
        db.delete_column(u'djsopnet_block', 'user_id')

        # Clear sliceblockrelation table
        db.clear_table(u'djsopnet_sliceblockrelation')

        # Deleting field 'SliceBlockRelation.project'
        db.delete_column(u'djsopnet_sliceblockrelation', 'project_id')

        # Deleting field 'SliceBlockRelation.edition_time'
        db.delete_column(u'djsopnet_sliceblockrelation', 'edition_time')

        # Deleting field 'SliceBlockRelation.creation_time'
        db.delete_column(u'djsopnet_sliceblockrelation', 'creation_time')

        # Deleting field 'SliceBlockRelation.user'
        db.delete_column(u'djsopnet_sliceblockrelation', 'user_id')

        # Adding unique constraint on 'SliceBlockRelation', fields ['block', 'slice']
        db.create_unique(u'djsopnet_sliceblockrelation', ['block_id', 'slice_id'])

        # Clear segmentfeatures table
        db.clear_table(u'djsopnet_segmentfeatures')

        # Deleting field 'SegmentFeatures.project'
        db.delete_column(u'djsopnet_segmentfeatures', 'project_id')

        # Deleting field 'SegmentFeatures.creation_time'
        db.delete_column(u'djsopnet_segmentfeatures', 'creation_time')

        # Deleting field 'SegmentFeatures.edition_time'
        db.delete_column(u'djsopnet_segmentfeatures', 'edition_time')

        # Deleting field 'SegmentFeatures.user'
        db.delete_column(u'djsopnet_segmentfeatures', 'user_id')


        # Changing field 'SegmentFeatures.features'
        db.alter_column(u'djsopnet_segmentfeatures', 'features', self.gf('catmaid.fields.DoubleArrayField')())
        # Deleting field 'BlockInfo.project'
        db.delete_column(u'djsopnet_blockinfo', 'project_id')

        # Deleting field 'BlockInfo.edition_time'
        db.delete_column(u'djsopnet_blockinfo', 'edition_time')

        # Deleting field 'BlockInfo.creation_time'
        db.delete_column(u'djsopnet_blockinfo', 'creation_time')

        # Deleting field 'BlockInfo.user'
        db.delete_column(u'djsopnet_blockinfo', 'user_id')

        # Clear blockconflictrelation table
        db.clear_table(u'djsopnet_blockconflictrelation')

        # Deleting field 'BlockConflictRelation.project'
        db.delete_column(u'djsopnet_blockconflictrelation', 'project_id')

        # Deleting field 'BlockConflictRelation.edition_time'
        db.delete_column(u'djsopnet_blockconflictrelation', 'edition_time')

        # Deleting field 'BlockConflictRelation.creation_time'
        db.delete_column(u'djsopnet_blockconflictrelation', 'creation_time')

        # Deleting field 'BlockConflictRelation.user'
        db.delete_column(u'djsopnet_blockconflictrelation', 'user_id')

        # Adding unique constraint on 'BlockConflictRelation', fields ['block', 'conflict']
        db.create_unique(u'djsopnet_blockconflictrelation', ['block_id', 'conflict_id'])

        # Clear segmentblockrelation table
        db.clear_table(u'djsopnet_segmentblockrelation')

        # Deleting field 'SegmentBlockRelation.project'
        db.delete_column(u'djsopnet_segmentblockrelation', 'project_id')

        # Deleting field 'SegmentBlockRelation.edition_time'
        db.delete_column(u'djsopnet_segmentblockrelation', 'edition_time')

        # Deleting field 'SegmentBlockRelation.creation_time'
        db.delete_column(u'djsopnet_segmentblockrelation', 'creation_time')

        # Deleting field 'SegmentBlockRelation.user'
        db.delete_column(u'djsopnet_segmentblockrelation', 'user_id')

        # Adding unique constraint on 'SegmentBlockRelation', fields ['block', 'segment']
        db.create_unique(u'djsopnet_segmentblockrelation', ['block_id', 'segment_id'])

        # Clear segmentsolution table
        db.clear_table(u'djsopnet_segmentsolution')

        # Deleting field 'SegmentSolution.project'
        db.delete_column(u'djsopnet_segmentsolution', 'project_id')

        # Deleting field 'SegmentSolution.user'
        db.delete_column(u'djsopnet_segmentsolution', 'user_id')

        # Deleting field 'SegmentSolution.creation_time'
        db.delete_column(u'djsopnet_segmentsolution', 'creation_time')

        # Deleting field 'SegmentSolution.edition_time'
        db.delete_column(u'djsopnet_segmentsolution', 'edition_time')

        # Adding unique constraint on 'SegmentSolution', fields ['core', 'segment']
        db.create_unique(u'djsopnet_segmentsolution', ['core_id', 'segment_id'])

        # Clear segment table
        db.clear_table(u'djsopnet_segment')

        # Deleting field 'Segment.slice_a_hash'
        db.delete_column(u'djsopnet_segment', 'slice_a_hash')

        # Deleting field 'Segment.slice_c_hash'
        db.delete_column(u'djsopnet_segment', 'slice_c_hash')

        # Deleting field 'Segment.creation_time'
        db.delete_column(u'djsopnet_segment', 'creation_time')

        # Deleting field 'Segment.edition_time'
        db.delete_column(u'djsopnet_segment', 'edition_time')

        # Deleting field 'Segment.project'
        db.delete_column(u'djsopnet_segment', 'project_id')

        # Deleting field 'Segment.slice_b_hash'
        db.delete_column(u'djsopnet_segment', 'slice_b_hash')

        # Deleting field 'Segment.user'
        db.delete_column(u'djsopnet_segment', 'user_id')

        # Deleting field 'Segment.hash_value'
        db.delete_column(u'djsopnet_segment', 'hash_value')

        # Adding field 'Segment.id'
        db.add_column(u'djsopnet_segment', 'id',
                      self.gf('django.db.models.fields.BigIntegerField')(primary_key=True),
                      keep_default=False)

        # Adding field 'Segment.slice_a'
        db.add_column(u'djsopnet_segment', 'slice_a',
                      self.gf('django.db.models.fields.related.ForeignKey')(related_name='segments_as_a', to=orm['djsopnet.Slice']),
                      keep_default=False)

        # Adding field 'Segment.slice_b'
        db.add_column(u'djsopnet_segment', 'slice_b',
                      self.gf('django.db.models.fields.related.ForeignKey')(related_name='segments_as_b', null=True, to=orm['djsopnet.Slice']),
                      keep_default=False)

        # Adding field 'Segment.slice_c'
        db.add_column(u'djsopnet_segment', 'slice_c',
                      self.gf('django.db.models.fields.related.ForeignKey')(related_name='segments_as_c', null=True, to=orm['djsopnet.Slice']),
                      keep_default=False)

        # Clear sliceconflictset table
        db.clear_table(u'djsopnet_sliceconflictset')

        # Adding field 'SliceConflictSet.slice_a'
        db.add_column(u'djsopnet_sliceconflictset', 'slice_a',
                      self.gf('django.db.models.fields.related.ForeignKey')(related_name='conflicts_as_a', to=orm['djsopnet.Slice']),
                      keep_default=False)

        # Adding field 'SliceConflictSet.slice_b'
        db.add_column(u'djsopnet_sliceconflictset', 'slice_b',
                      self.gf('django.db.models.fields.related.ForeignKey')(related_name='conflicts_as_b', to=orm['djsopnet.Slice']),
                      keep_default=False)

        # Adding unique constraint on 'SliceConflictSet', fields ['slice_a', 'slice_b']
        db.create_unique(u'djsopnet_sliceconflictset', ['slice_a_id', 'slice_b_id'])

        # Deleting field 'Core.creation_time'
        db.delete_column(u'djsopnet_core', 'creation_time')

        # Deleting field 'Core.user'
        db.delete_column(u'djsopnet_core', 'user_id')

        # Deleting field 'Core.edition_time'
        db.delete_column(u'djsopnet_core', 'edition_time')

        # Deleting field 'Core.project'
        db.delete_column(u'djsopnet_core', 'project_id')

        # Clear slice table
        db.clear_table(u'djsopnet_slice')

        # Deleting field 'Slice.creation_time'
        db.delete_column(u'djsopnet_slice', 'creation_time')

        # Deleting field 'Slice.edition_time'
        db.delete_column(u'djsopnet_slice', 'edition_time')

        # Deleting field 'Slice.project'
        db.delete_column(u'djsopnet_slice', 'project_id')

        # Deleting field 'Slice.user'
        db.delete_column(u'djsopnet_slice', 'user_id')

        # Deleting field 'Slice.hash_value'
        db.delete_column(u'djsopnet_slice', 'hash_value')

        # Adding field 'Slice.id'
        db.add_column(u'djsopnet_slice', 'id',
                      self.gf('django.db.models.fields.BigIntegerField')(primary_key=True),
                      keep_default=False)


    def backwards(self, orm):
        raise RuntimeError("Cannot reverse this migration.")


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
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'djsopnet.assembly': {
            'Meta': {'object_name': 'Assembly'},
            'assembly_type': ('django.db.models.fields.CharField', [], {'max_length': '32', 'db_index': 'True'}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'djsopnet.block': {
            'Meta': {'object_name': 'Block'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_x': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'max_y': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'max_z': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'min_x': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'min_y': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'min_z': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'segments_flag': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slices_flag': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'solution_cost_flag': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'stack': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Stack']"})
        },
        u'djsopnet.blockconflictrelation': {
            'Meta': {'unique_together': "(('block', 'conflict'),)", 'object_name': 'BlockConflictRelation'},
            'block': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Block']"}),
            'conflict': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.SliceConflictSet']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'djsopnet.blockinfo': {
            'Meta': {'object_name': 'BlockInfo'},
            'bdepth': ('django.db.models.fields.IntegerField', [], {'default': '16'}),
            'bheight': ('django.db.models.fields.IntegerField', [], {'default': '256'}),
            'bwidth': ('django.db.models.fields.IntegerField', [], {'default': '256'}),
            'cdepth': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'cheight': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'cwidth': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_x': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_y': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_z': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'stack': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Stack']"})
        },
        u'djsopnet.core': {
            'Meta': {'object_name': 'Core'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_x': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'max_y': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'max_z': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'min_x': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'min_y': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'min_z': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'solution_set_flag': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'stack': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Stack']"})
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
            'assembly': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Assembly']", 'null': 'True'}),
            'ctr_x': ('django.db.models.fields.FloatField', [], {}),
            'ctr_y': ('django.db.models.fields.FloatField', [], {}),
            'direction': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'id': ('django.db.models.fields.BigIntegerField', [], {'primary_key': 'True'}),
            'max_x': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'max_y': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'min_x': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'min_y': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'section_inf': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'slice_a': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'segments_as_a'", 'to': u"orm['djsopnet.Slice']"}),
            'slice_b': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'segments_as_b'", 'null': 'True', 'to': u"orm['djsopnet.Slice']"}),
            'slice_c': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'segments_as_c'", 'null': 'True', 'to': u"orm['djsopnet.Slice']"}),
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
        u'djsopnet.segmentsolution': {
            'Meta': {'unique_together': "(('core', 'segment'),)", 'object_name': 'SegmentSolution'},
            'core': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Core']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'segment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Segment']"}),
            'solution': ('django.db.models.fields.BooleanField', [], {})
        },
        u'djsopnet.slice': {
            'Meta': {'object_name': 'Slice'},
            'assembly': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Assembly']", 'null': 'True'}),
            'ctr_x': ('django.db.models.fields.FloatField', [], {}),
            'ctr_y': ('django.db.models.fields.FloatField', [], {}),
            'id': ('django.db.models.fields.BigIntegerField', [], {'primary_key': 'True'}),
            'max_x': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'max_y': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'min_x': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'min_y': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'section': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'shape_x': ('catmaid.fields.IntegerArrayField', [], {}),
            'shape_y': ('catmaid.fields.IntegerArrayField', [], {}),
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
        u'djsopnet.sliceconflictset': {
            'Meta': {'unique_together': "(('slice_a', 'slice_b'),)", 'object_name': 'SliceConflictSet'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slice_a': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'conflicts_as_a'", 'to': u"orm['djsopnet.Slice']"}),
            'slice_b': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'conflicts_as_b'", 'to': u"orm['djsopnet.Slice']"})
        }
    }

    complete_apps = ['djsopnet']