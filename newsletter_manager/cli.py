"""Local-first newsletter workflow. Remote creation always requires --apply."""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from .brevo import Brevo, ProviderError
from .core import load_json, render, collect, validate_provider_config

PROVIDERS = {'brevo': Brevo}


def main(argv=None):
    parser = argparse.ArgumentParser(prog='newsletter-manager')
    parser.add_argument('--config', default='newsletter.json')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('collect', help='Read recent Git history, output evidence JSON')
    p.add_argument('--days', type=int, default=7)
    p = sub.add_parser('render', help='Write HTML and text previews')
    p.add_argument('issue'); p.add_argument('--out', default='output')
    p = sub.add_parser('draft', help='Preview a draft; --apply creates it remotely')
    p.add_argument('issue'); p.add_argument('--apply', action='store_true')
    p.add_argument('--state', default='.newsletter-state.json')
    p = sub.add_parser('test', help='Send a test email to explicitly named recipients')
    p.add_argument('campaign_id', type=int); p.add_argument('--to', required=True, action='append'); p.add_argument('--apply', action='store_true')
    p = sub.add_parser('status'); p.add_argument('campaign_id', type=int)
    args = parser.parse_args(argv)
    try:
        config = load_json(args.config)
        if args.command == 'collect':
            print(json.dumps(collect(config, args.days), indent=2)); return 0
        if args.command in ('render', 'draft'):
            issue = load_json(args.issue)
            html, text = render(issue, config)
            if args.command == 'render':
                out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
                (out / (issue['id'] + '.html')).write_text(html, encoding='utf-8')
                (out / (issue['id'] + '.txt')).write_text(text, encoding='utf-8')
                print(json.dumps({'html': str(out / (issue['id'] + '.html')), 'text': str(out / (issue['id'] + '.txt'))})); return 0
            validate_provider_config(config)
        provider_name = config.get('provider', 'brevo')
        if provider_name not in PROVIDERS:
            raise ValueError('Unknown provider: ' + provider_name)
        provider = PROVIDERS[provider_name]()
        if args.command == 'draft':
            fingerprint = hashlib.sha256(json.dumps({'issue': issue, 'sender': config['sender'], 'lists': config['list_ids'], 'html': html}, sort_keys=True).encode()).hexdigest()
            plan = {'provider': provider_name, 'issue': issue['id'], 'subject': issue['subject'], 'list_ids': config['list_ids'], 'fingerprint': fingerprint}
            if not args.apply:
                print(json.dumps({'action': 'create-draft', 'plan': plan, 'applied': False}, indent=2)); return 0
            state_path = Path(args.state)
            state = load_json(state_path) if state_path.exists() else {}
            key = provider_name + ':' + issue['id']
            if key in state:
                raise ValueError('This issue already has a receipt. Review the recorded campaign or use a new issue id.')
            # Reserve before the network request. Ambiguous outcomes must be reconciled in the dashboard.
            state[key] = {'status': 'pending', **plan}
            save_state(state_path, state)
            result = provider.create_draft(issue, html, config)
            state[key].update(status='created', campaign_id=result['id'])
            save_state(state_path, state)
            print(json.dumps(state[key], indent=2))
        elif args.command == 'test':
            if args.campaign_id <= 0 or any('@' not in email for email in args.to):
                raise ValueError('Positive campaign id and valid test recipient emails required')
            if args.apply:
                provider.send_test(args.campaign_id, args.to)
            print(json.dumps({'action': 'send-test', 'campaign_id': args.campaign_id, 'recipients': args.to, 'applied': args.apply}))
        elif args.command == 'status':
            if args.campaign_id <= 0: raise ValueError('Positive campaign id required')
            print(json.dumps(provider.campaign(args.campaign_id), indent=2))
        return 0
    except (ValueError, OSError, ProviderError) as exc:
        print(str(exc), file=sys.stderr); return 2


def save_state(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as output:
        json.dump(state, output, indent=2)
    os.replace(tmp, path)
