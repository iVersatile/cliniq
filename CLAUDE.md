# cliniq — Project Ground Rules

These rules govern all development work on this project.
They override general Claude Code defaults where they conflict.

---

## 1. "go" Command

When user says **go**:
1. Read `PLAN.md` — identify current in-progress task (first unchecked box in the active phase)
2. Implement it
3. Run all local tests; ensure green
4. Commit + push; wait for remote CI green
5. Mark task checkbox complete in `PLAN.md`
6. Mark the next task checkbox as in-progress
7. Report to user: what was done, what is next

---

## 2. Pre-Commit Gate

Before every commit, run locally in order:
```
ruff check src/ tests/
ruff format --check src/ tests/
mypy src/cliniq
pytest tests/ --cov=cliniq --cov-fail-under=80
```
All four must pass. Do not commit if any fail. Fix first.

---

## 3. Pre-Push Gate

Before pushing local commits to remote:
- Confirm all local tests pass (re-run pytest if in doubt)
- No uncommitted changes in working tree
- No PHI, real patient names, NHS numbers, or API keys in diff

---

## 4. LESSONS_LEARNT.md

File lives at `docs/LESSONS_LEARNT.md`.

- **At every bug fix or regression:** cross-check this file before writing any code — an existing lesson may apply
- **On user "add lesson" command:** document the issue + root cause + solution as a new entry (append, do not edit existing entries)
- Format: `## LL-NNN — <short title>` with date, symptom, root cause, fix, prevention note

---

## 5. Git Tagging — Version Gate

Before proposing or applying a new version tag:
1. Verify remote CI is green on `main` (check GitHub Actions)
2. Review what changed since last tag
3. Suggest next version number with rationale (semver: patch/minor/major and why)
4. Wait for user approval before creating the tag

---

## 6. Phase Start Gate

Before beginning any new phase in `PLAN.md`:
1. Verify remote CI is green on `main`
2. Run code review across changed files: quality, security, performance
3. Present findings + improvement options to user
4. Wait for user approval before starting phase work

---

## 7. Phase Done Gate

Before marking a phase complete in `PLAN.md`:
1. All task checkboxes in the phase are checked
2. Exit criteria documented in `PLAN.md` for that phase are met
3. Remote CI is green
4. **Ask user for explicit approval** — do not self-approve phase completion

---

## 8. General Constraints (inherited)

- No PHI in logs, commits, or CI output at any verbosity level
- No hardcoded API keys, tokens, or credentials
- No `--dangerously-skip-permissions`, `--no-verify`, or `sudo`
- CPU-only — do not introduce GPU-only dependencies
