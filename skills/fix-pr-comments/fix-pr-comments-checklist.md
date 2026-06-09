# Address PR comments — checklist

Execute in order unless a step is not applicable (state N/A with reason).

## 0. Git (hard rule)

- [ ] **Never** `git commit`, `git push`, `git commit --amend`, `git rebase`,
      `git merge`, `git cherry-pick`, `git pull` when it would merge/rebase, or
      anything that creates commits or updates remotes. Read-only git is fine.
      Edits stay in the working tree; tell the user what to commit or push if
      needed.

## 1. Inputs

- [ ] PR URL (or owner, repo, number) confirmed with the user when ambiguous.
- [ ] Local clone is the same repository as the PR (or obtain one).

## 2. Collect review data

- [ ] Run **Phase 1** of [`../pr-review/pr-review-checklist.md`](../pr-review/pr-review-checklist.md) (PR context JSON,
      full diff, comments and inline threads, extra `gh api` when needed).
- [ ] Keep a **master list** of actionable items (inline comments, review
      bodies, issue comments—including CodeRabbit and similar bots).

## 3. Implement

- [ ] **Branch gate — timing**: Run **once** before the first review-driven edit,
      or again after the **user** **pushed** and you re-query `gh pr view`. If
      the user has **unpushed** commits for this PR, `HEAD` may differ from
      `headRefOid` until they push—do **not** stop for that alone (you do not
      commit or push).
- [ ] **Branch gate — check** (when the gate applies): **`git rev-parse HEAD`**
      equals **`headRefOid`**, or **`headRefOid`** is an ancestor of **`HEAD`**
      (`git merge-base --is-ancestor <headRefOid> HEAD`) for unpushed user
      commits on top. Values from `gh pr view <url> --json
      headRefOid,headRefName,isCrossRepository` (use `-R baseOwner/baseRepo`
      when the PR URL is the base repo but the head is on a fork). When
      `isCrossRepository` is true, confirm the clone can reach the head commit
      (fork remote / user checkout). Do not fail on branch name ≠ `headRefName`
      when OID/ancestor check passes. **Do not** run `gh pr checkout` yourself.
      Otherwise **stop** and instruct the user to check out the PR head (for
      example `gh pr checkout <url>`) and try again.
- [ ] For each item: fix, skip (with reason), or defer (with reason).
- [ ] Apply **TDD** per [`../tdd/SKILL.md`](../tdd/SKILL.md) when behavior or coverage is in play;
      skip full TDD only for clearly non-behavioral nits.
- [ ] Run tests and appropriate static checks after substantive edits.

## 4. Pre-summary generic-review (fresh eyes)

- [ ] Run [`../generic-review/SKILL.md`](../generic-review/SKILL.md) **Review workflow** (steps 1–6) on the
      **current** tree using a **git**-based full diff (see **Diff acquisition**
      in [`../generic-review/generic-review-checklist.md`](../generic-review/generic-review-checklist.md)); do not skip diff
      acquisition because local edits may have diverged from an earlier
      `gh pr diff`.
- [ ] Treat the pass as **independent review** (not only re-checking PR
      threads); apply routing, severity, output template, and
      [`../../prompts/review-shared/review-the-review.md`](../../prompts/review-shared/review-the-review.md).
- [ ] **Fix** accepted findings; re-run tests/static checks; **repeat** the full
      generic-review workflow until nothing you accept still blocks completion.

## 5. Close out

- [ ] Produce the **summary**: every item from the master list with outcome
      (fixed / skipped / deferred) and rationale where not fixed.
