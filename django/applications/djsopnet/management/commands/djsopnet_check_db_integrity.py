from django.core.management.base import NoArgsCommand
from django.db import connection
from djsopnet.models import SegmentationStack

class Command(NoArgsCommand):
    help = "Tests the integrity of the segmentation database with several sanity checks"

    def handle_noargs(self, **options):
        segstack_ids = SegmentationStack.objects.all().values_list('id', flat=True)

        for segstack_id in segstack_ids:
            self.check_segmentation_stack(segstack_id)

    def check_segmentation_stack(self, segmentation_stack_id):
        self.stdout.write('Checking integrity of segmentation stack %s' % segmentation_stack_id)

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
            self.stdout.write('FAILED: found %s conflicting rows (should be 0)' % row[0])

        self.stdout.write('Check that no slice is in more than two segments in the same solution...')
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
            self.stdout.write('FAILED: found %s rows (should be 0)' % cursor.rowcount)

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
            self.stdout.write('FAILED: found %s conflicting rows (should be 0)' % row[0])

        self.stdout.write('Check that all slices have exactly two end segments...')
        cursor = connection.cursor()
        cursor.execute('''
                SELECT sl.id, sl.section, count(seg.id) AS num_ends
                FROM segment_slice ss
                JOIN slice sl ON sl.id = ss.slice_id
                JOIN segment seg ON seg.id = ss.segment_id
                WHERE seg.type = 0
                GROUP BY sl.id
                HAVING count(seg.id) <> 2
                ''')
        if cursor.rowcount == 0:
            self.stdout.write('OK')
        else:
            self.stdout.write('FAILED: found %s rows (should be 0)' % cursor.rowcount)

        cursor.execute('RESET search_path;')
