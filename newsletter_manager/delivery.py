"""Review an existing draft before editing or scheduling it."""
from datetime import datetime, timezone
from html import unescape
from .brevo import ProviderError


def schedule_time(value):
    when = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if when.tzinfo is None or when.utcoffset() is None:
        raise ValueError('Schedule requires an explicit timezone offset.')
    if when <= datetime.now(timezone.utc):
        raise ValueError('Schedule must be in the future.')
    return when


def verify_content(remote, issue, html, config):
    lists = remote.get('recipients', {}).get('lists', remote.get('recipients', {}).get('listIds', []))
    ids = [item['id'] if isinstance(item, dict) else item for item in lists]
    checks = [remote.get('subject') == issue['subject'],
              unescape(remote.get('htmlContent', '')).strip() == unescape(html).strip(),
              remote.get('sender', {}).get('email') == config['sender']['email'],
              sorted(ids) == sorted(config['list_ids'])]
    if not all(checks):
        raise ValueError('Remote content, sender or audience differs from the local edition. Review in Brevo before proceeding.')
    recipients = remote.get('recipients', {})
    if recipients.get('segmentIds') or recipients.get('exclusionLists') or recipients.get('exclusionListIds'):
        raise ValueError('Remote audience has additional filters. Review and schedule it directly in Brevo.')


def deliver(provider, command, campaign_id, issue, html, config, apply=False, at=None):
    if campaign_id <= 0:
        raise ValueError('Positive campaign id required')
    when = schedule_time(at) if command == 'schedule' else None
    plan = {'action': command, 'campaign_id': campaign_id, 'subject': issue['subject'],
            'list_ids': config['list_ids'], 'applied': False}
    if when: plan['scheduled_at'] = when.isoformat()
    # Previews are completely offline, including on machines without provider credentials.
    if not apply: return plan
    remote = provider.campaign(campaign_id)
    if remote.get('status') != 'draft' or remote.get('scheduledAt'):
        raise ValueError('Only unscheduled drafts can be changed by this command. Review the campaign in Brevo.')
    if command == 'update':
        provider.update(campaign_id, {'subject': issue['subject'], 'htmlContent': html,
                                     'previewText': issue.get('preheader', '')})
        verify_content(provider.campaign(campaign_id), issue, html, config)
    else:
        verify_content(remote, issue, html, config)
        provider.update(campaign_id, {'scheduledAt': when.isoformat(), 'sendAtBestTime': False})
        result = provider.campaign(campaign_id)
        try:
            confirmed = datetime.fromisoformat(result.get('scheduledAt', '').replace('Z', '+00:00'))
        except ValueError:
            confirmed = None
        if result.get('status') != 'queued' or confirmed != when:
            raise ProviderError('Scheduling outcome is unconfirmed. Check Brevo before retrying; the campaign may already be scheduled.')
    plan['applied'] = True
    return plan
