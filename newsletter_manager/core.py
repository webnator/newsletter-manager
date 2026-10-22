"""Provider-independent issue validation, rendering and evidence collection."""
import html
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def validate(issue, config):
    for key in ('id', 'subject'):
        if not isinstance(issue.get(key), str) or not issue[key].strip():
            raise ValueError(f'Issue requires {key}')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', issue['id']):
        raise ValueError('Issue id must be a simple filename-safe identifier')
    if not isinstance(issue.get('sections'), list) or not issue['sections']:
        raise ValueError('Issue requires at least one section')
    for section in issue['sections']:
        if not isinstance(section.get('title'), str) or not isinstance(section.get('text'), str):
            raise ValueError('Each section requires title and text strings')
        if section.get('url') and urlparse(section['url']).scheme not in ('http', 'https'):
            raise ValueError('Section links must use HTTP or HTTPS')
    if not config.get('publication') or not config.get('footer'):
        raise ValueError('Configuration requires publication and footer')


def validate_provider_config(config):
    sender = config.get('sender', {})
    if not isinstance(sender, dict) or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', sender.get('email', '')):
        raise ValueError('Configure a verified sender.email')
    ids = config.get('list_ids')
    if not isinstance(ids, list) or not ids or any(type(x) is not int or x <= 0 for x in ids):
        raise ValueError('Configure one or more positive list_ids')


def render(issue, config, unsubscribe='{{ unsubscribe }}'):
    validate(issue, config)
    e = html.escape
    sections = []
    plain = [config['publication'], issue['subject'], '']
    for section in issue['sections']:
        paragraphs = ''.join('<p style="line-height:1.6">' + e(p).replace('\n', '<br>') + '</p>' for p in section['text'].split('\n\n'))
        link = f'<p><a href="{e(section["url"], quote=True)}">Read more</a></p>' if section.get('url') else ''
        sections.append(f'<tr><td style="padding:12px 28px"><h2>{e(section["title"])}</h2>{paragraphs}{link}</td></tr>')
        plain += [section['title'], section['text'], section.get('url', ''), '']
    body = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(issue['subject'])}</title></head>
<body style="margin:0;background:#f4f4f1;font-family:Arial,sans-serif;color:#202322">
<div style="display:none;max-height:0;overflow:hidden">{e(issue.get('preheader', ''))}</div>
<table role="presentation" width="100%"><tr><td align="center"><table role="presentation" width="100%" style="max-width:640px;background:white">
<tr><td style="padding:28px"><p>{e(config['publication'])}</p><h1>{e(issue['subject'])}</h1></td></tr>
{''.join(sections)}<tr><td style="padding:28px;color:#666"><p>{e(config['footer'])}</p><a href="{e(unsubscribe, quote=True)}">Unsubscribe</a></td></tr>
</table></td></tr></table></body></html>'''
    plain += [config['footer'], 'Unsubscribe: ' + unsubscribe]
    return body, '\n'.join(plain)


def collect(config, days=7):
    if not 1 <= days <= 365:
        raise ValueError('days must be between 1 and 365')
    evidence = []
    for repository in config.get('repositories', []):
        result = subprocess.run(['git', 'log', f'--since={days} days ago', '--date=iso-strict', '--format=%H%x09%ad%x09%s'], cwd=Path(repository).expanduser(), capture_output=True, text=True, timeout=30, check=True)
        for line in result.stdout.splitlines():
            sha, date, subject = line.split('\t', 2)
            evidence.append({'repository': Path(repository).name, 'commit': sha, 'date': date, 'subject': subject})
    return evidence
