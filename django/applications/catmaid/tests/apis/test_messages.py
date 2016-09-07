import json

from catmaid.models import Message

from .common import CatmaidApiTestCase


class MessagesApiTests(CatmaidApiTestCase):
    def test_read_message_error(self):
        self.fake_authentication()
        message_id = 5050

        response = self.client.get('/messages/mark_read', {'id': message_id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Could not retrieve message with id %s' % message_id)


    def test_read_message_without_action(self):
        self.fake_authentication()
        message_id = 3

        response = self.client.get('/messages/mark_read', {'id': message_id})
        self.assertEqual(response.status_code, 200)
        message = Message.objects.get(id=message_id)
        self.assertEqual(True, message.read)
        self.assertContains(response, 'history.back()', count=2)


    def test_read_message_with_action(self):
        self.fake_authentication()
        message_id = 1

        response = self.client.get('/messages/mark_read', {'id': message_id})
        self.assertEqual(response.status_code, 200)
        message = Message.objects.filter(id=message_id)[0]
        self.assertEqual(True, message.read)
        self.assertContains(response, 'location.replace')
        self.assertContains(response, message.action, count=2)


    def test_list_messages(self):
        self.fake_authentication()

        response = self.client.post(
                '/messages/list', {})
        self.assertEqual(response.status_code, 200)
        parsed_response = json.loads(response.content)

        def get_message(data, id):
            msgs = [d for d in data if d['id'] == id]
            if len(msgs) != 1:
                raise ValueError("Malformed message data")
            return msgs[0]

        expected_result = {
                '0': {
                    'action': '',
                    'id': 3,
                    'text': 'Contents of message 3.',
                    'time': '2014-10-05 11:12:01.360422+00:00',
                    'title': 'Message 3'
                },
                '1': {
                    'action': 'http://www.example.com/message2',
                    'id': 2,
                    'text': 'Contents of message 2.',
                    'time': '2011-12-20 16:46:01.360422+00:00',
                    'title': 'Message 2'
                },
                '2': {
                    'action': 'http://www.example.com/message1',
                    'id': 1,
                    'text': 'Contents of message 1.',
                    'time': '2011-12-19 16:46:01+00:00',
                    'title': 'Message 1'
                },
                '3': {
                    'id': -1,
                    'notification_count': 0
                }
        }
        # Check result independent from order
        for mi in ('0','1','2','3'):
            self.assertEqual(expected_result[mi], parsed_response[mi])
