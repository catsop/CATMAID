# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from djsopnet.models import SegmentationStack


class Migration(SchemaMigration):
    fks = {
        'slice_block_relation': {
            'slice_id': ('slice', 'id'),
            'block_id': ('block', 'id')
        },
        'treenode_slice': {
            'treenode_id': ('treenode', 'id'),
            'slice_id': ('slice', 'id')
        },
        'slice_conflict': {
            'slice_a_id': ('slice', 'id'),
            'slice_b_id': ('slice', 'id')
        },
        'conflict_clique_edge': {
            'conflict_clique_id': ('conflict_clique', 'id'),
            'slice_conflict_id': ('slice_conflict', 'id')
        },
        'block_conflict_relation': {
            'slice_conflict_id': ('slice_conflict', 'id'),
            'block_id': ('block', 'id')
        },
        'segment_slice': {
            'slice_id': ('slice', 'id'),
            'segment_id': ('segment', 'id')
        },
        'segment_features': {
            'segment_id': ('segment', 'id')
        },
        'segment_block_relation': {
            'segment_id': ('segment', 'id'),
            'block_id': ('block', 'id')
        },
        'solution': {
            'core_id': ('core', 'id')
        },
        'assembly_equivalence': {
            'skeleton_id': ('class_instance', 'id')
        },
        'assembly': {
            'equivalence_id': ('assembly_equivalence', 'id'),
            'solution_id': ('solution', 'id')
        },
        'assembly_relation': {
            'assembly_a_id': ('assembly', 'id'),
            'assembly_b_id': ('assembly', 'id')
        },
        'solution_precedence': {
            'core_id': ('core', 'id'),
            'solution_id': ('solution', 'id')
        },
        'segment_solution': {
            'segment_id': ('segment', 'id'),
            'solution_id': ('solution', 'id'),
            'assembly_id': ('assembly', 'id')
        },
        'solution_constraint': {
            'user_id': ('auth_user', 'id'),
            'skeleton_id': ('class_instance', 'id')
        },
        'block_constraint_relation': {
            'constraint_id': ('solution_constraint', 'id'),
            'block_id': ('block', 'id')
        },
        'constraint_segment_relation': {
            'constraint_id': ('solution_constraint', 'id'),
            'segment_id': ('segment', 'id')
        },
        'correction': {
            'constraint_id': ('solution_constraint', 'id'),
            'mistake_id': ('segment', 'id')
        }
    }

    def forwards(self, orm):
        for segstack_id in SegmentationStack.objects.all().values_list('id', flat=True):
            db.execute('''
                SET search_path TO segstack_%s,public
                ''' % segstack_id)
            for table, table_fks in self.fks.iteritems():
                for key_column, key_refs in table_fks.iteritems():
                    db.execute('''
                            ALTER TABLE segstack_%(segstack_id)s.%(table)s
                            DROP CONSTRAINT %(table)s_%(key_column)s_fkey;
                            ALTER TABLE segstack_%(segstack_id)s.%(table)s
                            ADD FOREIGN KEY (%(key_column)s) REFERENCES %(fk_table)s(%(fk_column)s)
                            DEFERRABLE INITIALLY IMMEDIATE;
                            ''' % {'segstack_id': segstack_id,
                                    'table': table,
                                    'key_column': key_column,
                                    'fk_table': key_refs[0],
                                    'fk_column': key_refs[1]})
            db.execute('RESET search_path')

    def backwards(self, orm):
        for segstack_id in SegmentationStack.objects.all().values_list('id', flat=True):
            db.execute('''
                SET search_path TO segstack_%s,public
                ''' % segstack_id)
            for table, table_fks in self.fks.iteritems():
                for key_column, key_refs in table_fks.iteritems():
                    db.execute('''
                            ALTER TABLE segstack_%(segstack_id)s.%(table)s
                            DROP CONSTRAINT %(table)s_%(key_column)s_fkey;
                            ALTER TABLE segstack_%(segstack_id)s.%(table)s
                            ADD FOREIGN KEY (%(key_column)s) REFERENCES %(fk_table)s(%(fk_column)s);
                            ''' % {'segstack_id': segstack_id,
                                    'table': table,
                                    'key_column': key_column,
                                    'fk_table': key_refs[0],
                                    'fk_column': key_refs[1]})
            db.execute('RESET search_path')

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
            'configuration': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'block_info'", 'unique': 'True', 'primary_key': 'True', 'to': u"orm['djsopnet.SegmentationConfiguration']"}),
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