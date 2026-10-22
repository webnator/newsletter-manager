import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from newsletter_manager.core import render, validate_provider_config
from newsletter_manager.cli import main
from newsletter_manager.brevo import Brevo, ProviderError

CONFIG = {'publication': 'Example', 'footer': 'Example address', 'sender': {'email': 'editor@example.com'}, 'list_ids': [42]}
ISSUE = {'id': 'issue-1', 'subject': 'News', 'sections': [{'title': '<script>', 'text': 'A & B', 'url': 'https://example.com'}]}


class Workflow(unittest.TestCase):
    def test_render_escapes_content_and_rejects_unsafe_links(self):
        html, text = render(ISSUE, CONFIG)
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('{{ unsubscribe }}', html)
        self.assertIn('A & B', text)
        bad = {**ISSUE, 'sections': [{'title': 'x', 'text': 'x', 'url': 'javascript:alert(1)'}]}
        with self.assertRaises(ValueError): render(bad, CONFIG)
        with self.assertRaises(ValueError): validate_provider_config({**CONFIG, 'list_ids': [True]})

    def test_draft_preview_never_calls_provider_and_receipt_blocks_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            config, issue, state = [Path(tmp) / name for name in ['config.json', 'issue.json', 'state.json']]
            config.write_text(json.dumps(CONFIG)); issue.write_text(json.dumps(ISSUE))
            args = ['--config', str(config), 'draft', str(issue), '--state', str(state)]
            with patch.object(Brevo, 'create_draft', return_value={'id': 99}) as create, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(args), 0); create.assert_not_called()
                self.assertEqual(main(args + ['--apply']), 0)
                self.assertEqual(main(args + ['--apply']), 2)
                self.assertEqual(create.call_count, 1)
                self.assertEqual(json.loads(state.read_text())['brevo:issue-1']['campaign_id'], 99)

    def test_ambiguous_failure_keeps_pending_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            config, issue, state = [Path(tmp) / name for name in ['config.json', 'issue.json', 'state.json']]
            config.write_text(json.dumps(CONFIG)); issue.write_text(json.dumps(ISSUE))
            args = ['--config', str(config), 'draft', str(issue), '--state', str(state), '--apply']
            with patch.object(Brevo, 'create_draft', side_effect=ProviderError('timeout')), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(args), 2)
            self.assertEqual(json.loads(state.read_text())['brevo:issue-1']['status'], 'pending')

    def test_brevo_payload_is_draft_and_test_requires_recipients(self):
        provider = Brevo('fake-test-key')
        with patch.object(provider, 'call', return_value={'id': 9}) as call:
            provider.create_draft(ISSUE, '<p>Hello</p>', CONFIG)
            path, method, payload = call.call_args.args
            self.assertEqual((path, method), ('/emailCampaigns', 'POST'))
            self.assertEqual(payload['recipients'], {'listIds': [42]})
            self.assertNotIn('scheduledAt', payload)
            with self.assertRaises(ProviderError): provider.send_test(9, [])
            provider.send_test(9, ['tester@example.com'])
            self.assertEqual(call.call_args.args[0], '/emailCampaigns/9/sendTest')


if __name__ == '__main__': unittest.main()
