import json
import urllib

from .common import CatmaidApiTestCase


class DatastoresApiTests(CatmaidApiTestCase):
    def test_client_datastores(self):
        url = '/client/datastores/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        parsed_response = json.loads(response.content)
        self.assertTrue(parsed_response['permission_error'])

        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        parsed_response = json.loads(response.content)
        self.assertTrue(parsed_response['permission_error'])

        # Test basic datastore creation.
        self.fake_authentication()
        name = 'test-  %% datastore'
        response = self.client.post(url, {'name': name})
        self.assertEqual(response.status_code, 200)
        parsed_response = json.loads(response.content)
        self.assertTrue('error' in parsed_response)
        name = 'test-datastore'
        response = self.client.post(url, {'name': name})
        self.assertEqual(response.status_code, 200)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        parsed_response = json.loads(response.content)
        parsed_response = [p for p in parsed_response if p['name'] == name]
        self.assertEqual(len(parsed_response), 1)
        response = self.client.delete(url + name)
        self.assertEqual(response.status_code, 403)

        # Create data entries.
        url = url + name + '/'
        response = self.client.put(
                url,
                urllib.urlencode({
                    'key': 'test a',
                    'value': '{"json": false'}),
                content_type='application/x-www-form-urlencoded')
        self.assertEqual(response.status_code, 400)
        parsed_response = json.loads(response.content)
        response = self.client.put(
                url,
                urllib.urlencode({
                    'key': 'test a',
                    'value': '{"json": true, "scope": "user-instance"}'}),
                content_type='application/x-www-form-urlencoded')
        self.assertEqual(response.status_code, 200)
        parsed_response = json.loads(response.content)
        self.assertFalse('error' in parsed_response)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        parsed_response = json.loads(response.content)
        self.assertEqual(len(parsed_response), 1)
        self.assertEqual(parsed_response[0]['key'], 'test a')

        # Test that PUTting the same key replaces the value.
        response = self.client.put(
                url,
                urllib.urlencode({
                    'key': 'test a',
                    'value': '{"json": true, "scope": "user-instance", "replaced": true}'}),
                content_type='application/x-www-form-urlencoded')
        self.assertEqual(response.status_code, 204)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        parsed_response = json.loads(response.content)
        self.assertEqual(len(parsed_response), 1)
        value = parsed_response[0]['value']
        self.assertTrue(value['replaced'])

        response = self.client.put(
                url,
                urllib.urlencode({
                    'key': 'test a',
                    'project_id': self.test_project_id,
                    'value': '{"json": true, "scope": "user-project"}'}),
                content_type='application/x-www-form-urlencoded')
        self.assertEqual(response.status_code, 200)
        parsed_response = json.loads(response.content)
        self.assertFalse('error' in parsed_response)
        # Omitting project ID should return only global and user-instance keys.
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        parsed_response = json.loads(response.content)
        self.assertEqual(len(parsed_response), 1)
        response = self.client.get(url, {'project_id': self.test_project_id})
        self.assertEqual(response.status_code, 200)
        parsed_response = json.loads(response.content)
        self.assertEqual(len(parsed_response), 2)
        self.assertEqual(parsed_response[0]['key'], 'test a')
        self.assertEqual(parsed_response[1]['key'], 'test a')

        # Test that a non-admin user cannot change global data.
        response = self.client.put(
                url,
                urllib.urlencode({
                    'key': 'test a',
                    'ignore_user': 'true',
                    'value': '{"json": true, "scope": "global-instance"}'}),
                content_type='application/x-www-form-urlencoded')
        self.assertEqual(response.status_code, 403)

        response = self.client.put(
                url,
                urllib.urlencode({
                    'key': 'test a',
                    'ignore_user': 'true',
                    'project_id': self.test_project_id,
                    'value': '{"json": true, "scope": "global-instance"}'}),
                content_type='application/x-www-form-urlencoded')
        self.assertEqual(response.status_code, 403)
