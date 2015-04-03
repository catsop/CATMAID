"""
This is a custom version of the postgresql_psycopg2 adaptor that
overrides last_insert_id so that it works with inherited tables.
Instead of using pg_get_serial_sequence, this finds the default value
of the primary key for the table and parse out the sequence name from
that.
"""

from django.db.backends.postgresql_psycopg2.base import DatabaseWrapper as PG2DatabaseWrapper
from django.db.backends.postgresql_psycopg2.base import DatabaseError as PG2DatabaseError
from django.db.backends.postgresql_psycopg2.base import DatabaseOperations as PG2DatabaseOperations

from django.conf import settings

import re
import sys

class DatabaseError(Exception):
    pass

class DatabaseOperations(PG2DatabaseOperations):
    def last_insert_id(self, cursor, table_name, pk_name):
        # Get the default value for the column name:
        cursor.execute('''
SELECT adsrc
  FROM pg_attrdef pad, pg_attribute pat, pg_class pc
  WHERE pc.relname=%s AND
        pc.oid=pat.attrelid AND
        pat.attname=%s AND
        pat.attrelid=pad.adrelid AND
        pat.attnum=pad.adnum
''', (table_name, pk_name))
        # The default value should look like:
        #   nextval('concept_id_seq'::regclass)
        result_row = cursor.fetchone()
        if not result_row:
            # Then there's no column of that name, which may mean, for
            # example, that this is a managed join table with no "id"
            # column:
            return None
        default_value = result_row[0]
        m = re.search(r'nextval\(\'(.*?)\'::regclass\)', default_value)
        if not m:
            raise DatabaseError("Couldn't find the sequence for column '%s' in table '%s'" % (pk_name, table_name))
        cursor.execute("SELECT CURRVAL(%s)", (m.group(1),))
        return cursor.fetchone()[0]

    def sql_flush(self, style, tables, sequences, allow_cascade=False):
        allow_cascade = settings.TESTING_ENVIRONMENT or allow_cascade
        return PG2DatabaseOperations.sql_flush(self, style, tables, sequences, allow_cascade)

class DatabaseWrapper(PG2DatabaseWrapper):
    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)
        self.ops = DatabaseOperations(self)
