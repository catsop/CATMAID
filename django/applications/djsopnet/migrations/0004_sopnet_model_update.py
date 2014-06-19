# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'SliceBlockRelation'
        db.create_table('djsopnet_sliceblockrelation', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['catmaid.Project'])),
            ('creation_time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('edition_time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('block', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.Block'])),
            ('slice', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.Slice'])),
        ))
        db.send_create_signal('djsopnet', ['SliceBlockRelation'])

        # Adding model 'SegmentCost'
        db.create_table('djsopnet_segmentcost', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['catmaid.Project'])),
            ('creation_time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('edition_time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('segment', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['djsopnet.Segment'], unique=True)),
            ('cost', self.gf('django.db.models.fields.FloatField')()),
        ))
        db.send_create_signal('djsopnet', ['SegmentCost'])

        # Adding model 'SegmentFeatures'
        db.create_table('djsopnet_segmentfeatures', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['catmaid.Project'])),
            ('creation_time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('edition_time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('segment', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['djsopnet.Segment'], unique=True)),
            ('features', self.gf('catmaid.fields.FloatArrayField')()),
        ))
        db.send_create_signal('djsopnet', ['SegmentFeatures'])

        # Adding model 'BlockConflictRelation'
        db.create_table('djsopnet_blockconflictrelation', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['catmaid.Project'])),
            ('creation_time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('edition_time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('block', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.Block'])),
            ('conflict', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.SliceConflictSet'])),
        ))
        db.send_create_signal('djsopnet', ['BlockConflictRelation'])

        # Adding model 'SegmentBlockRelation'
        db.create_table('djsopnet_segmentblockrelation', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['catmaid.Project'])),
            ('creation_time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('edition_time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('block', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.Block'])),
            ('segment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.Segment'])),
        ))
        db.send_create_signal('djsopnet', ['SegmentBlockRelation'])

        # Adding model 'FeatureName'
        db.create_table('djsopnet_featurename', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=32)),
        ))
        db.send_create_signal('djsopnet', ['FeatureName'])

        # Adding model 'SliceConflictRelation'
        db.create_table('djsopnet_sliceconflictrelation', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['catmaid.Project'])),
            ('creation_time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('edition_time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('slice', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.Slice'])),
            ('conflict', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.SliceConflictSet'])),
        ))
        db.send_create_signal('djsopnet', ['SliceConflictRelation'])

        # Adding model 'FeatureNameInfo'
        db.create_table('djsopnet_featurenameinfo', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['catmaid.Project'])),
            ('creation_time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('edition_time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('stack', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['catmaid.Stack'])),
            ('name_ids', self.gf('catmaid.fields.IntegerArrayField')()),
            ('size', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal('djsopnet', ['FeatureNameInfo'])

        # Adding model 'SegmentSolution'
        db.create_table('djsopnet_segmentsolution', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['catmaid.Project'])),
            ('creation_time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('edition_time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('core', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.Core'])),
            ('segment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.Segment'])),
            ('solution', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('djsopnet', ['SegmentSolution'])

        # Adding model 'SliceConflictSet'
        db.create_table('djsopnet_sliceconflictset', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('djsopnet', ['SliceConflictSet'])

        # Adding model 'Core'
        db.create_table('djsopnet_core', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['catmaid.Project'])),
            ('creation_time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('edition_time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('stack', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['catmaid.Stack'])),
            ('min_x', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('min_y', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('max_x', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('max_y', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('min_z', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('max_z', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('solution_set_flag', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('djsopnet', ['Core'])

        # Deleting field 'Segment.slice_a'
        db.delete_column('djsopnet_segment', 'slice_a_id')

        # Deleting field 'Segment.slice_c'
        db.delete_column('djsopnet_segment', 'slice_c_id')

        # Deleting field 'Segment.slice_b'
        db.delete_column('djsopnet_segment', 'slice_b_id')

        # Deleting field 'Segment.id'
        db.delete_column('djsopnet_segment', 'id')

        # Adding field 'Segment.slice_a_hash'
        db.add_column('djsopnet_segment', 'slice_a_hash',
                      self.gf('django.db.models.fields.CharField')(max_length=20, null=True, db_index=True),
                      keep_default=False)

        # Adding field 'Segment.slice_b_hash'
        db.add_column('djsopnet_segment', 'slice_b_hash',
                      self.gf('django.db.models.fields.CharField')(max_length=20, null=True, db_index=True),
                      keep_default=False)

        # Adding field 'Segment.slice_c_hash'
        db.add_column('djsopnet_segment', 'slice_c_hash',
                      self.gf('django.db.models.fields.CharField')(max_length=20, null=True, db_index=True),
                      keep_default=False)


        # Changing field 'Segment.hash_value'
        db.alter_column('djsopnet_segment', 'hash_value', self.gf('django.db.models.fields.CharField')(max_length=20, primary_key=True))
        # Removing index on 'Segment', fields ['hash_value']
        db.delete_index('djsopnet_segment', ['hash_value'])

        # Adding unique constraint on 'Segment', fields ['hash_value']
        db.create_unique('djsopnet_segment', ['hash_value'])

        # Deleting field 'Block.slices'
        db.delete_column('djsopnet_block', 'slices')

        # Deleting field 'Block.segments'
        db.delete_column('djsopnet_block', 'segments')

        # Adding field 'Block.solution_cost_flag'
        db.add_column('djsopnet_block', 'solution_cost_flag',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Deleting field 'BlockInfo.height'
        db.delete_column('djsopnet_blockinfo', 'height')

        # Deleting field 'BlockInfo.width'
        db.delete_column('djsopnet_blockinfo', 'width')

        # Deleting field 'BlockInfo.depth'
        db.delete_column('djsopnet_blockinfo', 'depth')

        # Adding field 'BlockInfo.bheight'
        db.add_column('djsopnet_blockinfo', 'bheight',
                      self.gf('django.db.models.fields.IntegerField')(default=256),
                      keep_default=False)

        # Adding field 'BlockInfo.bwidth'
        db.add_column('djsopnet_blockinfo', 'bwidth',
                      self.gf('django.db.models.fields.IntegerField')(default=256),
                      keep_default=False)

        # Adding field 'BlockInfo.bdepth'
        db.add_column('djsopnet_blockinfo', 'bdepth',
                      self.gf('django.db.models.fields.IntegerField')(default=16),
                      keep_default=False)

        # Adding field 'BlockInfo.cheight'
        db.add_column('djsopnet_blockinfo', 'cheight',
                      self.gf('django.db.models.fields.IntegerField')(default=1),
                      keep_default=False)

        # Adding field 'BlockInfo.cwidth'
        db.add_column('djsopnet_blockinfo', 'cwidth',
                      self.gf('django.db.models.fields.IntegerField')(default=1),
                      keep_default=False)

        # Adding field 'BlockInfo.cdepth'
        db.add_column('djsopnet_blockinfo', 'cdepth',
                      self.gf('django.db.models.fields.IntegerField')(default=1),
                      keep_default=False)

        # Deleting field 'Slice.parent'
        db.delete_column('djsopnet_slice', 'parent_id')

        # Deleting field 'Slice.id'
        db.delete_column('djsopnet_slice', 'id')


        # Changing field 'Slice.hash_value'
        db.alter_column('djsopnet_slice', 'hash_value', self.gf('django.db.models.fields.CharField')(max_length=20, primary_key=True))
        # Removing index on 'Slice', fields ['hash_value']
        db.delete_index('djsopnet_slice', ['hash_value'])

        # Adding unique constraint on 'Slice', fields ['hash_value']
        db.create_unique('djsopnet_slice', ['hash_value'])


    def backwards(self, orm):
        # Removing unique constraint on 'Slice', fields ['hash_value']
        db.delete_unique('djsopnet_slice', ['hash_value'])

        # Adding index on 'Slice', fields ['hash_value']
        db.create_index('djsopnet_slice', ['hash_value'])

        # Removing unique constraint on 'Segment', fields ['hash_value']
        db.delete_unique('djsopnet_segment', ['hash_value'])

        # Adding index on 'Segment', fields ['hash_value']
        db.create_index('djsopnet_segment', ['hash_value'])

        # Deleting model 'SliceBlockRelation'
        db.delete_table('djsopnet_sliceblockrelation')

        # Deleting model 'SegmentCost'
        db.delete_table('djsopnet_segmentcost')

        # Deleting model 'SegmentFeatures'
        db.delete_table('djsopnet_segmentfeatures')

        # Deleting model 'BlockConflictRelation'
        db.delete_table('djsopnet_blockconflictrelation')

        # Deleting model 'SegmentBlockRelation'
        db.delete_table('djsopnet_segmentblockrelation')

        # Deleting model 'FeatureName'
        db.delete_table('djsopnet_featurename')

        # Deleting model 'SliceConflictRelation'
        db.delete_table('djsopnet_sliceconflictrelation')

        # Deleting model 'FeatureNameInfo'
        db.delete_table('djsopnet_featurenameinfo')

        # Deleting model 'SegmentSolution'
        db.delete_table('djsopnet_segmentsolution')

        # Deleting model 'SliceConflictSet'
        db.delete_table('djsopnet_sliceconflictset')

        # Deleting model 'Core'
        db.delete_table('djsopnet_core')


        # User chose to not deal with backwards NULL issues for 'Segment.slice_a'
        raise RuntimeError("Cannot reverse this migration. 'Segment.slice_a' and its values cannot be restored.")
        # Adding field 'Segment.slice_c'
        db.add_column('djsopnet_segment', 'slice_c',
                      self.gf('django.db.models.fields.related.ForeignKey')(related_name='slice_c', null=True, to=orm['djsopnet.Slice']),
                      keep_default=False)

        # Adding field 'Segment.slice_b'
        db.add_column('djsopnet_segment', 'slice_b',
                      self.gf('django.db.models.fields.related.ForeignKey')(related_name='slice_b', null=True, to=orm['djsopnet.Slice']),
                      keep_default=False)


        # User chose to not deal with backwards NULL issues for 'Segment.id'
        raise RuntimeError("Cannot reverse this migration. 'Segment.id' and its values cannot be restored.")
        # Deleting field 'Segment.slice_a_hash'
        db.delete_column('djsopnet_segment', 'slice_a_hash')

        # Deleting field 'Segment.slice_b_hash'
        db.delete_column('djsopnet_segment', 'slice_b_hash')

        # Deleting field 'Segment.slice_c_hash'
        db.delete_column('djsopnet_segment', 'slice_c_hash')


        # Changing field 'Segment.hash_value'
        db.alter_column('djsopnet_segment', 'hash_value', self.gf('django.db.models.fields.IntegerField')())

        # User chose to not deal with backwards NULL issues for 'Block.slices'
        raise RuntimeError("Cannot reverse this migration. 'Block.slices' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'Block.segments'
        raise RuntimeError("Cannot reverse this migration. 'Block.segments' and its values cannot be restored.")
        # Deleting field 'Block.solution_cost_flag'
        db.delete_column('djsopnet_block', 'solution_cost_flag')


        # User chose to not deal with backwards NULL issues for 'BlockInfo.height'
        raise RuntimeError("Cannot reverse this migration. 'BlockInfo.height' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'BlockInfo.width'
        raise RuntimeError("Cannot reverse this migration. 'BlockInfo.width' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'BlockInfo.depth'
        raise RuntimeError("Cannot reverse this migration. 'BlockInfo.depth' and its values cannot be restored.")
        # Deleting field 'BlockInfo.bheight'
        db.delete_column('djsopnet_blockinfo', 'bheight')

        # Deleting field 'BlockInfo.bwidth'
        db.delete_column('djsopnet_blockinfo', 'bwidth')

        # Deleting field 'BlockInfo.bdepth'
        db.delete_column('djsopnet_blockinfo', 'bdepth')

        # Deleting field 'BlockInfo.cheight'
        db.delete_column('djsopnet_blockinfo', 'cheight')

        # Deleting field 'BlockInfo.cwidth'
        db.delete_column('djsopnet_blockinfo', 'cwidth')

        # Deleting field 'BlockInfo.cdepth'
        db.delete_column('djsopnet_blockinfo', 'cdepth')

        # Adding field 'Slice.parent'
        db.add_column('djsopnet_slice', 'parent',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djsopnet.Slice'], null=True),
                      keep_default=False)


        # User chose to not deal with backwards NULL issues for 'Slice.id'
        raise RuntimeError("Cannot reverse this migration. 'Slice.id' and its values cannot be restored.")

        # Changing field 'Slice.hash_value'
        db.alter_column('djsopnet_slice', 'hash_value', self.gf('django.db.models.fields.IntegerField')())

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'catmaid.project': {
            'Meta': {'object_name': 'Project', 'db_table': "'project'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'stacks': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['catmaid.Stack']", 'through': "orm['catmaid.ProjectStack']", 'symmetrical': 'False'}),
            'title': ('django.db.models.fields.TextField', [], {})
        },
        'catmaid.projectstack': {
            'Meta': {'object_name': 'ProjectStack', 'db_table': "'project_stack'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'orientation': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['catmaid.Project']"}),
            'stack': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['catmaid.Stack']"}),
            'translation': ('catmaid.fields.Double3DField', [], {'default': '(0, 0, 0)'})
        },
        'catmaid.stack': {
            'Meta': {'object_name': 'Stack', 'db_table': "'stack'"},
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'dimension': ('catmaid.fields.Integer3DField', [], {}),
            'file_extension': ('django.db.models.fields.TextField', [], {'default': "'jpg'", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
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
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'djsopnet.assembly': {
            'Meta': {'object_name': 'Assembly'},
            'assembly_type': ('django.db.models.fields.CharField', [], {'max_length': '32', 'db_index': 'True'}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'djsopnet.block': {
            'Meta': {'object_name': 'Block'},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_x': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'max_y': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'max_z': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'min_x': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'min_y': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'min_z': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['catmaid.Project']"}),
            'segments_flag': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slices_flag': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'solution_cost_flag': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'stack': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['catmaid.Stack']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'djsopnet.blockconflictrelation': {
            'Meta': {'object_name': 'BlockConflictRelation'},
            'block': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djsopnet.Block']"}),
            'conflict': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djsopnet.SliceConflictSet']"}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['catmaid.Project']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'djsopnet.blockinfo': {
            'Meta': {'object_name': 'BlockInfo'},
            'bdepth': ('django.db.models.fields.IntegerField', [], {'default': '16'}),
            'bheight': ('django.db.models.fields.IntegerField', [], {'default': '256'}),
            'bwidth': ('django.db.models.fields.IntegerField', [], {'default': '256'}),
            'cdepth': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'cheight': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'cwidth': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_x': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_y': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_z': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['catmaid.Project']"}),
            'stack': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['catmaid.Stack']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'djsopnet.core': {
            'Meta': {'object_name': 'Core'},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_x': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'max_y': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'max_z': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'min_x': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'min_y': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'min_z': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['catmaid.Project']"}),
            'solution_set_flag': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'stack': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['catmaid.Stack']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'djsopnet.featurename': {
            'Meta': {'object_name': 'FeatureName'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'djsopnet.featurenameinfo': {
            'Meta': {'object_name': 'FeatureNameInfo'},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name_ids': ('catmaid.fields.IntegerArrayField', [], {}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['catmaid.Project']"}),
            'size': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'stack': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['catmaid.Stack']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'djsopnet.segment': {
            'Meta': {'object_name': 'Segment'},
            'assembly': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djsopnet.Assembly']", 'null': 'True'}),
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
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['catmaid.Project']"}),
            'section_inf': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'slice_a_hash': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'db_index': 'True'}),
            'slice_b_hash': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'db_index': 'True'}),
            'slice_c_hash': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'db_index': 'True'}),
            'stack': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['catmaid.Stack']"}),
            'type': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'djsopnet.segmentblockrelation': {
            'Meta': {'object_name': 'SegmentBlockRelation'},
            'block': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djsopnet.Block']"}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['catmaid.Project']"}),
            'segment': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djsopnet.Segment']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'djsopnet.segmentcost': {
            'Meta': {'object_name': 'SegmentCost'},
            'cost': ('django.db.models.fields.FloatField', [], {}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['catmaid.Project']"}),
            'segment': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['djsopnet.Segment']", 'unique': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'djsopnet.segmentfeatures': {
            'Meta': {'object_name': 'SegmentFeatures'},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'features': ('catmaid.fields.FloatArrayField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['catmaid.Project']"}),
            'segment': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['djsopnet.Segment']", 'unique': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'djsopnet.segmentsolution': {
            'Meta': {'object_name': 'SegmentSolution'},
            'core': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djsopnet.Core']"}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['catmaid.Project']"}),
            'segment': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djsopnet.Segment']"}),
            'solution': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'djsopnet.slice': {
            'Meta': {'object_name': 'Slice'},
            'assembly': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djsopnet.Assembly']", 'null': 'True'}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'ctr_x': ('django.db.models.fields.FloatField', [], {}),
            'ctr_y': ('django.db.models.fields.FloatField', [], {}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'hash_value': ('django.db.models.fields.CharField', [], {'max_length': '20', 'primary_key': 'True'}),
            'max_x': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'max_y': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'min_x': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'min_y': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['catmaid.Project']"}),
            'section': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'shape_x': ('catmaid.fields.IntegerArrayField', [], {}),
            'shape_y': ('catmaid.fields.IntegerArrayField', [], {}),
            'size': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'stack': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['catmaid.Stack']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'value': ('django.db.models.fields.FloatField', [], {})
        },
        'djsopnet.sliceblockrelation': {
            'Meta': {'object_name': 'SliceBlockRelation'},
            'block': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djsopnet.Block']"}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['catmaid.Project']"}),
            'slice': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djsopnet.Slice']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'djsopnet.sliceconflictrelation': {
            'Meta': {'object_name': 'SliceConflictRelation'},
            'conflict': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djsopnet.SliceConflictSet']"}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'edition_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['catmaid.Project']"}),
            'slice': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djsopnet.Slice']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'djsopnet.sliceconflictset': {
            'Meta': {'object_name': 'SliceConflictSet'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'taggit_taggeditem_items'", 'to': "orm['taggit.Tag']"})
        }
    }

    complete_apps = ['djsopnet']