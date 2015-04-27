from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

import csv
import filecmp
from optparse import make_option
import tempfile

class Command(BaseCommand):
    args = '<segmentation_stack_id>'
    help = '''
        Verifies features and solutions in the database against a known standard
        (or exports such a standard) to test for changes or regressions in
        solutions for a specified segmentation stack
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

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.segstack_id = None

    def handle(self, *args, **options):
        if len(args) == 1:
            self.segstack_id = int(args[0])
        else:
            raise CommandError('Must specify a single segmentation stack ID')

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
            FROM segstack_%(segstack_id)s.segment seg
            JOIN segstack_%(segstack_id)s.segment_features sf ON (sf.segment_id = seg.id)
            ORDER BY sf.segment_id ASC
            ''' % {'segstack_id': self.segstack_id})
        for row in cursor.fetchall():
            filewriter.writerow(row)

        cursor = connection.cursor()
        cursor.execute('''
            SELECT aseg.segment_id
            FROM segstack_%(segstack_id)s.solution_precedence sp
            JOIN segstack_%(segstack_id)s.solution_assembly sola
              ON sola.solution_id = sp.solution_id
            JOIN segstack_%(segstack_id)s.assembly_segment aseg
              ON aseg.assembly_id = sola.assembly_id
            ORDER BY aseg.segment_id ASC
            ''' % {'segstack_id': self.segstack_id})
        for row in cursor.fetchall():
            filewriter.writerow(row)
