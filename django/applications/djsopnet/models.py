import logging
import os
import re

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import connection, models
from django.db.models.signals import post_save
from django.dispatch import receiver

import pysopnet

from catmaid.models import Project, ProjectStack, Stack
import djsopnet

logger = logging.getLogger(__name__)


def int_ceil(num, den):
    """Utility for the integer ceiling of the quotient of two integers."""
    return ((num - 1) // den) + 1


class SegmentationConfiguration(models.Model):
    class Meta:
        db_table = 'segmentation_configuration'

    project = models.ForeignKey(Project)

    def __unicode__(self):
        return u'%s (%s)' % (self.project, self.pk)

    @staticmethod
    def create(project_id, raw_stack_id, membrane_stack_id, ground_truth_stack_id=None, feature_weights_file=None):
        """Creates a configuration, segmentation stacks and feature infos."""
        p = Project.objects.get(pk=project_id)
        sr = Stack.objects.get(pk=raw_stack_id)
        sm = Stack.objects.get(pk=membrane_stack_id)

        # Link both stacks to project
        psr, created = ProjectStack.objects.get_or_create(project=p, stack=sr)
        psm, created = ProjectStack.objects.get_or_create(project=p, stack=sm)

        sc = SegmentationConfiguration(project=p)
        sc.save()
        ssr, created = SegmentationStack.objects.get_or_create(
                configuration=sc, project_stack=psr, type='Raw')
        ssm, created = SegmentationStack.objects.get_or_create(
                configuration=sc, project_stack=psm, type='Membrane')

        if not feature_weights_file:
            feature_weights_file = os.path.join(os.path.dirname(djsopnet.__file__), 'fixtures', 'feature_weights.dat')
        fo = open(feature_weights_file, 'r')
        feature_weights = map(float, fo.readlines())
        fi, created = FeatureInfo.objects.get_or_create(segmentation_stack=ssm,
            defaults={'size':len(feature_weights), 'name_ids':[0], 'weights':feature_weights})
        if created:
            unnamed_feature = FeatureName(name='Unnamed Feature')
            unnamed_feature.save()
            feature_names = [unnamed_feature.id for i in range(len(feature_weights))]
            fi.name_ids = feature_names
            fi.save()

        if ground_truth_stack_id:
            sgt = Stack.objects.get(pk=ground_truth_stack_id)

            psgt, created = ProjectStack.objects.get_or_create(project=p, stack=sgt)

            ssgt, created = SegmentationStack.objects.get_or_create(
                    configuration=sc, project_stack=psgt, type='GroundTruth')

            gtfi, created = FeatureInfo.objects.get_or_create(segmentation_stack=ssgt,
                    defaults={'size':0, 'name_ids':[], 'weights':[]})

        return sc

    def to_pysopnet_configuration(self):
        bi = self.block_info
        conf = pysopnet.ProjectConfiguration()
        conf.setBackendType(pysopnet.BackendType.PostgreSql)
        min_width = float('inf')
        min_height = float('inf')
        min_depth = float('inf')

        for segstack in self.segmentationstack_set.all():
            stack = segstack.project_stack.stack
            stack_desc = pysopnet.StackDescription()
            # Strings require special handling to convert from unicode to std::string
            stack_desc.imageBase = stack.image_base.encode('utf8')
            stack_desc.fileExtension = stack.file_extension.encode('utf8')
            stack_desc.width = stack.dimension.x
            stack_desc.height = stack.dimension.y
            stack_desc.depth = stack.dimension.z
            min_width = min(stack_desc.width, min_width)
            min_height = min(stack_desc.height, min_height)
            min_depth = min(stack_desc.depth, min_depth)
            stack.resX = stack.resolution.x
            stack.resY = stack.resolution.y
            stack.resZ = stack.resolution.z
            stack_desc.scale = bi.scale
            stack_desc.id = stack.id
            stack_desc.segmentationId = segstack.id
            for name in ['tile_source_type', 'tile_width', 'tile_height']:
                camel_name = re.sub(r'(?!^)_([a-zA-Z])', lambda m: m.group(1).upper(), name)
                setattr(stack_desc, camel_name, getattr(stack, name))

            stack_type = pysopnet.StackType.names[segstack.type]
            conf.setCatmaidStack(stack_type, stack_desc)

        conf.setComponentDirectory(settings.SOPNET_COMPONENT_DIR)
        conf.setBlockSize(pysopnet.point3(bi.block_dim_x, bi.block_dim_y, bi.block_dim_z))
        conf.setVolumeSize(pysopnet.point3(
                min(bi.block_dim_x*bi.num_x, min_width),
                min(bi.block_dim_y*bi.num_y, min_height),
                min(bi.block_dim_z*bi.num_z, min_depth)))
        conf.setCoreSize(pysopnet.point3(bi.core_dim_x, bi.core_dim_y, bi.core_dim_z))
        conf.setPostgreSqlDatabase(settings.SOPNET_DATABASE['NAME'])
        conf.setPostgreSqlHost(settings.SOPNET_DATABASE['HOST'])
        conf.setPostgreSqlPort(settings.SOPNET_DATABASE['PORT'])
        conf.setPostgreSqlUser(settings.SOPNET_DATABASE['USER'])
        conf.setPostgreSqlPassword(settings.SOPNET_DATABASE['PASSWORD'])

        return conf


class SegmentationStack(models.Model):
    class Meta:
        db_table = 'segmentation_stack'

    configuration = models.ForeignKey(SegmentationConfiguration)
    project_stack = models.ForeignKey(ProjectStack)
    type = models.CharField(max_length=128)

    def __unicode__(self):
        return u'Segstack %s: %s' % (self.pk, self.project_stack)

    def clear_schema(self, delete_slices=True, delete_segments=True, delete_solutions=True, delete_assembly_relationships=False):
        """Deletes segmentation data from the segstack-specific schema."""
        delete_config = delete_slices and delete_segments

        cursor = connection.cursor()

        if delete_slices:
            cursor.execute('TRUNCATE TABLE segstack_%s.slice CASCADE;' % self.id)
            cursor.execute('UPDATE segstack_%s.block SET slices_flag = FALSE;' % self.id)

        if delete_segments:
            cursor.execute('TRUNCATE TABLE segstack_%s.segment CASCADE;' % self.id)
            cursor.execute('UPDATE segstack_%s.block SET segments_flag = FALSE;' % self.id)

        if delete_solutions:
            cursor.execute('TRUNCATE TABLE segstack_%s.assembly_equivalence CASCADE;' % self.id)
            cursor.execute('TRUNCATE TABLE segstack_%s.solution CASCADE;' % self.id)
            cursor.execute('UPDATE segstack_%s.core SET solution_set_flag = FALSE;' % self.id)

        if delete_assembly_relationships:
            cursor.execute('UPDATE segstack_%s.assembly SET equivalence_id = NULL WHERE equivalence_id IS NOT NULL;' % self.id)
            cursor.execute('DELETE FROM segstack_%s.assembly_equivalence;' % self.id)
            cursor.execute('TRUNCATE TABLE segstack_%s.assembly_relation;' % self.id)

        if delete_config:
            cursor.execute('TRUNCATE TABLE segstack_%s.block CASCADE;' % self.id)
            cursor.execute('TRUNCATE TABLE segstack_%s.core CASCADE;' % self.id)


@receiver(post_save, sender=SegmentationStack)
def create_segmentation_stack_schema(sender, instance, created, **kwargs):
    if created:
        cursor = connection.cursor()
        cursor.execute('''
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name = 'segstack_%s';
            ''' % instance.id)
        if cursor.rowcount:
            logger.warning('''
                Schema for segmentation stack %s already exists. No schema changes made.
                ''' % instance.id)
        else:
            with open(os.path.join(os.path.dirname(__file__), 'sql', 'instantiate_segmentation.sql'), 'r') as sqlfile:
                cursor.execute(('''
                    CREATE SCHEMA segstack_%(segstack_id)s;
                    SET search_path TO segstack_%(segstack_id)s,public;
                    ''' % {'segstack_id': instance.id}) + \
                    sqlfile.read() +\
                    'RESET search_path;')


class BlockInfo(models.Model):
    class Meta:
        db_table = 'segmentation_block_info'

    configuration = models.OneToOneField(SegmentationConfiguration, primary_key=True,
            related_name='block_info')

    scale = models.IntegerField(default=0, help_text='''
        Zoom level for segmentation data relative to raw stack.''')

    # Block height, width, depth, measured units of scaled pixels
    block_dim_x = models.IntegerField(default=256)
    block_dim_y = models.IntegerField(default=256)
    block_dim_z = models.IntegerField(default=16)

    # Core height, width, depth, measured in units of Blocks
    core_dim_x = models.IntegerField(default=1)
    core_dim_y = models.IntegerField(default=1)
    core_dim_z = models.IntegerField(default=1)

    # Number of blocks in x, y and z
    num_x = models.IntegerField(default=0)
    num_y = models.IntegerField(default=0)
    num_z = models.IntegerField(default=0)

    def __unicode__(self):
        return u'%s block info' % (self.configuration,)

    def save(self, *args, **kwargs):
        # Set the number of blocks based on the size of the raw stack.
        if not kwargs.get('raw', False):
            stack = SegmentationStack.objects.get(
                            configuration_id=self.configuration_id,
                            type='Raw').project_stack.stack

            # The number of blocks is the ceiling of the stack size divided by block dimension
            self.num_x = int_ceil(stack.dimension.x, self.block_dim_x * 2**self.scale)
            self.num_y = int_ceil(stack.dimension.y, self.block_dim_y * 2**self.scale)
            self.num_z = int_ceil(stack.dimension.z, self.block_dim_z)

        super(BlockInfo, self).save(*args, **kwargs)

        self.setup_blocks()

    def block_range(self, start=None, end=None):
        """Generator yielding all block coordinates."""
        if not start:
            start = (0, 0, 0)
        if not end:
            end = (self.num_x, self.num_y, self.num_z)
        for i in xrange(start[0], end[0]):
            for j in xrange(start[1], end[1]):
                for k in xrange(start[2], end[2]):
                    yield (i, j, k)

    def core_extents(self):
        """Returns the number of cores in each dimension."""
        return (int_ceil(self.num_x, self.core_dim_x),
                int_ceil(self.num_y, self.core_dim_y),
                int_ceil(self.num_z, self.core_dim_z))

    def core_range(self, start=None, end=None):
        """Generator yielding all core coordinates."""
        if not start:
            start = (0, 0, 0)
        if not end:
            end = self.core_extents()
        for i in xrange(start[0], end[0]):
            for j in xrange(start[1], end[1]):
                for k in xrange(start[2], end[2]):
                    yield (i, j, k)

    def core_neighbor_range(self, coords, half=True):
        """Generator yielding 6-neighbors to a core."""
        i, j, k = coords
        end = self.core_extents()
        deltas = [(1, 0, 0), (0, 1, 0), (0, 0, 1)]
        if not half:
            deltas.extend([(-1, 0, 0), (0, -1, 0), (0, 0, -1)])
        for (di, dj, dk) in deltas:
            if i + di < end[0] and \
               j + dj < end[1] and \
               k + dk < end[2]:
                yield (i + di, j + dj, k + dk)

    def core_interface_block_range(self, core_a, core_b):
        """Generator for all block coordinates in `core_a` adjacent to `core_b`.
        """
        delta = (core_b[0] - core_a[0],
                 core_b[1] - core_a[1],
                 core_b[2] - core_a[2])
        normal = map(abs, delta)
        if not sum(normal) == 1:
            raise ValueError('Cores are not adjacent')
        delta = map(max, delta, (0, 0, 0))

        start = ((core_a[0] + delta[0]) * self.core_dim_x - delta[0],
                 (core_a[1] + delta[1]) * self.core_dim_y - delta[1],
                 (core_a[2] + delta[2]) * self.core_dim_z - delta[2])
        start = map(max, start, (0, 0, 0))
        end = (start[0] + (1 - normal[0]) * self.core_dim_x + normal[0],
               start[1] + (1 - normal[1]) * self.core_dim_y + normal[1],
               start[2] + (1 - normal[2]) * self.core_dim_z + normal[2])
        end = map(min, end, (self.num_x, self.num_y, self.num_z))
        for i in xrange(start[0], end[0]):
            for j in xrange(start[1], end[1]):
                for k in xrange(start[2], end[2]):
                    yield (i, j, k)

    def unit_ids_from_coordinates(self, table, coords, segmentation_stack_id):
        """Get block/core IDs from coordinates for a segmentation stack."""
        if not table == 'block' and not table == 'core':
            raise ValueError('%s is not a blockwise unit' % table)
        if len(coords) == 0:
            return []
        coord_tuples = ','.join(['(%s, %s, %s)' % tuple(map(int, coord)) for coord in coords])
        cursor = connection.cursor()
        cursor.execute('''
            WITH coords AS (VALUES %(coord_tuples)s)
            SELECT u.id
            FROM coords AS c (x, y, z)
            JOIN segstack_%(segstack_id)s.%(table)s u ON (
                u.coordinate_x = c.x AND
                u.coordinate_y = c.y AND
                u.coordinate_z = c.z);
            ''' % {'coord_tuples': coord_tuples,
                   'segstack_id': int(segmentation_stack_id),
                   'table': table})
        return [row[0] for row in cursor.fetchall()]

    def setup_blocks(self):
        """Creates blocks and cores in each segmentation stack schema."""
        cursor = connection.cursor()
        for segstack in self.configuration.segmentationstack_set.all():
            cursor.execute('SELECT 1 FROM segstack_%s.block LIMIT 1' % segstack.id)
            if cursor.rowcount > 0:
                logger.warning('Blocks for SegmentationStack %s are already setup.', segstack.id)
                continue

            cursor.execute('''
                    INSERT INTO segstack_{0}.block
                      (slices_flag, segments_flag, coordinate_x, coordinate_y, coordinate_z)
                        SELECT false, false, x.id, y.id, z.id FROM
                          generate_series(0, %s - 1) AS x (id),
                          generate_series(0, %s - 1) AS y (id),
                          generate_series(0, %s - 1) AS z (id);
                    '''.format(segstack.id), (self.num_x, self.num_y, self.num_z))

            # Create new Cores, round up if number of blocks is not divisible by core size
            nxc, nyc, nzc = self.core_extents()
            cursor.execute('''
                    INSERT INTO segstack_{0}.core
                      (solution_set_flag, coordinate_x, coordinate_y, coordinate_z)
                        SELECT false, x.id, y.id, z.id FROM
                          generate_series(0, %s - 1) AS x (id),
                          generate_series(0, %s - 1) AS y (id),
                          generate_series(0, %s - 1) AS z (id);
                    '''.format(segstack.id), (nxc, nyc, nzc))

    @staticmethod
    def update_or_create(configuration_id, scale, width, height, depth, corewib, corehib, coredib):
        """Updates or creates a segmentation configuration block decomposition.
        """
        # TODO: this method should be removed once upgraded to Django 1.7,
        # since it provides this functionality with a different signature.
        try:
            info = BlockInfo.objects.get(configuration_id=configuration_id)
            info.block_dim_x = width
            info.block_dim_y = height
            info.block_dim_z = depth
            info.core_dim_x = corewib
            info.core_dim_y = corehib
            info.core_dim_z = coredib
            info.save()
        except BlockInfo.DoesNotExist:
            info = BlockInfo(configuration_id=configuration_id, scale=scale,
                             block_dim_y=height, block_dim_x=width, block_dim_z=depth,
                             core_dim_y=corehib, core_dim_x=corewib, core_dim_z=coredib)
            info.save()

    def size_for_unit(self, table):
        if table == 'block':
            zoom = 2**self.scale
            return {'x': zoom * self.block_dim_x,
                    'y': zoom * self.block_dim_y,
                    'z': self.block_dim_z}
        elif table == 'core':
            zoom = 2**self.scale
            return {'x': zoom * self.core_dim_x * self.block_dim_x,
                    'y': zoom * self.core_dim_y * self.block_dim_y,
                    'z': self.core_dim_z * self.block_dim_z}
        else:
            raise ValueError('%s is not a blockwise unit' % table)


class FeatureName(models.Model):
    class Meta:
        db_table = 'segmentation_feature_name'

    name = models.CharField(max_length=128)

    def __unicode__(self):
        return self.name


class FeatureInfo(models.Model):
    class Meta:
        db_table = 'segmentation_feature_info'

    segmentation_stack = models.OneToOneField(SegmentationStack, primary_key=True)
    size = models.IntegerField(default=0)
    name_ids = ArrayField(models.IntegerField())
    weights = ArrayField(models.FloatField())

    def __unicode__(self):
        return u'%s feature info' % (self.segmentation_stack,)

    def import_weights(self, feature_weights_file):
        fo = open(feature_weights_file, 'r')

        weights = map(float, fo.readlines())
        if len(weights) != self.size:
            raise ValueError('Expected %s weights but found %s.' % (self.size, len(weights)))

        self.weights = weights
        self.save(update_fields=['weights'])

@receiver(post_save, sender=FeatureInfo)
def clear_cost_cache_on_feature_weights_update(**kwargs):
    """Changing feature weights invalidates cached costs."""
    if kwargs['update_fields'] and 'weights' in kwargs['update_fields']:
        # Clear existing cached costs for segstack
        cursor = connection.cursor()
        cursor.execute('''
            UPDATE segstack_%s.segment SET cost = NULL
            ''' % kwargs['instance'].segmentation_stack_id)
