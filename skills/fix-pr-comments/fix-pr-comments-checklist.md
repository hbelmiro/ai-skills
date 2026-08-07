# Address PR comments — checklist

Execute in order unless step not applicable (state N/A with reason).

## 0. Git (hard rule)

- [ ] **Never** `git commit`, `git push`, `git commit --amend`, `git rebase`,
      `git merge`, `git cherry-pick`, `git pull` when it would merge/rebase, or
      anything that creates commits or updates remotes. Read-only git fine.
      Edits stay in working tree; tell user what to commit or push if
      needed.

## 1. Inputs

- [ ] PR URL (or owner, repo, number) confirmed with user when ambiguous.
- [ ] Local clone same repository as PR (or obtain one).

## 2. Collect review data

- [ ] Run **Phase 1** of [`../pr-review/pr-review-checklist.md`](../pr-review/pr-review-checklist.md) (PR context JSON,
      full diff, comments and inline threads, extra `gh api` when needed).
- [ ] Keep **master list** of actionable items (inline comments, review
      bodies, issue comments—including CodeRabbit and similar bots).

## 3. Triage

- [ ] For each item: fix, skip (with reason), or defer (with reason).

## 4. Plan

- [ ] Present implementation plan to user: what will be fixed (and in
      what order), what will be skipped or deferred, and approach for each
      item (direct edit vs TDD).
- [ ] Follow [`../../prompts/plan/PROMPT.md`](../../prompts/plan/PROMPT.md).
- [ ] **Wait** for user to approve before proceeding to implementation.

## 5. Implement

- [ ] **Branch gate — timing**: Run **once** before first review-driven edit,
      or again after **user** **pushed** and you re-query `gh pr view`. If
      user has **unpushed** commits for this PR, `HEAD` may differ from
      `headRefOid` until they push—do **not** stop for that alone (you do not
      commit or push).
- [ ] **Branch gate — check** (when gate applies): **`git rev-parse HEAD`**
      equals **`headRefOid`**, or **`headRefOid`** is ancestor of **`HEAD`**
      (`git merge-base --is-ancestor <headRefOid> HEAD`) for unpushed user
      commits on top. Values from `gh pr view <url> --json
      headRefOid,headRefName,isCrossRepository` (use `-R baseOwner/baseRepo`
      when PR URL is base repo but head is on fork). When
      `isCrossRepository` is true, confirm clone can reach head commit
      (fork remote / user checkout). Do not fail on branch name ≠ `headRefName`
      when OID/ancestor check passes. **Do not** run `gh pr checkout` yourself.
      Otherwise **stop** and instruct user to check out PR head (for
      example `gh pr checkout <url>`) and try again.
- [ ] Apply **TDD** per [`../tdd/SKILL.md`](../tdd/SKILL.md) when behavior or coverage in play;
      skip full TDD only for clearly non-behavioral nits.
- [ ] Run tests and appropriate static checks after substantive edits.

## 6. Pre-summary generic-review (fresh eyes)

- [ ] Run [`../generic-review/SKILL.md`](../generic-review/SKILL.md) **Review workflow** (steps 1–5) on
      **current** tree using **git**-based full diff (see **Diff acquisition**
      in [`../generic-review/generic-review-checklist.md`](../generic-review/generic-review-checklist.md)); do not skip diff
      acquisition because local edits may have diverged from earlier
      `gh pr diff`.
- [ ] Treat pass as **independent review** (not only re-checking PR
      threads); apply routing, output template, and
      [`../../prompts/review-shared/review-the-review.md`](../../prompts/review-shared/review-the-review.md).
- [ ] **Fix** accepted findings; re-run tests/static checks; **repeat** full
      generic-review workflow until nothing you accept still blocks completion.

## 7. Close out

- [ ] Produce **summary**: every item from master list with outcome
      (fixed / skipped / deferred) and rationale where not fixed.