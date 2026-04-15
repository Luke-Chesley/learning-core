# Agent Feedback Loop For learning-core

This folder is the handoff target for findings coming from the product-loop agents.

Use it to convert scenario and evaluation reports into learning-core work such as:
- operation-routing fixes
- source interpretation improvements
- session generation improvements
- activity generation improvements
- new pack proposals
- contract changes

## What should land here

Stable, actionable briefs:
- why the failure happened
- which operation likely owns it
- which scenario ids prove it
- whether it is a routing problem, prompt problem, or pack problem
- the smallest validation set for confirming the fix

## What should not land here

- vague "AI should be better" feedback
- reports with no scenario ids
- app-only UX complaints
- one-off outputs with no pattern

## Typical flow

1. Product agents generate scenario cards and execution reports.
2. Evaluator scores outputs.
3. Pack Gap Miner or Backlog Synthesizer writes a concise brief here.
4. learning-core changes the smallest likely cause.
5. The same scenario set is rerun to confirm the fix.
