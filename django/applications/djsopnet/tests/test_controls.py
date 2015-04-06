from django.test import TestCase
from django.test.client import Client
from django.db import connection
from guardian.shortcuts import assign_perm
import os

from catmaid.models import Project, User

class AssemblyTests(TestCase):
    fixtures = ['djsopnet_testdata']

    maxDiff = None

    def setUp(self):
        """ Creates a new test client and test user. The user is assigned
        permissions to modify an existing test project.
        """
        self.test_project_id = 1
        self.test_segstack_id = 2
        self.test_user_id = 3
        self.client = Client()

        p = Project.objects.get(pk=self.test_project_id)

        user = User.objects.get(pk=3)
        # Assign the new user permissions to browse and annotate projects
        assign_perm('can_browse', user, p)
        assign_perm('can_annotate', user, p)

        # Load unmanaged fixtures
        cursor = connection.cursor()
        with open(os.path.join(os.path.dirname(__file__), '..', 'fixtures', 'assembly_testdata.sql'), 'r') as sqlfile:
            cursor.execute(sqlfile.read())

    def fake_authentication(self, username='test2', password='test', add_default_permissions=False):
        self.client.login(username=username, password=password)

        if add_default_permissions:
            p = Project.objects.get(pk=self.test_project_id)
            user = User.objects.get(username=username)
            # Assign the new user permissions to browse and annotate projects
            assign_perm('can_browse', user, p)
            assign_perm('can_annotate', user, p)

    def test_generate_assemblies_for_core(self):
        self.fake_authentication()

        core_id = 000
        response = self.client.post(
                '/sopnet/%d/segmentation/%d/core/%d/generate_assemblies' % (self.test_project_id, self.test_segstack_id, core_id))
        self.assertEqual(response.status_code, 200)

        cursor = connection.cursor()
        cursor.execute("""
            SELECT count(a.id)
            FROM segstack_%(segstack_id)s.assembly a
            JOIN segstack_%(segstack_id)s.solution_precedence sp
              ON sp.solution_id = a.solution_id
            WHERE sp.core_id = %(core_id)s
            """ % {'segstack_id': self.test_segstack_id, 'core_id': core_id})
        self.assertEqual(cursor.fetchone()[0], 1,
                msg="Core should contain 1 assembly")

        cursor.execute("""
            SELECT count(*)
            FROM segstack_%(segstack_id)s.segment_solution ssol
            JOIN segstack_%(segstack_id)s.assembly a
              ON ssol.assembly_id = a.id
            JOIN segstack_%(segstack_id)s.solution_precedence sp
              ON sp.solution_id = a.solution_id
            WHERE ssol.segment_id BETWEEN 1000 AND 1999
              AND sp.core_id = %(core_id)s
            """ % {'segstack_id': self.test_segstack_id, 'core_id': core_id})
        self.assertEqual(cursor.fetchone()[0], 10,
                msg="All segments with ID 1xxx should be in assembly")
