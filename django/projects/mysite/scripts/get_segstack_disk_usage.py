""" Retrieve disk usage statistics for the tables in a segmentation stack schema """

import os

os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

from django.conf import settings
from django.db import connection

from djsopnet.models import SegmentationConfiguration
from tests.testsopnet import SopnetTest

st = SopnetTest()
sc = SegmentationConfiguration.objects.get(pk=st.segmentation_configuration_id)
segstack = sc.segmentationstack_set.get(type='Membrane')

# the total bytes of the data and indices of the tables of the segmentation stack
result = {
	'data': {},
	'indices': {}
}

cursor = connection.cursor()
cursor.execute('''
	SELECT tablename FROM pg_tables WHERE schemaname='segstack_%s';
	''' % segstack.id)
table_names = [row[0] for row in cursor.fetchall()]

for table_name in table_names:
	cursor = connection.cursor()
	cursor.execute('''
		SELECT pg_relation_size('segstack_%s.%s');
		''' % (segstack.id, table_name) )
	result['data'][table_name] = cursor.fetchone()[0]

	cursor = connection.cursor()
	cursor.execute('''
		SELECT pg_total_relation_size('segstack_%s.%s');
		''' % (segstack.id, table_name))
	result['indices'][table_name] = cursor.fetchone()[0] - result['data'][table_name]

print 'slice data,', sum([v for k,v in result['data'].items() if k.startswith('slice')])
print 'slice indices,', sum([v for k,v in result['indices'].items() if k.startswith('slice')])
print 'segment data,', sum([v for k,v in result['data'].items() if k.startswith('segment')])
print 'segment indices,', sum([v for k,v in result['indices'].items() if k.startswith('segment')])
print 'other data,', sum([v for k,v in result['data'].items() if not k.startswith('segment') and not k.startswith('slice')])
print 'other indices,', sum([v for k,v in result['indices'].items() if not k.startswith('segment') and not k.startswith('slice')])
