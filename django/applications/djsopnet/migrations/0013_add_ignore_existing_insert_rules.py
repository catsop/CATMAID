# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Ignore duplicate inserts of slice-slice associations to the conflict sets table
        db.execute('''
            CREATE OR REPLACE RULE djsopnet_sliceconflictset_on_duplicate_ignore
            AS ON INSERT TO djsopnet_sliceconflictset
            WHERE EXISTS (SELECT 1 FROM djsopnet_sliceconflictset WHERE slice_a_id=NEW.slice_a_id AND slice_b_id=NEW.slice_b_id)
            DO INSTEAD NOTHING
        ''')

    def backwards(self, orm):
        db.execute('''
            DROP RULE IF EXISTS djsopnet_sliceconflictset_on_duplicate_ignore
            ON djsopnet_sliceconflictset
        ''')

    complete_apps = ['djsopnet']

