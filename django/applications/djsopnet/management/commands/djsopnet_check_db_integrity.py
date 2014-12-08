from django.conf import settings
from django.core.management.base import NoArgsCommand, CommandError
from django.db import connection

class Command(NoArgsCommand):
    help = "Tests the integrity of the segmentation database with several sanity checks"

    def handle_noargs(self, **options):
        self.stdout.write('Check that no conflicting slices are in the same solution...')
        cursor = connection.cursor()
        cursor.execute('''
                SELECT count(*)
                FROM djsopnet_segmentsolution ssol1
                  JOIN djsopnet_segmentslice ss1
                    ON (ss1.segment_id = ssol1.segment_id)
                  JOIN djsopnet_sliceconflictset scs
                    ON (ss1.slice_id = scs.slice_a_id OR ss1.slice_id = scs.slice_b_id)
                  JOIN djsopnet_segmentslice ss2
                    ON ((ss2.slice_id = scs.slice_a_id OR ss2.slice_id = scs.slice_b_id)
                        AND ss2.slice_id <> ss1.slice_id)
                  JOIN djsopnet_segmentsolution ssol2
                    ON (ssol2.segment_id = ss2.segment_id)
                  WHERE ss1.segment_id <> ss2.segment_id AND ssol1.solution_id = ssol2.solution_id
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
                FROM djsopnet_slice s
                  JOIN djsopnet_segmentslice ss1
                    ON (ss1.slice_id = s.id)
                  JOIN djsopnet_segmentslice ss2
                    ON (ss2.slice_id = s.id AND ss1.segment_id <> ss2.segment_id)
                  JOIN djsopnet_segmentsolution ssol1
                    ON (ssol1.segment_id = ss1.segment_id)
                  JOIN djsopnet_segmentsolution ssol2
                    ON (ssol2.segment_id = ss2.segment_id AND ssol1.solution_id = ssol2.solution_id)
                  GROUP BY s.id
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
                FROM djsopnet_segmentslice ss1
                  JOIN djsopnet_segmentslice ss2
                    ON (ss1.segment_id = ss2.segment_id AND ss1.id <> ss2.id)
                  JOIN djsopnet_sliceconflictset scs
                    ON (scs.slice_a_id = ss1.slice_id AND scs.slice_b_id = ss2.slice_id);
                ''')
        row = cursor.fetchone()
        if row[0] == 0:
            self.stdout.write('OK')
        else:
            self.stdout.write('FAILED: found %s conflicting rows (should be 0)' % row[0])
