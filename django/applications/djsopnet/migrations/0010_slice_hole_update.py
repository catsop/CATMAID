# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'SliceHole.min_x'
        db.add_column(u'djsopnet_slicehole', 'min_x',
                      self.gf('django.db.models.fields.FloatField')(default=0, db_index=True),
                      keep_default=False)

        # Adding field 'SliceHole.min_y'
        db.add_column(u'djsopnet_slicehole', 'min_y',
                      self.gf('django.db.models.fields.FloatField')(default=0, db_index=True),
                      keep_default=False)

        # Adding field 'SliceHole.max_x'
        db.add_column(u'djsopnet_slicehole', 'max_x',
                      self.gf('django.db.models.fields.FloatField')(default=0, db_index=True),
                      keep_default=False)

        # Adding field 'SliceHole.max_y'
        db.add_column(u'djsopnet_slicehole', 'max_y',
                      self.gf('django.db.models.fields.FloatField')(default=0, db_index=True),
                      keep_default=False)

        # Adding field 'SliceHole.section'
        db.add_column(u'djsopnet_slicehole', 'section',
                      self.gf('django.db.models.fields.IntegerField')(default=-1, db_index=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'SliceHole.min_x'
        db.delete_column(u'djsopnet_slicehole', 'min_x')

        # Deleting field 'SliceHole.min_y'
        db.delete_column(u'djsopnet_slicehole', 'min_y')

        # Deleting field 'SliceHole.max_x'
        db.delete_column(u'djsopnet_slicehole', 'max_x')

        # Deleting field 'SliceHole.max_y'
        db.delete_column(u'djsopnet_slicehole', 'max_y')

        # Deleting field 'SliceHole.section'
        db.delete_column(u'djsopnet_slicehole', 'section')


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
        u'catmaid.project': {
            'Meta': {'object_name': 'Project', 'db_table': "'project'"},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
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
            'stack': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Stack']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'djsopnet.block': {
            'Meta': {'object_name': 'Block'},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_x': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'max_y': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'max_z': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'min_x': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'min_y': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'min_z': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'segments_flag': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slices_flag': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'solution_cost_flag': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'stack': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Stack']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'djsopnet.blockconflictrelation': {
            'Meta': {'object_name': 'BlockConflictRelation'},
            'block': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Block']"}),
            'conflict': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.SliceConflictSet']"}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'djsopnet.blockinfo': {
            'Meta': {'object_name': 'BlockInfo'},
            'bdepth': ('django.db.models.fields.IntegerField', [], {'default': '16'}),
            'bheight': ('django.db.models.fields.IntegerField', [], {'default': '256'}),
            'bwidth': ('django.db.models.fields.IntegerField', [], {'default': '256'}),
            'cdepth': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'cheight': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'cwidth': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_x': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_y': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_z': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'stack': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Stack']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'djsopnet.core': {
            'Meta': {'object_name': 'Core'},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_x': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'max_y': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'max_z': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'min_x': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'min_y': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'min_z': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'solution_set_flag': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'stack': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Stack']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'djsopnet.featurename': {
            'Meta': {'object_name': 'FeatureName'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'djsopnet.featurenameinfo': {
            'Meta': {'object_name': 'FeatureNameInfo'},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name_ids': ('catmaid.fields.IntegerArrayField', [], {}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'size': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'stack': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Stack']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'djsopnet.segment': {
            'Meta': {'object_name': 'Segment'},
            'assembly': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Assembly']", 'null': 'True'}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'ctr_x': ('django.db.models.fields.FloatField', [], {}),
            'ctr_y': ('django.db.models.fields.FloatField', [], {}),
            'direction': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'hash_value': ('django.db.models.fields.CharField', [], {'max_length': '20', 'primary_key': 'True'}),
            'max_x': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'max_y': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'min_x': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'min_y': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'section_inf': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'slice_a_hash': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'db_index': 'True'}),
            'slice_b_hash': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'db_index': 'True'}),
            'slice_c_hash': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'db_index': 'True'}),
            'stack': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Stack']"}),
            'type': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'djsopnet.segmentblockrelation': {
            'Meta': {'object_name': 'SegmentBlockRelation'},
            'block': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Block']"}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'segment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Segment']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'djsopnet.segmentcost': {
            'Meta': {'object_name': 'SegmentCost'},
            'cost': ('django.db.models.fields.FloatField', [], {}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'segment': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['djsopnet.Segment']", 'unique': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'djsopnet.segmentfeatures': {
            'Meta': {'object_name': 'SegmentFeatures'},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'features': ('catmaid.fields.FloatArrayField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'segment': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['djsopnet.Segment']", 'unique': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'djsopnet.segmentsolution': {
            'Meta': {'object_name': 'SegmentSolution'},
            'core': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Core']"}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'segment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Segment']"}),
            'solution': ('django.db.models.fields.BooleanField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'djsopnet.slice': {
            'Meta': {'object_name': 'Slice'},
            'assembly': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Assembly']", 'null': 'True'}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'ctr_x': ('django.db.models.fields.FloatField', [], {}),
            'ctr_y': ('django.db.models.fields.FloatField', [], {}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'hash_value': ('django.db.models.fields.CharField', [], {'max_length': '20', 'primary_key': 'True'}),
            'max_x': ('django.db.models.fields.FloatField', [], {'db_index': 'True'}),
            'max_y': ('django.db.models.fields.FloatField', [], {'db_index': 'True'}),
            'min_x': ('django.db.models.fields.FloatField', [], {'db_index': 'True'}),
            'min_y': ('django.db.models.fields.FloatField', [], {'db_index': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'section': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'shape_x': ('catmaid.fields.FloatArrayField', [], {}),
            'shape_y': ('catmaid.fields.FloatArrayField', [], {}),
            'size': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'stack': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Stack']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'value': ('django.db.models.fields.FloatField', [], {})
        },
        u'djsopnet.sliceblockrelation': {
            'Meta': {'object_name': 'SliceBlockRelation'},
            'block': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Block']"}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'slice': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Slice']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'djsopnet.sliceconflictrelation': {
            'Meta': {'object_name': 'SliceConflictRelation'},
            'conflict': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.SliceConflictSet']"}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['catmaid.Project']"}),
            'slice': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Slice']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'djsopnet.sliceconflictset': {
            'Meta': {'object_name': 'SliceConflictSet'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'djsopnet.slicehole': {
            'Meta': {'object_name': 'SliceHole'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_x': ('django.db.models.fields.FloatField', [], {'db_index': 'True'}),
            'max_y': ('django.db.models.fields.FloatField', [], {'db_index': 'True'}),
            'min_x': ('django.db.models.fields.FloatField', [], {'db_index': 'True'}),
            'min_y': ('django.db.models.fields.FloatField', [], {'db_index': 'True'}),
            'section': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'shape_x': ('catmaid.fields.FloatArrayField', [], {}),
            'shape_y': ('catmaid.fields.FloatArrayField', [], {})
        },
        u'djsopnet.sliceholerelation': {
            'Meta': {'object_name': 'SliceHoleRelation'},
            'external': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Slice']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'internal': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.SliceHole']"})
        },
        u'djsopnet.viewproperties': {
            'Meta': {'object_name': 'ViewProperties'},
            'assembly': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djsopnet.Assembly']"}),
            'color': ('django.db.models.fields.TextField', [], {'default': "'#0000ff'"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'opacity': ('django.db.models.fields.FloatField', [], {'default': '0.5'})
        }
    }

    complete_apps = ['djsopnet']