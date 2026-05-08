# Review and fix — checklist

Execute in order unless a step is not applicable (state N/A with reason).

## 0. Git (hard rule)

- [ ] **Never** `git commit`, `git push`, `git commit --amend`, `git rebase`,
      `git merge`, `git cherry-pick`, `git pull` when it would merge/rebase, or
      anything that creates commits or updates remotes. Read-only git is fine.
      Edits stay in the working tree; tell the user what to commit or push if
      needed.

## 1. Review (fresh eyes)

- [ ] Run `../generic-review/SKILL.md` **Review workflow** (steps 1–6) on the
      **current** tree using a **git**-based full diff (see **Diff acquisition**
      in `../generic-review/generic-review-checklist.md`).
- [ ] Treat the pass as **independent review**; apply routing, severity, output
      template, and `../review-shared/review-the-review.md`.

## 2. Decision gate

- [ ] If the review produced **accepted findings** → proceed to step 3.
- [ ] If **no issues** remain → skip to step 4.

## 3. Fix and loop

- [ ] **Fix** every accepted finding.
- [ ] Apply **TDD** per `../tdd/SKILL.md` (phases A–G) when behavior or
      coverage is in play; skip full TDD only for clearly non-behavioral nits.
- [ ] Re-run tests and appropriate static checks after substantive edits.
- [ ] **Return to step 1** with a fresh git diff; repeat until the review
      produces no remaining issues that block completion.

## 4. Save clean review

- [ ] Create `<project>/.hbelmiro/reviews/` directory if it does not exist.
- [ ] Add `.hbelmiro/` to `<project>/.git/info/exclude` if not already present.
- [ ] Write the final clean review output to
      `<project>/.hbelmiro/reviews/<YYYY-MM-DD-HHmmss>-review.md`.
