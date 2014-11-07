from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

import csv
import filecmp
from optparse import make_option
import tempfile

class Command(BaseCommand):
    help = '''
        Verifies features and solutions in the database against a known standard
        (or exports such a standard) to test for changes or regressions in
        solutions
        '''

    option_list = BaseCommand.option_list + (
        make_option('--export',
            dest='export_filename',
            help='export the current database state to FILE as a standard for comparison',
            metavar='FILE'),
        make_option('-f', '--file',
            dest='standard_filename',
            default='sopnet_regression_standard~',
            help='name of the file to use as a regression standard',
            metavar='FILE')
    )

    def handle(self, *args, **options):
        if options['export_filename']:
            self.stdout.write('Exporting regression standard to %s...' % options['export_filename'])
            with open(options['export_filename'], 'wb') as csvfile:
                self.dumpdb(csvfile)
        else:
            self.stdout.write('Comparing database with standard file %s...' % options['standard_filename'])
            with tempfile.NamedTemporaryFile() as dumpfile:
                self.dumpdb(dumpfile)
                dumpfile.flush()
                with open(options['standard_filename'], 'rb') as csvfile:
                    if filecmp.cmp(dumpfile.name, csvfile.name, False):
                        self.stdout.write('Regression test OK: database and standard file are identical')
                    else:
                        self.stdout.write('Regression test FAILED: database and standard file differ')

    def dumpdb(self, file):
        filewriter = csv.writer(file, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)

        cursor = connection.cursor()
        cursor.execute('''
            SELECT sf.segment_id, sf.features
            FROM djsopnet_segment seg
            JOIN djsopnet_segmentfeatures sf ON (sf.segment_id = seg.id)
            WHERE seg.stack_id = %s
            ORDER BY sf.segment_id ASC
            ''' % settings.SOPNET_RAW_STACK_ID)
        for row in cursor.fetchall():
            filewriter.writerow(row)

        cursor = connection.cursor()
        cursor.execute('''
            SELECT sol.segment_id
            FROM djsopnet_segment seg
            JOIN djsopnet_segmentsolution sol ON (sol.segment_id = seg.id)
            WHERE seg.stack_id = %s
            ORDER BY sol.segment_ID ASC
            ''' % settings.SOPNET_RAW_STACK_ID)
        for row in cursor.fetchall():
            filewriter.writerow(row)
