# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from djsopnet.models import SegmentationStack


class Migration(SchemaMigration):

    def forwards(self, orm):
        db.execute('''
                SET search_path TO segstack_template,public;

                TRUNCATE TABLE segstack_template.assembly CASCADE;

                ALTER TABLE segstack_template.assembly
                  DROP COLUMN IF EXISTS solution_id,
                  ADD COLUMN core_id integer NOT NULL REFERENCES core(id) DEFERRABLE INITIALLY IMMEDIATE,
                  ADD COLUMN hash bigint NOT NULL,
                  ADD UNIQUE (core_id, hash);

                DROP TABLE segstack_template.segment_solution CASCADE;

                CREATE TABLE segstack_template.solution_assembly (
                  solution_id integer NOT NULL REFERENCES solution(id) DEFERRABLE INITIALLY IMMEDIATE,
                  assembly_id integer NOT NULL REFERENCES assembly(id) DEFERRABLE INITIALLY IMMEDIATE,
                  PRIMARY KEY (solution_id, assembly_id),
                  CHECK (false) NO INHERIT -- prevent any rows populating this table
                ) WITH (
                  OIDS=FALSE
                );

                CREATE TABLE segstack_template.assembly_segment (
                  assembly_id integer NOT NULL REFERENCES assembly(id) DEFERRABLE INITIALLY IMMEDIATE,
                  segment_id bigint NOT NULL REFERENCES segment(id) DEFERRABLE INITIALLY IMMEDIATE,
                  PRIMARY KEY (assembly_id, segment_id),
                  CHECK (false) NO INHERIT -- prevent any rows populating this table
                ) WITH (
                  OIDS=FALSE
                );

                RESET search_path;
                ''')

        for segstack_id in SegmentationStack.objects.all().values_list('id', flat=True):
            db.execute('''
                    SET search_path TO segstack_%s,public;

                    TRUNCATE TABLE assembly CASCADE;

                    ALTER TABLE assembly
                      DROP COLUMN IF EXISTS solution_id,
                      ADD FOREIGN KEY (core_id) REFERENCES core(id) DEFERRABLE INITIALLY IMMEDIATE,
                      ADD UNIQUE (core_id, hash);

                    CREATE TABLE solution_assembly
                        (LIKE segstack_template.solution_assembly INCLUDING INDEXES,
                          FOREIGN KEY (solution_id) REFERENCES solution(id) DEFERRABLE INITIALLY IMMEDIATE,
                          FOREIGN KEY (assembly_id) REFERENCES assembly(id) DEFERRABLE INITIALLY IMMEDIATE)
                        INHERITS (segstack_template.solution_assembly);

                    CREATE TABLE assembly_segment
                        (LIKE segstack_template.assembly_segment INCLUDING INDEXES,
                          FOREIGN KEY (assembly_id) REFERENCES assembly(id) DEFERRABLE INITIALLY IMMEDIATE,
                          FOREIGN KEY (segment_id) REFERENCES segment(id) DEFERRABLE INITIALLY IMMEDIATE)
                        INHERITS (segstack_template.assembly_segment);

                    RESET search_path;
                    ''' % segstack_id)

    def backwards(self, orm):
        db.execute('''
                SET search_path TO segstack_template,public;

                TRUNCATE TABLE segstack_template.assembly CASCADE;

                ALTER TABLE segstack_template.assembly
                  DROP COLUMN IF EXISTS core_id,
                  DROP COLUMN IF EXISTS hash,
                  ADD COLUMN solution_id integer NOT NULL REFERENCES solution(id) DEFERRABLE INITIALLY IMMEDIATE;

                DROP TABLE segstack_template.solution_assembly CASCADE;

                DROP TABLE segstack_template.assembly_segment CASCADE;

                CREATE TABLE segment_solution (
                  segment_id bigint NOT NULL REFERENCES segment(id) DEFERRABLE INITIALLY IMMEDIATE,
                  solution_id integer NOT NULL REFERENCES solution(id) DEFERRABLE INITIALLY IMMEDIATE,
                  assembly_id integer REFERENCES assembly(id) DEFERRABLE INITIALLY IMMEDIATE,
                  PRIMARY KEY (segment_id, solution_id),
                  CHECK (false) NO INHERIT -- prevent any rows populating this table
                ) WITH (
                  OIDS=FALSE
                );

                RESET search_path;
                ''')

        for segstack_id in SegmentationStack.objects.all().values_list('id', flat=True):
            db.execute('''
                    SET search_path TO segstack_%s,public;

                    TRUNCATE TABLE assembly CASCADE;

                    ALTER TABLE assembly
                      DROP COLUMN IF EXISTS core_id,
                      DROP COLUMN IF EXISTS hash,
                      ADD FOREIGN KEY (solution_id) REFERENCES solution(id) DEFERRABLE INITIALLY IMMEDIATE;

                    CREATE TABLE segment_solution
                        (LIKE segstack_template.segment_solution INCLUDING INDEXES,
                          FOREIGN KEY (segment_id) REFERENCES segment(id) DEFERRABLE INITIALLY IMMEDIATE,
                          FOREIGN KEY (solution_id) REFERENCES solution(id) DEFERRABLE INITIALLY IMMEDIATE,
                          FOREIGN KEY (assembly_id) REFERENCES assembly(id) DEFERRABLE INITIALLY IMMEDIATE)
                        INHERITS (segstack_template.segment_solution);

                    RESET search_path;
                    ''' % segstack_id)

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