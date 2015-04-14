from django.test import TestCase, TransactionTestCase
from django.test.client import Client
from django.db import connection, transaction
from guardian.shortcuts import assign_perm
import os
import json

from catmaid.models import Project, User, Treenode
from catmaid.control.tracing import setup_tracing
from djsopnet.control.assembly import \
        generate_assembly_equivalences, \
        generate_compatible_assemblies_between_cores, \
        generate_conflicting_assemblies_between_cores, \
        generate_continuing_assemblies_between_cores, \
        map_assembly_equivalence_to_arborescence

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

    def assertNumberOfAssemblyRelationsBetweenCores(self, relation_name, core_a_id, core_b_id, num):
        cursor = connection.cursor()
        cursor.execute("""
            SELECT count(ar.id)
            FROM segstack_%(segstack_id)s.assembly_relation ar
            JOIN segstack_%(segstack_id)s.assembly a1
              ON a1.id = ar.assembly_a_id
            JOIN segstack_%(segstack_id)s.assembly a2
              ON a2.id = ar.assembly_b_id
            JOIN segstack_%(segstack_id)s.solution_precedence sp1
              ON sp1.solution_id = a1.solution_id
            JOIN segstack_%(segstack_id)s.solution_precedence sp2
              ON sp2.solution_id = a2.solution_id
            WHERE ar.relation = '%(relation_name)s'::assemblyrelation
              AND sp1.core_id = %(core_a_id)s
              AND sp2.core_id = %(core_b_id)s
            """ % {
                'segstack_id': self.test_segstack_id,
                'relation_name': relation_name,
                'core_a_id': core_a_id,
                'core_b_id': core_b_id})
        self.assertEqual(cursor.fetchone()[0], num)

    def assertAssembliesForSegmentsHaveRelation(self, relation_name, segment_a_id, core_a_id, segment_b_id, core_b_id):
        cursor = connection.cursor()
        cursor.execute("""
            WITH assembly_a AS (
                    SELECT ssol.assembly_id AS id
                    FROM segstack_%(segstack_id)s.segment_solution ssol
                    JOIN segstack_%(segstack_id)s.assembly a
                      ON ssol.assembly_id = a.id
                    JOIN segstack_%(segstack_id)s.solution_precedence sp
                      ON sp.solution_id = a.solution_id
                    WHERE ssol.segment_id = %(segment_a_id)s
                      AND sp.core_id = %(core_a_id)s
                ), assembly_b AS (
                    SELECT ssol.assembly_id AS id
                    FROM segstack_%(segstack_id)s.segment_solution ssol
                    JOIN segstack_%(segstack_id)s.assembly a
                      ON ssol.assembly_id = a.id
                    JOIN segstack_%(segstack_id)s.solution_precedence sp
                      ON sp.solution_id = a.solution_id
                    WHERE ssol.segment_id = %(segment_b_id)s
                      AND sp.core_id = %(core_b_id)s
                )
            SELECT 1
            FROM segstack_%(segstack_id)s.assembly_relation ar
            WHERE ar.assembly_a_id IN (SELECT id FROM assembly_a)
              AND ar.assembly_b_id IN (SELECT id FROM assembly_b)
              AND ar.relation = '%(relation_name)s'::assemblyrelation
            """ % {
                'segstack_id': self.test_segstack_id,
                'relation_name': relation_name,
                'core_a_id': core_a_id,
                'core_b_id': core_b_id,
                'segment_a_id': segment_a_id,
                'segment_b_id': segment_b_id})
        self.assertEqual(cursor.rowcount, 1)

    def assertAssembliesForSegmentsInEquivalence(self, segment_a_id, core_a_id, segment_b_id, core_b_id):
        cursor = connection.cursor()
        cursor.execute("""
            WITH assembly_a AS (
                    SELECT ssol.assembly_id AS id
                    FROM segstack_%(segstack_id)s.segment_solution ssol
                    JOIN segstack_%(segstack_id)s.assembly a
                      ON ssol.assembly_id = a.id
                    JOIN segstack_%(segstack_id)s.solution_precedence sp
                      ON sp.solution_id = a.solution_id
                    WHERE ssol.segment_id = %(segment_a_id)s
                      AND sp.core_id = %(core_a_id)s
                ), assembly_b AS (
                    SELECT ssol.assembly_id AS id
                    FROM segstack_%(segstack_id)s.segment_solution ssol
                    JOIN segstack_%(segstack_id)s.assembly a
                      ON ssol.assembly_id = a.id
                    JOIN segstack_%(segstack_id)s.solution_precedence sp
                      ON sp.solution_id = a.solution_id
                    WHERE ssol.segment_id = %(segment_b_id)s
                      AND sp.core_id = %(core_b_id)s
                )
            SELECT a.equivalence_id
            FROM segstack_%(segstack_id)s.assembly a
            WHERE a.id IN (SELECT id FROM assembly_a UNION SELECT id FROM assembly_b)
            """ % {
                'segstack_id': self.test_segstack_id,
                'core_a_id': core_a_id,
                'core_b_id': core_b_id,
                'segment_a_id': segment_a_id,
                'segment_b_id': segment_b_id})
        self.assertEqual(cursor.rowcount, 2)
        rows = cursor.fetchall()
        self.assertEqual(rows[0][0], rows[1][0])

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
        self.assertEqual(cursor.fetchone()[0], 3,
                msg="Core should contain 3 assemblies")

        cursor.execute("""
            SELECT count(*)
            FROM segstack_%(segstack_id)s.segment_solution ssol
            JOIN segstack_%(segstack_id)s.assembly a
              ON ssol.assembly_id = a.id
            JOIN segstack_%(segstack_id)s.solution_precedence sp
              ON sp.solution_id = a.solution_id
            WHERE ssol.segment_id BETWEEN 1000000 AND 1000999
              AND sp.core_id = %(core_id)s
            """ % {'segstack_id': self.test_segstack_id, 'core_id': core_id})
        self.assertEqual(cursor.fetchone()[0], 30,
                msg="All segments with ID 1000[014]xx should be in assembly")

    def test_continuing_assemblies_between_cores(self):
        self.fake_authentication()

        for core_id in [000, 001, 010, 011]:
            response = self.client.post(
                    '/sopnet/%d/segmentation/%d/core/%d/generate_assemblies' % (self.test_project_id, self.test_segstack_id, core_id))
            self.assertEqual(response.status_code, 200)

        core_a_id = 000
        core_b_id = 001
        generate_continuing_assemblies_between_cores(self.test_segstack_id, core_a_id, core_b_id)

        self.assertNumberOfAssemblyRelationsBetweenCores('Continuation', core_a_id, core_b_id, 2)

        self.assertAssembliesForSegmentsHaveRelation('Continuation', 1000000, 000, 1001020, 001)
        self.assertAssembliesForSegmentsHaveRelation('Continuation', 1000400, 000, 1001420, 001)

    def test_conflicting_assemblies_between_cores(self):
        self.fake_authentication()

        for core_id in [000, 001, 010, 011]:
            response = self.client.post(
                    '/sopnet/%d/segmentation/%d/core/%d/generate_assemblies' % (self.test_project_id, self.test_segstack_id, core_id))
            self.assertEqual(response.status_code, 200)

        core_a_id = 000
        core_b_id = 001
        generate_conflicting_assemblies_between_cores(self.test_segstack_id, core_a_id, core_b_id)

        self.assertNumberOfAssemblyRelationsBetweenCores('Conflict', core_a_id, core_b_id, 2)

        self.assertAssembliesForSegmentsHaveRelation('Conflict', 1000100, 000, 1001220, 001)
        self.assertAssembliesForSegmentsHaveRelation('Conflict', 1000400, 000, 1001420, 001)

    def test_compatible_assemblies_between_cores(self):
        self.fake_authentication()

        for core_id in [000, 001, 010, 011]:
            response = self.client.post(
                    '/sopnet/%d/segmentation/%d/core/%d/generate_assemblies' % (self.test_project_id, self.test_segstack_id, core_id))
            self.assertEqual(response.status_code, 200)

        core_a_id = 000
        core_b_id = 001
        generate_compatible_assemblies_between_cores(self.test_segstack_id, core_a_id, core_b_id)

        self.assertNumberOfAssemblyRelationsBetweenCores('Compatible', core_a_id, core_b_id, 1)

        self.assertAssembliesForSegmentsHaveRelation('Compatible', 1000000, 000, 1001020, 001)

    def test_assembly_equivalences(self):
        self.fake_authentication()

        for core_id in [000, 001, 010, 011]:
            response = self.client.post(
                    '/sopnet/%d/segmentation/%d/core/%d/generate_assemblies' % (self.test_project_id, self.test_segstack_id, core_id))
            self.assertEqual(response.status_code, 200)

        core_a_id = 000
        core_b_id = 001
        generate_compatible_assemblies_between_cores(self.test_segstack_id, core_a_id, core_b_id)

        generate_assembly_equivalences(self.test_segstack_id)

        cursor = connection.cursor()
        cursor.execute("""
            SELECT count(*)
            FROM segstack_%s.assembly_equivalence ae
            """ % self.test_segstack_id)
        self.assertEqual(cursor.fetchone()[0], 1)

        self.assertAssembliesForSegmentsInEquivalence(1000000, 000, 1001020, 001)

# Because the assembly relation function use their own transactions, Django
# fails when these are intermixed with its own atomic requests in TestCase where
# transactional behavior is silently changed. Instead skeleton mapping must be
# run as its own TransactionTestCase.

class MappedSkeletonTests(TransactionTestCase):
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

        setup_tracing(self.test_project_id, user)

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

    def get_assembly_equivalences_for_segment(self, segment_id, core_id):
        cursor = connection.cursor()
        cursor.execute("""
            WITH assembly_a AS (
                    SELECT ssol.assembly_id AS id
                    FROM segstack_%(segstack_id)s.segment_solution ssol
                    JOIN segstack_%(segstack_id)s.assembly a
                      ON ssol.assembly_id = a.id
                    JOIN segstack_%(segstack_id)s.solution_precedence sp
                      ON sp.solution_id = a.solution_id
                    WHERE ssol.segment_id = %(segment_a_id)s
                      AND sp.core_id = %(core_a_id)s
                )
            SELECT a.equivalence_id
            FROM segstack_%(segstack_id)s.assembly a
            WHERE a.id IN (SELECT id FROM assembly_a)
            """ % {
                'segstack_id': self.test_segstack_id,
                'core_a_id': core_id,
                'segment_a_id': segment_id })
        self.assertTrue(cursor.rowcount >= 1)
        return [x[0] for x in cursor.fetchall()]

    def test_mapped_skeletons(self):
        self.fake_authentication()

        for core_id in [000, 001, 010, 011]:
            response = self.client.post(
                    '/sopnet/%d/segmentation/%d/core/%d/generate_assemblies' % (self.test_project_id, self.test_segstack_id, core_id))
            self.assertEqual(response.status_code, 200)

        core_a_id = 000
        core_b_id = 001
        generate_compatible_assemblies_between_cores(self.test_segstack_id, core_a_id, core_b_id)

        generate_assembly_equivalences(self.test_segstack_id)

        equivalence_id = self.get_assembly_equivalences_for_segment(1000000, 000)[0]

        arborescence = map_assembly_equivalence_to_arborescence(self.test_segstack_id, equivalence_id)
        self.assertEqual(20, arborescence.number_of_nodes())

        response = self.client.post(
                '/sopnet/%d/segmentation/%d/assembly_equivalence/%d/map_to_skeleton' % (self.test_project_id, self.test_segstack_id, equivalence_id))
        self.assertEqual(response.status_code, 200)
        parsed_response = json.loads(response.content)

        treenodes = Treenode.objects.filter(skeleton_id=parsed_response['skeleton_id'])
        self.assertEqual(20, len(treenodes))
