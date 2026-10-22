---
name: newsletter-manager
description: Prepare a recurring newsletter from project evidence, ask focused editorial questions, render a reviewable edition, send a Brevo test and schedule the approved campaign. Use when the user wants to write, revise, preview or schedule their newsletter.
---

# Newsletter Manager

Use the installed `newsletter-manager` CLI or `python3 -m newsletter_manager` from its checkout. Run `--help` when unsure. This skill coordinates editorial work; the CLI handles deterministic rendering and delivery. Configuration, audiences and brand voice belong to the user's project.

## 1. Gather evidence

Read the configured publication, audience, editorial notes and previous edition. Run `newsletter-manager collect --days 7` for the explicitly configured repositories. If the user provides notes, support conversations or release links, include relevant evidence from those sources. Do not scan unrelated projects or inboxes.

List 3 to 5 potential stories with their sources. Separate shipped work, experiments and plans. Commits alone do not prove deployment or customer adoption. Avoid repeating the previous issue unless there is a meaningful update.

Ask at most 3 or 4 focused questions about missing facts: what changed for readers, what failed, what was learned, and what they can try. Never invent results or testimonials.

## 2. Write and render

Follow the publication's voice. Prefer concrete observations over promotional language. Default to 200 to 400 words unless instructed otherwise. Create a unique issue JSON matching `examples/issue.json`, then render it. Inspect the HTML in narrow and wide layouts and review the text version. Check links, sender, footer, unsubscribe placeholder and audience configuration.

Present the subject and complete edition for review. Apply requested edits without rewriting unrelated sections.

## 3. Create and test

Preview `draft ISSUE`, then use `draft ISSUE --apply` when authorized to create the remote draft. Retain its campaign ID and local receipt. Send only to explicitly agreed test recipients using `test ID --to EMAIL --apply`.

For revisions, render again and use `update ID ISSUE --apply`; send another test if requested. A test-send response confirms a request, not inbox delivery. Ask the user to inspect the actual email before scheduling.

## 4. Schedule the approved edition

Confirm the exact edition, recipient list, date, local time and timezone. Use an offset-aware ISO timestamp. Preview `schedule ID ISSUE --at TIMESTAMP`; only use `--apply` after explicit approval to schedule that edition. Scheduling causes a future audience-wide send.

The CLI checks remote content, sender and audience, then verifies the queued status and scheduled time. Report only confirmed state. If a request fails or confirmation is missing, inspect `status ID` and the dashboard before any retry. Never create a replacement campaign just because a network response was lost.

Record the campaign ID, approved subject, evidence sources and confirmed schedule in the project's newsletter log. Do not record API keys. Metrics belong to later follow-up and must come from provider data, not assumptions.
