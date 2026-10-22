import unittest
from unittest.mock import Mock
from newsletter_manager.delivery import deliver, schedule_time
from newsletter_manager.brevo import ProviderError

class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.provider = Mock()
        self.issue = {'subject': 'Weekly update'}
        self.config = {'sender': {'email': 'editor@example.com'}, 'list_ids': [12]}
        self.remote = {'status': 'draft', 'subject': 'Weekly update', 'htmlContent': '<p>Hello</p>', 'sender': self.config['sender'], 'recipients': {'lists': [12]}}

    def call(self, **kwargs):
        return deliver(self.provider, 'schedule', 5, self.issue, '<p>Hello</p>', self.config, at='2099-01-01T10:00:00+01:00', **kwargs)

    def test_preview_has_no_network(self):
        self.assertFalse(self.call()['applied'])
        self.assertEqual(self.provider.mock_calls, [])

    def test_invalid_dates(self):
        for date in ('2099-01-01T10:00:00', '2000-01-01T10:00:00Z'):
            with self.assertRaises(ValueError): schedule_time(date)

    def test_changed_audience_blocks_schedule(self):
        self.remote['recipients']['lists'] = [99]
        self.provider.campaign.return_value = self.remote
        with self.assertRaises(ValueError): self.call(apply=True)
        self.provider.update.assert_not_called()

    def test_queue_is_verified_in_equivalent_timezone(self):
        self.provider.campaign.side_effect = [self.remote, {'status': 'queued', 'scheduledAt': '2099-01-01T09:00:00Z'}]
        self.assertTrue(self.call(apply=True)['applied'])
        self.provider.update.assert_called_once()

    def test_uncertain_result_is_not_retried(self):
        self.provider.campaign.side_effect = [self.remote, {'status': 'draft'}]
        with self.assertRaises(ProviderError): self.call(apply=True)
        self.provider.update.assert_called_once()

    def test_update_verifies_content(self):
        self.provider.campaign.side_effect = [self.remote, self.remote]
        result = deliver(self.provider, 'update', 5, self.issue, '<p>Hello</p>', self.config, True)
        self.assertTrue(result['applied'])
