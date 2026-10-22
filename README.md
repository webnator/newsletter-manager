# Newsletter Manager

A small, local-first workflow for recurring newsletters: collect Git evidence, write an edition as JSON, render HTML and plain text, and create a draft in Brevo. No runtime Python dependencies, web app or model subscription required.

Extracted and generalized from a personal weekly newsletter workflow. It does not scrape your inbox, read assistant transcripts or assume a particular brand, directory or contact list.

## Quick start

Python 3.10+ and Git are required. Git is only used by the optional evidence collector.

```sh
git clone https://github.com/webnator/newsletter-manager.git
cd newsletter-manager
python3 -m newsletter_manager --config examples/newsletter.json render examples/issue.json
```

Open `output/issue-001.html` and review the accompanying `.txt`. The example is fully offline. To install a CLI in a virtual environment:

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
newsletter-manager --help
```

## Prepare your own edition

Copy `examples/newsletter.json` to `newsletter.json`, then set publication name, verified Brevo sender, recipient list IDs and a real business/footer address. Copy the issue example to your own edition file. Each section has a title, plain text and an optional HTTP(S) link. Content is escaped automatically; raw HTML and Markdown are not interpreted.

The renderer uses a fluid, table-based HTML layout with inline styles. Browser preview is useful, but does not replace testing in actual email clients. The text file is a standalone artifact; Brevo's campaign endpoint receives the HTML edition.

Add explicit repository paths to `repositories`, then collect supporting evidence:

```sh
python3 -m newsletter_manager collect --days 7 > evidence.json
```

This reads the current Git history of those repositories only. It does not invent copy or infer shipped features from commits. Verify the evidence before writing the edition. Paths in configuration are resolved from the current working directory; absolute paths are simplest.

## Brevo workflow

Set `BREVO_API_KEY` in your environment. The tool never reads keys from another project. Do not commit your key, local configuration or receipts.

```sh
# Prints the plan without contacting Brevo
python3 -m newsletter_manager draft editions/issue-002.json

# Creates a remote draft, never schedules or sends a campaign
python3 -m newsletter_manager draft editions/issue-002.json --apply

# Inspect the returned campaign ID
python3 -m newsletter_manager status 123

# Preview a test-send request, then explicitly send to that address
python3 -m newsletter_manager test 123 --to you@example.com
python3 -m newsletter_manager test 123 --to you@example.com --apply
```

Finish the audience review and actual campaign send in Brevo. There is deliberately no bulk-send command. Brevo creates campaigns in draft status by default; see its [campaign API](https://developers.brevo.com/reference/create-email-campaign) and [test-send API](https://developers.brevo.com/reference/send-test-email). The HTML includes Brevo's unsubscribe placeholder. Verify unsubscribe behavior, sender identity, recipient consent and the footer in a real test before a campaign send.

Receipts are stored in `.newsletter-state.json` with owner-only permissions. Reusing an issue ID is refused, including after a network error whose result is uncertain. Check the Brevo dashboard and reconcile the receipt before retrying. There are no automatic retries for creation or sending. Run one invocation at a time against a state file; this is a local CLI, not a distributed scheduler.

## Extend it

- `core.py`: issue validation, HTML/text rendering and Git evidence collection. Customize the template here or add a renderer with the same `(html, text)` result.
- `brevo.py`: provider HTTP adapter with timeouts and redirects disabled. Implement `create_draft(issue, html, config)`, `send_test(id, recipients)` and `campaign(id)` for another provider.
- `cli.py`: commands and local receipts. Register adapters in `PROVIDERS`, and adapt provider-specific unsubscribe handling before using a different provider.
- Add new evidence sources as explicit collectors that return data. Keep them separate from delivery operations.

A CLI is the simplest distribution for both humans and coding agents. No separate skill installation is required: an agent can run the same preview commands and show the resulting edition before you authorize a remote draft or test email.

## Development and limitations

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q newsletter_manager
```

Tests use mocks and temporary files, never real lists or email sends. Coverage includes escaping, draft payloads, preview behavior, duplicate receipts and uncertain failures. No live Brevo campaign has been created as part of this release validation. No rich-text editor, analytics dashboard, scheduling service or automatic copy generation is included.

MIT licensed.
