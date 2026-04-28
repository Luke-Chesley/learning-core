# Repository Guidelines

## Shared Skill Activation
- Use the global Codex skill `learning-cross-repo-workflow` when a task touches `homeschool-v2`, `harnesses/browser-ux`, activity generation, widget/runtime changes, learner activity QA, or cross-repo debugging.
- The canonical skill lives at `/home/luke/.codex/skills/learning-cross-repo-workflow/SKILL.md`. Do not create a repo-local copy of that skill.
- For real browser execution, follow that skill and use the global `playwright` skill instead of repeatedly writing new inline Playwright scripts when repo docs or harness files already cover the flow.
- Some older docs still mention legacy pre-move paths like `/home/luke/Desktop/homeschool-v2` and `/home/luke/Desktop/learning-core`; normalize those to the live workspace under `/home/luke/Desktop/learning/...` unless the filesystem proves otherwise.

## Commands
- Setup:
  `uv venv --python 3.12`
  `uv sync --extra dev`
- Run the API server:
  `uv run learning-core`
- Run the local widget harness:
  `./local_test/run.sh`
- Run tests:
  `uv run pytest -q`

## Cross-Repo Workflow
- `learning-core` owns runtime behavior, contracts, packs, and widget engine logic.
- `homeschool-v2` owns product UI, learner routes, auth/session flow, and browser QA.
- For widget or activity-runtime work, validate in this order:
  1. contracts and generation docs
  2. `widget_transition`
  3. `activity_feedback`
  4. `local_test`
  5. real `homeschool-v2` browser interaction if the product boundary is affected
- Do not stop at unit tests if the widget cannot be rendered and exercised in `local_test`.

## References
- Repo overview:
  `/home/luke/Desktop/learning/learning-core/README.md`
- Widget onboarding:
  `/home/luke/Desktop/learning/learning-core/learning_core/skills/activity_generate/widget_engine_onboarding.md`
- Cross-repo skill:
  `/home/luke/.codex/skills/learning-cross-repo-workflow/SKILL.md`
