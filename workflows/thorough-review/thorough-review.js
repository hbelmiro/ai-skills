export const meta = {
  name: 'thorough-review',
  description: 'Fan-out parallel reviewers with adversarial verification of each finding',
  phases: [
    { title: 'Review', detail: 'Go, Python, and generic reviewers in parallel' },
    { title: 'Verify', detail: 'Skeptic agent per finding — verify and correct' },
    { title: 'Write', detail: 'Merge survivors and format output' },
  ],
}

// ---------------------------------------------------------------------------
// Structured output schemas
// ---------------------------------------------------------------------------

const FINDINGS_SCHEMA = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          file:         { type: 'string', description: 'Path to the file' },
          line:         { type: 'integer', description: 'Line number in the current file' },
          title:        { type: 'string', description: 'One-line summary of the issue' },
          description:  { type: 'string', description: 'Detailed explanation of the issue' },
          suggestedFix: { type: 'string', description: 'Concrete remediation with code if applicable' },
          whyItMatters: { type: 'string', description: 'Impact and risk (omit if self-evident)' },
        },
        required: ['file', 'line', 'title', 'description'],
      },
    },
  },
  required: ['findings'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    survives:             { type: 'boolean', description: 'true if the finding is real and should be reported' },
    reasoning:            { type: 'string', description: 'Why the finding survives, was corrected, or was refuted' },
    correctedFile:        { type: 'string', description: 'Corrected file path if the original was wrong' },
    correctedLine:        { type: 'integer', description: 'Corrected line number if the original was wrong' },
    correctedDescription: { type: 'string', description: 'Corrected description if the original was inaccurate' },
  },
  required: ['survives', 'reasoning'],
}

const REVIEW_OUTPUT_SCHEMA = {
  type: 'object',
  properties: {
    formattedReview: { type: 'string', description: 'The complete formatted review output' },
  },
  required: ['formattedReview'],
}

// ---------------------------------------------------------------------------
// Dependency files — bundled by `striatum pack` from Prompt dependencies
// declared in artifact.json, installed to deps/ by `striatum install`.
// See: https://github.com/hbelmiro/striatum/issues/77
//
// generic-review-checklist is embedded because generic-review is a Skill
// (not a Prompt), so striatum does not bundle it.
// ---------------------------------------------------------------------------

const DEPS = '~/.claude/workflows/thorough-review/deps'

const GENERIC_CHECKLIST = `
## Generic Review Checklist

- Review the full diff before reporting findings.
- Build hypotheses only after the full-diff pass.
- Avoid selective confirmation from isolated snippets.
- Inspect impacted call paths and cross-file effects, not only edited lines.
- For high-impact claims, look for disconfirming evidence in nearby call paths or tests.
- Prioritize security, data integrity, reliability, and compatibility risks first.
- Verify tests cover changed behavior, edge cases, and failure paths.
- Challenge happy-path assumptions by checking at least one adversarial scenario.
- Explicitly answer: "Do tests cover enough scenarios?"
`

// ---------------------------------------------------------------------------
// Phase 1: Review — parallel fan-out
// ---------------------------------------------------------------------------

phase('Review')

const diff = args

const READ_SHARED_DEPS = `Before starting, read this review criteria file:
- ${DEPS}/review-shared/general-review-requirements.md
Apply the requirements from that file to your review.`

const REVIEWER_BASE_PROMPT = `You are an expert code reviewer. You will review a diff for correctness, security, reliability, and test coverage issues.

${READ_SHARED_DEPS}

Return your findings as structured data. Only include findings where you have concrete evidence of an issue. Do not include speculative concerns or stylistic nitpicks unless they materially increase defect risk.

If you find no issues, return an empty findings array.

Here is the diff to review:

${diff}`

const reviewers = [
  {
    key: 'go',
    prompt: `${REVIEWER_BASE_PROMPT}

Also read: ${DEPS}/go-code-review/go-review-checklist.md

Focus specifically on Go code in this diff. Skip files that are not Go.
If there are no Go files in the diff, return an empty findings array.`,
  },
  {
    key: 'python',
    prompt: `${REVIEWER_BASE_PROMPT}

Also read: ${DEPS}/python-code-review/python-review-checklist.md

Focus specifically on Python code in this diff. Skip files that are not Python.
If there are no Python files in the diff, return an empty findings array.`,
  },
  {
    key: 'generic',
    prompt: `${REVIEWER_BASE_PROMPT}

Review ALL files in this diff for language-agnostic issues: architecture, error handling patterns, test coverage gaps, security, data integrity, and cross-file consistency. Do not duplicate language-specific checks that Go or Python reviewers would catch — focus on cross-cutting concerns.

${GENERIC_CHECKLIST}`,
  },
]

// ---------------------------------------------------------------------------
// Phase 2: Verify — adversarial skeptic per finding
// Pipeline: each reviewer's findings flow to verification immediately.
// ---------------------------------------------------------------------------

const results = await pipeline(
  reviewers,
  (reviewer) => agent(reviewer.prompt, {
    label: `review:${reviewer.key}`,
    phase: 'Review',
    schema: FINDINGS_SCHEMA,
  }),
  (review, reviewer) => {
    if (!review || !review.findings || review.findings.length === 0) {
      log(`${reviewer.key} reviewer: no findings`)
      return []
    }
    log(`${reviewer.key} reviewer: ${review.findings.length} finding(s) — verifying`)
    return parallel(
      review.findings.map((f, i) => () =>
        agent(
          `You are a skeptical code reviewer. Your job is to VERIFY the following finding and CORRECT any inaccurate details.

Read the actual source code at the file and line referenced. Check whether the claimed issue actually exists in the code. Consider:
- Is the file path correct? If not, find the right file and return it as correctedFile.
- Is the line number correct? If the issue exists but at a different line, return the correct line as correctedLine.
- Does the code actually behave as the finding claims? If the description is inaccurate but the underlying issue is real, return a corrected version as correctedDescription.
- Is there context (tests, callers, configuration) that makes this a non-issue?

If the issue is real but details are wrong, set survives=true and provide corrections. Only set survives=false when the issue genuinely does not exist or is already handled.

Finding to verify:
- File: ${f.file}
- Line: ${f.line}
- Title: ${f.title}
- Description: ${f.description}
${f.suggestedFix ? `- Suggested fix: ${f.suggestedFix}` : ''}`,
          {
            label: `verify:${reviewer.key}:${i}`,
            phase: 'Verify',
            schema: VERDICT_SCHEMA,
          }
        ).then((verdict) => {
          if (!verdict) return null
          return {
            ...f,
            file: verdict.correctedFile || f.file,
            line: verdict.correctedLine || f.line,
            description: verdict.correctedDescription || f.description,
            reviewer: reviewer.key,
            verdict,
          }
        })
      )
    )
  },
)

// ---------------------------------------------------------------------------
// Collect survivors
// ---------------------------------------------------------------------------

const allVerified = results
  .flat()
  .filter(Boolean)

const survivors = allVerified.filter(
  (f) => f.verdict && f.verdict.survives
)
const refuted = allVerified.filter(
  (f) => f.verdict && !f.verdict.survives
)

log(`Verified: ${allVerified.length} total, ${survivors.length} survived, ${refuted.length} refuted`)

// ---------------------------------------------------------------------------
// Phase 3: Write — merge and format
// ---------------------------------------------------------------------------

phase('Write')

if (survivors.length === 0) {
  log('No surviving findings — review is clean')
  return { formattedReview: 'No issues found after thorough review with adversarial verification.', survivors: [], refuted }
}

const findingsList = survivors.map((f, i) => {
  const num = i + 1
  const whyLine = f.whyItMatters ? `\n\n**Why it matters:** ${f.whyItMatters}` : ''
  const fixLine = f.suggestedFix ? `\n\n**Suggested fix:** ${f.suggestedFix}` : ''
  return `### Comment ${num}

File: \`${f.file}\`
Line: \`${f.line}\`

${f.description}${whyLine}${fixLine}

*Verified by skeptic agent (${f.reviewer} reviewer). Verdict: ${f.verdict.reasoning}*`
}).join('\n\n')

const synthesisPrompt = `You are a senior code reviewer producing the final review output.

Before starting, read this file:
- ${DEPS}/review-shared/output-template.md — output format to follow

You have a set of findings that have been independently verified and corrected by skeptic agents. Your job is to:

1. Re-read the diff to verify line numbers and file paths are still accurate.
2. Check for duplicate findings (same issue raised by different reviewers). Merge duplicates, keeping the most detailed description.
3. Re-number the findings sequentially after deduplication.
4. Format the output following the output template.
5. Return the complete formatted review.

Here is the diff that was reviewed:

${diff}

Here are the verified findings:

${findingsList}

Produce the final review output. Include all verified findings (after dedup) and fill in the Coverage Check and Change Summary sections based on your reading of the diff.`

const synthesis = await agent(synthesisPrompt, {
  label: 'synthesize',
  phase: 'Write',
  schema: REVIEW_OUTPUT_SCHEMA,
})

if (synthesis && synthesis.formattedReview) {
  log('Review complete')
  return { formattedReview: synthesis.formattedReview, survivors, refuted }
}

return { formattedReview: findingsList, survivors, refuted }
