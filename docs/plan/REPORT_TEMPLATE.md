---
step: NN
title: <step title from PLAN.md>
status: done | partial | blocked
branch: plan/step-NN-<slug>
pr: <PR number or URL>
commits: <first..last short hashes>
date: YYYY-MM-DD
blender: <version and path used, or "not run">
tests_core: <e.g. "34 passed">
tests_blender: <e.g. "ALL TESTS PASSED" or the failure line>
decision_changes: none | <ADR numbers added or superseded>
---

# Step NN: <title>

## Summary
Three to six sentences: what was done, what works now, what doesn't.

## Acceptance criteria
Copy each criterion from PLAN.md and give evidence.
- [x] <criterion>: <evidence: command + result, number, file path>
- [ ] <criterion>: <why not, and what's needed>

## Changes
| File | What changed |
|---|---|
| `path` | … |

## Verification
Exact commands and the relevant end of their output.
```
<command>
<output>
```

## Deviations from the plan or spec
What you did differently and why. "None" if none.

## Decisions
New or superseded ADRs, or choices made inside the step's freedom (with the reason).

## Problems and risks
Bugs found, fragile spots, things that worked but felt shaky.

## Follow-ups for the planner
Concrete proposals: new tasks, step changes, re-ordering. One line each, starting with a verb.

## Questions for the user
With the answers if you got them. "None" if none.
