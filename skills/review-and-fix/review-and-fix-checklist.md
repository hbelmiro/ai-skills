# Review and fix — checklist

Execute in order. If step not applicable, state N/A with reason.

## 0. Git (hard rule)

- [ ] **Never** `git commit`, `git push`, `git commit --amend`, `git rebase`, `git merge`, `git cherry-pick`, `git pull` when merge/rebase, or anything that creates commits or updates remotes. Read-only git fine. Edits stay in working tree; tell user what commit or push if needed.

## 1. Review (fresh eyes)

- [ ] Run [`../generic-review/SKILL.md`](../generic-review/SKILL.md) **Review workflow** (steps 1–5) on **current** tree using **git**-based full diff (see **Diff acquisition** in [`../generic-review/generic-review-checklist.md`](../generic-review/generic-review-checklist.md)).
- [ ] Treat pass as **independent review**; apply routing, output template, and [`../../prompts/review-shared/review-the-review.md`](../../prompts/review-shared/review-the-review.md).

## 2. Decision gate

- [ ] If review produced **accepted findings** → proceed to step 3.
- [ ] If **no issues** remain → workflow complete; present clean review output to user.

## 3. Plan

- [ ] Present fix plan to user: which findings fix, in what order, and approach (direct edit vs TDD).
- [ ] Follow [`../../prompts/plan/PROMPT.md`](../../prompts/plan/PROMPT.md).
- [ ] **Wait** for user approve before proceed to fixes.

## 4. Fix and loop

- [ ] **Fix** every accepted finding.
- [ ] Apply **TDD** per [`../tdd/SKILL.md`](../tdd/SKILL.md) (phases A–G) when behavior or coverage in play; skip full TDD only for clearly non-behavioral nits.
- [ ] Re-run tests and appropriate static checks after substantive edits.
- [ ] **Return to step 1** with fresh git diff; repeat until review produces no remaining issues that block completion.