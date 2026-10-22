"""Small Brevo adapter using the Python standard library."""
import json
import os
import urllib.error
import urllib.request


class ProviderError(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Brevo:
    def __init__(self, key=None, opener=None):
        self.key = key or os.environ.get('BREVO_API_KEY')
        self.opener = opener or urllib.request.build_opener(NoRedirect())

    def call(self, path, method='GET', body=None):
        if not self.key:
            raise ProviderError('Set BREVO_API_KEY in your environment.')
        req = urllib.request.Request(
            'https://api.brevo.com/v3' + path, method=method,
            headers={'api-key': self.key, 'Content-Type': 'application/json', 'Accept': 'application/json'},
            data=json.dumps(body).encode() if body is not None else None)
        try:
            with self.opener.open(req, timeout=30) as response:
                raw = response.read(2_000_001)
                if len(raw) > 2_000_000:
                    raise ProviderError('Provider response exceeded 2 MB')
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            # Do not echo provider bodies, which can contain addresses or credentials.
            raise ProviderError(f'Brevo returned HTTP {exc.code} for {method} {path}; check the dashboard.') from None
        except urllib.error.URLError as exc:
            raise ProviderError('Brevo request failed; check network connectivity. No automatic retry was made.') from exc

    def create_draft(self, issue, html, config):
        return self.call('/emailCampaigns', 'POST', {
            'name': issue['id'], 'subject': issue['subject'], 'type': 'classic',
            'sender': config['sender'], 'htmlContent': html,
            'previewText': issue.get('preheader', ''),
            'recipients': {'listIds': config['list_ids']}})

    def send_test(self, campaign_id, emails):
        if not emails:
            raise ProviderError('At least one explicit test recipient is required.')
        return self.call(f'/emailCampaigns/{int(campaign_id)}/sendTest', 'POST', {'emailTo': emails})

    def campaign(self, campaign_id):
        return self.call(f'/emailCampaigns/{int(campaign_id)}')

    def update(self, campaign_id, payload):
        return self.call(f'/emailCampaigns/{int(campaign_id)}', 'PUT', payload)
