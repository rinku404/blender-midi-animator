# Agent brief: read this before working on any plan step

You are executing **one step** of the MIDI Animator v1 plan. A planning session wrote the plan
and will read your report to decide what happens next. Your report matters as much as your code.

## 1. Get your bearings (always)
1. Read, in this order: `CLAUDE.md`, `docs/plan/PLAN.md` (your step and the status board),
   `docs/SPEC.md`, `docs/decisions/` (all records), then any `docs/plan/reports/` for steps your step depends on.
2. Confirm your step's dependencies are ✅ or ⚠️ on the status board. If one isn't, **stop** and write
   a `blocked` report saying which.
3. Check the state of the repo, and note anything surprising in your report.
   ```
   git fetch origin
   git log --oneline -5 origin/v1-rewrite
   ```

## 2. Branch and scope
- Branch from the latest `origin/v1-rewrite` (after v1 is merged: `origin/main`), named
  `plan/step-NN-<slug>`, for example `plan/step-02-hold`.
- Do **only** your step's tasks. If you find work outside it (a bug, a better idea), don't do it.
  Put it in the report under *Follow-ups*. Exception: a tiny fix that blocks your own tests; say so in the report.
- Don't change `docs/plan/PLAN.md`. The planner owns it. Report instead.
- Don't contradict a decision in `docs/decisions/`. If your step truly needs to, write a new ADR that supersedes it,
  and flag it at the top of the report.

## 3. Engineering rules
- `midi_animator/core/` never imports `bpy`. Put any logic that doesn't need Blender there, with pytest tests.
- Blender behaviour gets a check in `tests/test_in_blender.py`, or in a new in-Blender test script the step names.
- Follow `CLAUDE.md` conventions (pose names, marker props, `MIDI:` tracks, written pitch).
- Keep the user-facing guide `docs/aerophone-guide.md` true to the UI you ship.
- Commits end with the attribution lines your environment gives you.

## 4. Verify before you report
Run and record the exact commands and results:
```
python -m pytest tests/core -q
<blender> -b --factory-startup --python tests/test_in_blender.py
<blender> --command extension validate midi_animator
```
Plus any step-specific checks. On this machine, `<blender>` is normally
`"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"`; say which one you used. A step isn't done while
anything fails: report it as `partial` instead.

## 5. Write the report
Create `docs/plan/reports/step-NN-<slug>.md` from [REPORT_TEMPLATE.md](REPORT_TEMPLATE.md), commit it
**in the same branch**, push, and open a PR into `v1-rewrite` titled `Step NN: <title>`, with the report's
summary as the PR description. Be factual: every ticked acceptance criterion needs evidence (a command output,
a number or a file). Don't round "almost" up to "done".

## 6. When you need the user
Only for things only they can do (look at the result in the UI, use their files, make a choice that the spec
leaves open). Ask clearly and briefly, then continue. Record the question and the answer in the report.

## 7. When you're stuck
After two honest attempts at the same problem, stop, write the report with status `blocked` or `partial`,
explain what you tried and what you think is needed, and push it. A clear blocked report beats a guess.
