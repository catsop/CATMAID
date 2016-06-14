import sys

from django.core.management.base import BaseCommand
from django.db import connection
from djsopnet.models import SegmentationStack

class Command(BaseCommand):
    args = '[segmentation_stack_id]'
    help = '''
        Tests the integrity of the segmentation database with several
        sanity checks. By default checks all segmentation stacks, but
        a list of segmentation stack IDs can be provided.
        '''

    def handle(self, *args, **options):
        if args:
            segstack_ids = [int(x) for x in args]
        else:
            segstack_ids = SegmentationStack.objects.all().values_list('id', flat=True)
        failed = False

        for segstack_id in segstack_ids:
            failed = failed or self.check_segmentation_stack(segstack_id)

        if failed:
          sys.exit(1)

    def check_segmentation_stack(self, segmentation_stack_id):
        self.stdout.write('Checking integrity of segmentation stack %s' % segmentation_stack_id)
        segstack = SegmentationStack.objects.get(pk=segmentation_stack_id)
        failed = False

        cursor = connection.cursor()
        cursor.execute('SET search_path TO segstack_%s,public;' % segmentation_stack_id)
        self.stdout.write('Check that no conflicting slices are in the same solution...')
        cursor.execute('''
                SELECT count(*)
                FROM solution_assembly sola1
                  JOIN assembly_segment aseg1
                    ON (aseg1.assembly_id = sola1.assembly_id)
                  JOIN segment_slice ss1
                    ON (ss1.segment_id = aseg1.segment_id)
                  JOIN slice_conflict scs
                    ON (ss1.slice_id = scs.slice_a_id OR ss1.slice_id = scs.slice_b_id)
                  JOIN segment_slice ss2
                    ON ((ss2.slice_id = scs.slice_a_id OR ss2.slice_id = scs.slice_b_id)
                        AND ss2.slice_id <> ss1.slice_id)
                  JOIN assembly_segment aseg2
                    ON (aseg2.segment_id = ss2.segment_id)
                  JOIN solution_assembly sola2
                    ON (sola1.assembly_id = aseg2.assembly_id)
                  WHERE ss1.segment_id <> ss2.segment_id AND sola1.solution_id = sola2.solution_id
                ''')
        row = cursor.fetchone()
        if row[0] == 0:
            self.stdout.write('OK')
        else:
            failed = True
            self.stderr.write('FAILED: found %s conflicting rows (should be 0)' % row[0])

        self.stdout.write('Check that no segment is in more than one assembly in the same solution...')
        cursor = connection.cursor()
        cursor.execute('''
                SELECT seg.id, count(*)
                FROM segment seg
                  JOIN assembly_segment aseg1
                    ON (aseg1.segment_id = seg.id)
                  JOIN assembly_segment aseg2
                    ON (aseg2.segment_id = seg.id
                        AND aseg1.assembly_id <> aseg2.assembly_id)
                  JOIN solution_assembly sola1
                    ON (sola1.assembly_id = aseg1.assembly_id)
                  JOIN solution_assembly sola2
                    ON (sola2.assembly_id = aseg2.assembly_id
                        AND sola1.solution_id = sola2.solution_id)
                  GROUP BY seg.id, sola1.solution_id
                ''')
        if cursor.rowcount == 0:
            self.stdout.write('OK')
        else:
            failed = True
            self.stderr.write('FAILED: found %s rows (should be 0)' % cursor.rowcount)

        self.stdout.write('Check that no slice is in more than one assembly in the same solution...')
        cursor = connection.cursor()
        cursor.execute('''
                SELECT s.id, count(*)
                FROM slice s
                  JOIN segment_slice ss1
                    ON (ss1.slice_id = s.id)
                  JOIN segment_slice ss2
                    ON (ss2.slice_id = s.id AND ss1.segment_id <> ss2.segment_id)
                  JOIN assembly_segment aseg1
                    ON (aseg1.segment_id = ss1.segment_id)
                  JOIN assembly_segment aseg2
                    ON (aseg2.segment_id = ss2.segment_id
                        AND aseg1.assembly_id <> aseg2.assembly_id)
                  JOIN solution_assembly sola1
                    ON (sola1.assembly_id = aseg1.assembly_id)
                  JOIN solution_assembly sola2
                    ON (sola2.assembly_id = aseg2.assembly_id
                        AND sola1.solution_id = sola2.solution_id)
                  GROUP BY s.id, sola1.solution_id
                ''')
        if cursor.rowcount == 0:
            self.stdout.write('OK')
        else:
            failed = True
            self.stderr.write('FAILED: found %s rows (should be 0)' % cursor.rowcount)

        self.stdout.write('Check that no slice is in more than two segments in the same solution...')
        if segstack.type == 'GroundTruth':
            self.stdout.write('NOTE: this is expected to fail for ground truth stacks')
        cursor = connection.cursor()
        cursor.execute('''
                SELECT s.id, count(*)
                FROM slice s
                  JOIN segment_slice ss1
                    ON (ss1.slice_id = s.id)
                  JOIN segment_slice ss2
                    ON (ss2.slice_id = s.id AND ss1.segment_id <> ss2.segment_id)
                  JOIN assembly_segment aseg1
                    ON (aseg1.segment_id = ss1.segment_id)
                  JOIN assembly_segment aseg2
                    ON (aseg2.segment_id = ss2.segment_id
                        AND aseg1.segment_id <> aseg2.segment_id)
                  JOIN solution_assembly sola1
                    ON (sola1.assembly_id = aseg1.assembly_id)
                  JOIN solution_assembly sola2
                    ON (sola2.assembly_id = aseg2.assembly_id
                        AND sola1.solution_id = sola2.solution_id)
                  GROUP BY s.id, sola1.solution_id
                    HAVING count(*) > 2
                ''')
        if cursor.rowcount == 0:
            self.stdout.write('OK')
        else:
            failed = True
            self.stderr.write('FAILED: found %s rows (should be 0)' % cursor.rowcount)

        self.stdout.write('Check that no segment contains conflicting slices...')
        cursor = connection.cursor()
        cursor.execute('''
                SELECT count(*)
                FROM segment_slice ss1
                  JOIN segment_slice ss2
                    ON (ss1.segment_id = ss2.segment_id AND ss1.slice_id <> ss2.slice_id)
                  JOIN slice_conflict scs
                    ON (scs.slice_a_id = ss1.slice_id AND scs.slice_b_id = ss2.slice_id);
                ''')
        row = cursor.fetchone()
        if row[0] == 0:
            self.stdout.write('OK')
        else:
            failed = True
            self.stderr.write('FAILED: found %s conflicting rows (should be 0)' % row[0])

        self.stdout.write('Check that all slices have exactly two end segments...')
        if segstack.type == 'GroundTruth':
            self.stdout.write('NOTE: this is expected to fail for ground truth stacks')
        cursor = connection.cursor()
        cursor.execute('''
                SELECT ss.slice_id, count(seg.id) AS num_ends
                FROM segment_slice ss
                JOIN segment seg ON seg.id = ss.segment_id
                WHERE seg.type = 0
                GROUP BY ss.slice_id
                HAVING count(seg.id) <> 2
                ''')
        if cursor.rowcount == 0:
            self.stdout.write('OK')
        else:
            failed = True
            self.stderr.write('FAILED: found %s rows (should be 0)' % cursor.rowcount)

        self.stdout.write('Check that all segments have the correct number of slices...')
        cursor = connection.cursor()
        cursor.execute('''
                SELECT seg.id, seg.type, count(ss.slice_id)
                FROM segment seg
                  JOIN segment_slice ss
                    ON (ss.segment_id = seg.id)
                  GROUP BY seg.id
                  HAVING count(ss.slice_id) > seg.type + 1
                ''')
        if cursor.rowcount == 0:
            self.stdout.write('OK')
        else:
            failed = True
            self.stderr.write('FAILED: found %s rows (should be 0)' % cursor.rowcount)

        cursor.execute('RESET search_path;')

        return failed
