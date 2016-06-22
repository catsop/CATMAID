from optparse import make_option
import sys

import numpy as np

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from djsopnet.models import SegmentationStack, BlockInfo


class Command(BaseCommand):
    args = '<segmentation_stack_id> [core_id] [solution_id]'
    help = '''
        Writes a libsvm/SVMlight-formatted training file from a solution,
        which should represent a gold standard. Currently does not include
        constraints.
        '''

    option_list = BaseCommand.option_list + (
        make_option('-f', '--file',
            dest='training_filename',
            default='svm_training.txt',
            help='training filename',
            metavar='FILE'),
        make_option('-n', '--normalization-file',
            dest='normalization_filename',
            default='svm_normalization.txt',
            help='feature normalization info filename',
            metavar='FILE')
    )

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.segstack_id = None
        self.core_id = None
        self.solution_id = None

    def handle(self, *args, **options):
        if len(args) < 1:
            raise CommandError('Must specify at least a segmentation stack ID')

        self.segstack_id = int(args[0])

        cursor = connection.cursor()

        # Parse core ID
        if len(args) >= 2:
            self.core_id = int(args[1])
            cursor.execute('''
                SELECT 1 FROM segstack_{0}.core WHERE id = %s
                '''.format(self.segstack_id), (self.core_id,))
            if cursor.rowcount == 0:
                raise CommandError('Core with ID {0} does not exist in segmentation stack {1}'.format(self.core_id, self.segsatck_id))
        else:
            cursor.execute('''
                SELECT id FROM segstack_{0}.core
                '''.format(self.segstack_id))
            if cursor.rowcount != 1:
                raise CommandError('If no core ID is provided, stack must contain exactly one core.')
            self.core_id = cursor.fetchone()[0]

        # Parse solution ID
        if len(args) >= 3:
            self.solution_id = int(args[2])
            cursor.execute('''
                SELECT 1 FROM segstack_{0}.solution WHERE id = %s AND core_id = %s
                '''.format(self.segstack_id), (self.solution_id, self.core_id,))
            if cursor.rowcount == 0:
                raise CommandError('Solution with ID {0} does not exist for core {1}'.format(self.solution_id, self.core_id))
        else:
            cursor.execute('''
                SELECT solution_id FROM segstack_{0}.solution_precedence WHERE core_id = %s
                '''.format(self.segstack_id), (self.core_id,))
            if cursor.rowcount != 1:
                raise CommandError('If no solution ID is provided, core must have a precedent solution.')
            self.solution_id = cursor.fetchone()[0]

        self.stdout.write('Writing training file for segmentation stack %s core %s solution %s' % (self.segstack_id, self.core_id, self.solution_id))
        self.write_training_file(options['training_filename'], options['normalization_filename'])

    def write_training_file(self, training_filename, normalization_filename):
        cursor = connection.cursor()

        segstack = SegmentationStack.objects.get(pk=self.segstack_id)
        bi = BlockInfo.objects.get(configuration_id=segstack.configuration_id)

        cursor.execute('''
            SELECT coordinate_x, coordinate_y, coordinate_z
            FROM segstack_{0}.core WHERE id = %s
            '''.format(self.segstack_id), (self.core_id,))
        core_coords = cursor.fetchone()
        block_coords_start = (core_coords[0] * bi.core_dim_x,
                              core_coords[1] * bi.core_dim_y,
                              core_coords[2] * bi.core_dim_z)
        block_coords_end = (block_coords_start[0] + bi.core_dim_x,
                            block_coords_start[1] + bi.core_dim_y,
                            block_coords_start[2] + bi.core_dim_z)
        block_coords = list(bi.block_range(block_coords_start, block_coords_end))
        block_ids = bi.unit_ids_from_coordinates('block', block_coords, self.segstack_id)

        cursor.execute('''
            SELECT sf.segment_id, sf.features
            FROM segstack_{0}.segment_features sf
            JOIN segstack_{0}.segment_block_relation sbr
              ON (sf.segment_id = sbr.segment_id)
            WHERE sbr.block_id = ANY(%s)
            GROUP BY sf.segment_id
            ORDER BY sf.segment_id ASC
            '''.format(self.segstack_id), (block_ids,))
        segments = list(cursor.fetchall())

        segment_features = np.matrix([s[1] for s in segments])
        segment_features_max = segment_features.max(axis=0)
        segment_features_min = segment_features.min(axis=0)
        segment_features_norm = (segment_features - segment_features_min) / segment_features.ptp(0)

        with open(normalization_filename, 'w') as f:
            for i in xrange(0, segment_features_min.size):
                f.write('%s %s\n' % (segment_features_min.flat[i], segment_features_max.flat[i]))

        cursor.execute('''
            SELECT DISTINCT aseg.segment_id
            FROM segstack_{0}.solution_assembly sola
            JOIN segstack_{0}.assembly_segment aseg
              ON aseg.assembly_id = sola.assembly_id
            WHERE sola.solution_id = %s
            ORDER BY aseg.segment_id ASC
            '''.format(self.segstack_id), (self.solution_id,))
        gold_standard_segment_ids = frozenset([r[0] for r in cursor.fetchall()])

        with open(training_filename, 'w') as f:
            for i in xrange(0, len(segments)):
                segment_id = segments[i][0]
                f.write('1' if segment_id in gold_standard_segment_ids else '-1')
                for j in xrange(0, segment_features_norm[i].size):
                    v = segment_features_norm[i, j]
                    if v != 0:
                        f.write(' %s:%s' % (j + 1, v))
                f.write(' # %s\n' % segment_id)
