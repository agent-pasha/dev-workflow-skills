# Orchestration patterns

The shapes a project lead runs, each with when to pick it, a compact stage skeleton and what it tends to produce. The lifecycle table in `SKILL.md` says which pattern serves which stage, and its "Harness capabilities" table maps each capability to your harness. Every skeleton assumes the `COMMON` brief below and the strongest available model on every agent.

## Reading the skeletons

The skeletons are JavaScript-like pseudocode, compact enough to show a whole stage. They run as-is in Claude Code's Workflow tool (script API in the workflow-authoring skill); in any other harness, read them as a plan:

| Notation | Meaning | Without scripted orchestration |
|---|---|---|
| `agent(prompt, { label, schema })` | Spawn one subagent with this brief; `schema` is the shape of its structured return | Spawn a subagent (or do it yourself) and ask for a JSON block or a file at a named path |
| `isolation: 'worktree'` | The agent works in its own worktree | `git worktree add .worktrees/<label> <base sha>` and brief the agent to `cd` there |
| `parallel([...])` | Run these at once and wait for all | Launch the subagents together; collect every result before the next stage |
| `pipeline(items, stage1, stage2, ...)` | Each item flows through the stages independently, so item A can be in review while item B still builds | Run each item's stages as a chain; start the next item's chain without waiting |
| `phase('X')`, `log(...)` | Progress labels | Status lines in your scratch report |

Carry every result between stages as a file in scratch space, so a later stage or a resumed session can read it.

## Stage conventions

- **Constants first:** absolute paths (`W` the integration worktree, `MAIN` the main checkout, `SCR` scratch space, `DESIGN`, `SPECS` = `<repo>/specs`), then `COMMON`, then the items and schemas.
- **Labels** have the form `<stage>:<key>` (`research:07`, `build:C`, `review:safety`, `fix:C`), so the run's log reads as live status.
- **Build agents return free text** whose first lines are `WORKTREE: <pwd>` and `BRANCH: <name>`; the next stage parses them and must `cd` there itself.
- **Cap forwarded text** (about 12,000 characters of a report), and pass the tip SHA along in results, not as a constant in a later stage's brief.
- **Long or code-heavy returns** go to a file the agent writes, and the structured return carries its path.
- **Changing a rule mid-run:** stop the run, edit only the stages the rule affects, and rerun them. Tell re-run verifiers to treat the earlier pass's corrections as unverified claims.

### Claude Code Workflow specifics

- Bake constants into the script text; `args` can arrive JSON-stringified. Avoid `<` in schema string outputs; they can be mangled.
- Give each `agent()` its `phase` option so the run's journal reads as live status. Leave `model` out so agents inherit an Opus session, and check for an `agentType` that pins another model.
- **Pass the script inline.** The tool saves it and returns its `scriptPath`, which is what you edit and resume from.
- **Reading the result.** The completion notice is truncated. The full value is in the file its `<output-file>` tag names, and the script's return value is under `result`:

  ```bash
  python3 - <<'EOF'
  import json
  r = json.load(open('<output-file path>'))
  print(list(r))            # summary, agentCount, logs, result, workflowProgress, totalTokens, totalToolCalls
  res = r['result']
  print(list(res) if isinstance(res, dict) else type(res))
  EOF
  ```

  Check the keys before assuming a shape, then write the fields you need to a scratch report and read that.
- **Resuming after a rule change:** `TaskStop` the run, edit the script and resume with the same run id. Only agents whose prompt and options are unchanged replay from cache, so an edit to `COMMON` reruns every agent. When the stored `scriptPath` is refused, copy the script into the scratchpad and resume from the copy.

## The brief template

```js
const COMMON = `
You are <one researcher | a senior engineer | a JUDGE, not an implementer | an independent VERIFIER> on a team building <project> (<areas touched, with stacks and versions, from the context file's Repository section>). Today is <date>.
THE PROBLEM: <two or three sentences: who has it, what it costs, the evidence>. Everything you do serves it. Flag work that does not, and any requirement that looks inherited rather than needed.
THE CONTRACT: ${DESIGN}. Read it FULLY and follow it exactly; where it is silent, choose the simplest option and write it down in your report.
SCOPE: <RESEARCH ONLY: describe what IS, no implementation plan | read-only: do not edit, commit or start servers | build only in your worktree>.
READ FIRST (do not re-research what they establish): .agents/workflow-context.md; the docs its Specs & Docs section lists; <scratch reports, specs/*-research.md, spike worktrees as REFERENCE ONLY, not to copy>.
USER DECISIONS (fixed, do not relitigate): <each quoted verbatim>.
KNOWN APP BEHAVIOURS (not bugs to fix here; work around them and report them): <list>.
CONVENTIONS AND BEST PRACTICES: the repo's documented conventions (AGENTS.md, CONTRIBUTING.md or equivalent, quoted by section); any stack-specific skills installed; the framework's documented patterns; the patterns of recent merged PRs in the same directory. State the reason for any deviation. Never refactor existing code toward generic principles unasked; keep diffs small.
COMPLEXITY BUDGET: the smallest change that solves THE PROBLEM. Every new abstraction, dependency, table, flag or component you add is listed in your report with the problem it solves and the simpler option it beat.
YOUR WORKTREE: it must contain <base sha>: git merge-base --is-ancestor <sha> HEAD || git merge --ff-only <sha>. Install dependencies in it before any gate.
<the SAFETY block from SKILL.md with the context file's Safety section filled in, verbatim, and the role lines that apply>
LOCAL ENVIRONMENT: <you are the ONLY agent allowed to deploy to the shared local environment in this run | do not touch the shared local environment | your own instance: <ports, name prefix>>.
SHARED INTERFACE (identical in every track; <track> owns the real file, the integrator takes its copy): <code>.
GATES (run them, paste the results): <the context file's Gates rows for the areas touched, with its CI/local drift notes>.
COMMITS: the context file's commit format and attribution rule. Fold fixes into their item (--fixup, then autosquash). Never push.
REPORT: first lines WORKTREE: <pwd> and BRANCH: <name>. Prove every claim with commands and outputs. Long findings go to <file>; return the summary the schema asks for. Tear down what you started.
`
```

Drop the blocks an item does not need: a researcher has no worktree or gates, a judge has no commits. Give each item its own part after `COMMON`: the area, track or lens; concrete files and questions; the output path; and a STOP condition where a go/no-go exists.

## Schemas

```js
const SUMMARY = { type: 'object', properties: { file: { type: 'string' }, key_findings: { type: 'array', items: { type: 'string' } }, open_questions: { type: 'array', items: { type: 'string' } }, risks: { type: 'array', items: { type: 'string' } } }, required: ['file', 'key_findings', 'open_questions', 'risks'] }
const VERDICT = { type: 'object', properties: { file: { type: 'string' }, claims_checked: { type: 'number' }, corrections: { type: 'array', items: { type: 'string' } }, unverified: { type: 'array', items: { type: 'string' } }, overall: { type: 'string', enum: ['reliable', 'mostly-reliable', 'unreliable'] } }, required: ['file', 'claims_checked', 'corrections', 'unverified', 'overall'] }
const REVIEW = { type: 'object', properties: { issues: { type: 'array', items: { type: 'object', properties: { severity: { type: 'string', enum: ['blocker', 'major', 'minor'] }, title: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } }, required: ['severity', 'title', 'evidence', 'fix'] } }, verdict: { type: 'string' } }, required: ['issues', 'verdict'] }
const GATE = { type: 'object', properties: { verdict: { type: 'string', enum: ['PUSH', 'DO-NOT-PUSH'] }, blocking: { type: 'array', items: { type: 'string' } }, notes: { type: 'array', items: { type: 'string' } }, tip: { type: 'string' } }, required: ['verdict', 'blocking', 'notes', 'tip'] }
```

Other shapes, by field:

- `SYNTH` (P1): `path`, `executive_summary`, `critical_gaps`, `important_gaps`, `open_questions`, `decision_relevant_facts`.
- `ROWS` (P2): `rows[{option, verdict, reason}]`; the verifier adds `corrections`. `SPIKE`: `feasible`, `branch`, `steps`, `app_code_changes`, `risks`, `recommendation`, `evidence_paths`.
- `REPORT` (P3): `approach`, `branch`, `worktree_path`, `files_built`, `app_code_changes`, `protocol_results`, `fragile_dependencies`, `remaining_gaps`, `effort_to_productionise`, `recommendation`, `evidence_paths`. `JUDGE`: `lens`, `scores[{approach, score_1_to_10, rationale}]`, `winner`, `graft_from_runner_up`, `blocking_risks`, `claims_i_checked`.
- `ANSWER` (P4): the key answer as its own field, `key_findings`, `risks`; `ANSWER_VERDICT`: the same field, `corrections`, `overall`.
- `DESIGN_REVIEW` (P5): `lens`, `issues[]` as in `REVIEW` plus `impact`, `drop[]`, `verdict`.
- `VERIFY` (P8): `issues[]` as in `REVIEW`, `reproduced`, `verdict`.
- `REPRO` (P15): `candidates[{id, reproduced: yes | no | code-only, title, impact, steps_to_reproduce, observed, expected, root_cause, fix_sketch, acceptance_criteria, needs_human_decision, decision_question, evidence_paths}]`. `TRIAGE`: `verdicts[{id, verdict: confirmed | corrected | not-a-bug | duplicate, notes, duplicate_of}]`.
- `FINDINGS` (P16): `findings[{component, file, severity, issue, evidence, fix}]`, `checked[]`. `VERDICTS`: `verdicts[{component, issue, holds, severity, reason, fix}]`.

## P1. Research fan-out, a verifier per area, a synthesizer

**When:** at the start of a project, and whenever a new domain arrives (a vendor, an external integration, a subsystem), before any design. research-document owns the areas, the file layout and the synthesis; this runs its areas as parallel subagents and adds the verifier stage.

```js
const DIR = `${SPECS}/research-findings/${TOPIC}`
phase('Research')
const results = await pipeline(AREAS,
  (a) => agent(`${COMMON}\n\n${a.prompt}\nWrite to: ${DIR}/${a.n}-${a.key}.md`, { label: `research:${a.n}`, phase: 'Research', schema: SUMMARY }),
  (summary, a) => agent(`${COMMON}\nYou are an ADVERSARIAL VERIFIER, not a researcher. Read ${DIR}/${a.n}-${a.key}.md fully. Pick the 10-15 most load-bearing claims and assume each is wrong until you confirm it at file:line, in current docs, or with a read-only query. Edit the file in place ("corrected by verifier", "(unverified)") and append "## Verification notes". Never paste a credential or PII value.`, { label: `verify:${a.n}`, phase: 'Verify', schema: VERDICT }).then((v) => ({ area: a.key, summary, verdict: v })))
phase('Synthesize')
const synthesis = await agent(`${COMMON}\nYou are the SYNTHESIZER. Follow the synthesis step of the research-document skill over ${DIR}, Verification notes included; prefer the verifiers' corrections. Write ${SPECS}/${TOPIC}-research.md.`, { label: 'synthesize', phase: 'Synthesize', schema: SYNTH })
return { areas: results.filter(Boolean), synthesis }
```

Areas that query production use only the read-only access the context file's Safety section names. Re-verifying a weaker model's pass on the strongest model is worth it: verifiers catch confirmed-wrong commits, "corrected" right figures, and pasted secrets.

## P2. Research, verify, then a spike gated on the verified verdict

**When:** the owner's answer is conditional ("only if the vendor has a sandbox we can create by API"). Build a prototype only if the verifier confirms the precondition.

```js
const research = await agent(`${COMMON}\nUSER DECISION: "<quoted>". RESEARCHER: for each option, does the precondition hold, and at what cost? One row per option with a verdict.`, { label: 'research:precondition', phase: 'Research', schema: ROWS })
const verified = await agent(`${COMMON}\nADVERSARIAL VERIFIER: re-check every positive verdict against current docs and return the corrected rows.\n${JSON.stringify(research)}`, { label: 'verify:precondition', phase: 'Verify', schema: ROWS })
const row = (verified?.rows ?? []).find((r) => r.option === '<the one that matters>')
let spike = null
if (row?.verdict === '<the passing verdict>') {
  phase('Spike')
  spike = await agent(`${COMMON}\nSPIKE. <the SKILL.md role line for a real vendor sandbox>. ...`, { label: 'spike:<option>', phase: 'Spike', isolation: 'worktree', schema: SPIKE })
} else log('Skipping the spike: precondition not verified')
return { research, verified, spike }
```

Launch independent spikes first, then ask the blocking questions, then launch this as soon as the answer lands.

## P3. Competing spikes in worktrees, judged through different lenses

**When:** a risky unknown with two or more viable approaches that paper analysis cannot settle (two workflow shapes, two data models, two vendor integrations).

```js
const spikes = await parallel(SPIKES.map((s) => () => agent(`${COMMON}\n${PROTOCOL}\n\n${s.prompt}`, { label: `spike:${s.key}`, phase: 'Spike', isolation: 'worktree', schema: REPORT }).then((r) => ({ key: s.key, report: r }))))
const judges = await parallel(LENSES.map((lens, i) => () => agent(`${COMMON}\nYou are a JUDGE, not an implementer. Do not modify code. Check the most important claims yourself (read the branches, re-run cheap checks, start no servers), then score every spike through this lens:\n${lens}\nSPIKE REPORTS:\n${JSON.stringify(spikes.filter(Boolean))}`, { label: `judge:${i + 1}`, phase: 'Judge', schema: JUDGE })))
return { spikes, judges }
```

`PROTOCOL` is one real end-to-end test every spike must pass, as close to the real surface as the environment allows: real migrations, the real runtime or its official test harness, recorded real inputs. If the local environment is a single shared instance, at most one spike deploys to it, or they take turns in sequence. Each spike commits locally and never pushes. Typical lenses: correctness and robustness against maintainability and fit with existing patterns. When the judges split, show the owner the table rather than pick. Spike code is reference only (P5).

## P4. One question, researched and verified

**When:** one contract the build depends on, such as a vendor API's behaviour, a runtime's replay or ordering constraint, or an external system's input format.

```js
const research = await agent(`${COMMON}\nDECISION CONTEXT: <what was decided, the owner quoted>. TASK: write ${FILE}. KEY QUESTION to answer from source: <q>. Cite source files and lines, docs URLs, or query results for every contract claim. Never invent team facts; write a clearly marked TODO.`, { label: 'research:<topic>', phase: 'Research', schema: ANSWER })
const verify = await agent(`${COMMON}\nADVERSARIAL VERIFIER. Check the 15 most load-bearing claims in ${FILE} against the source. Edit in place; append "## Verification notes".`, { label: 'verify:<topic>', phase: 'Verify', schema: ANSWER_VERDICT })
```

## P5. Design doc, multi-lens adversarial review, v2

**When:** after research and spikes, before any code. You write the design and the v2 yourself.

```js
const REVIEWER = `Senior reviewer. Review the DESIGN at ${DESIGN} adversarially against THE PROBLEM it states: what is wrong, missing, risky or over-built BEFORE implementation, and the smallest concrete fix. Ground every issue in evidence (file:line, research, spike code, docs). Read-only. User decisions that are FIXED (do not relitigate): <list>. Also list what to DROP as over-engineering.`
const LENSES = [['necessity', '<is the problem real and evidenced; does the design solve it at its root rather than a symptom; which components, layers, flags or stages the problem does not require; the simplest design that would still solve it>'], ['feasibility', '<checklist>'], ['safety', '<production data, secrets and PII, the Safety section hard rules, migrations, deploy path>'], ['conventions', '<documented repo conventions, framework best practices where they apply, pr-train split and risk tiers, recent PRs>'], ['operability', '<alerts, flags, rollback, versioning of long-running work>']]
const reviews = await parallel(LENSES.map(([key, lens]) => () => agent(`${REVIEWER}\n\nYOUR LENS: ${lens}`, { label: `review:${key}`, phase: 'Review', schema: DESIGN_REVIEW })))
return reviews.filter(Boolean)
```

Always run the necessity lens; add or drop the others to fit the project. The necessity lens and the DROP lists are where over-building gets cut: every component the design keeps has a line saying why the simpler alternative fails. The conventions lens sizes the split against pr-train's 500-line target and recent merges in the same area, and usually finds that reusing a spike's code means a rewrite, not a copy. The feasibility lens names the first go/no-go milestone, which goes into wave 1's brief.

## P6. Land the shared seam first

**When:** parallel tracks will meet in shared files (a data model, a DB table, a message or event shape, an API contract). Before the wave, commit the smallest shared interface as train item 1. Tell every track to contain it (`git merge-base --is-ancestor <sha> HEAD || git merge --ff-only <sha>`). Put a SHARED INTERFACE block in `COMMON`, byte-identical in every track, naming the track that owns the real file. Name each integration point and the failure to raise when a partner's piece is missing. The integrator then skips a track's duplicate interface commits and takes the owner's.

## P7. Build wave: parallel worktree tracks, each built, reviewed, fixed

**When:** the revised design and the seam exist. 2 or 3 tracks. If the local environment is a single shared instance, tracks run their gates only and leave it to the integrator.

```js
const results = await pipeline(TRACKS,
  (t) => agent(`${COMMON}\n\n${t.prompt}\n\nStart your final report with WORKTREE: <pwd> and BRANCH: <name> on their own lines.`, { label: `build:${t.key}`, phase: 'Build', isolation: 'worktree' }),
  (report, t) => {
    const wt = (String(report).match(/WORKTREE:\s*(\S+)/) || [])[1] || ''
    return agent(`${COMMON}\nYou are an independent REVIEWER (read-only; you may re-run cheap gates). Review TRACK ${t.key} in ${wt} against (1) the design, (2) the repo's documented conventions and the surrounding code, quoting line numbers, (3) the safety rules, (4) whether the report's evidence reproduces from HEAD, (5) whether every added abstraction, dependency or component is warranted by THE PROBLEM, or a simpler option would do. Verify before asserting; no speculative issues.\nTRACK REPORT:\n${String(report).slice(0, 12000)}`, { label: `review:${t.key}`, phase: 'Review', schema: REVIEW }).then((review) => ({ report, review, wt }))
  },
  (r, t) => {
    if (!r.wt) return { key: t.key, fix: 'no worktree path parsed; fix skipped' }
    return agent(`${COMMON}\nYou are the IMPLEMENTER of TRACK ${t.key}. First run "cd ${r.wt}" and work only there. For each issue: verify it, then fix it (commit) or record why it is not valid. Re-run the gates. Report WORKTREE:/BRANCH: first, then each issue as fixed / not valid / deferred.\nREVIEW:\n${JSON.stringify(r.review)}`, { label: `fix:${t.key}`, phase: 'Fix' }).then((fix) => ({ key: t.key, wt: r.wt, fix }))
  })
return { tracks: results.filter(Boolean) }
```

The fixer is a fresh agent sent into the builder's worktree, not the builder's context. Reviews typically find evidence that depended on uncommitted files and integration faults a track's own mocks hid. Isolation worktrees that changed stay on disk: list them for cleanup.

## P8. Integrate from a fresh clone, then an independent verifier

**When:** after every build wave. Per-track reviews cannot see problems that only appear across tracks.

```js
const integration = await agent(`${COMMON}\nYou are the INTEGRATOR in ${W}, and the ONLY agent allowed to deploy to the shared local environment. 1 Rebase onto origin/<default branch>. 2 Bring in the tracks in train order by cherry-pick, skipping duplicates. 3 Each integration fix is its own commit naming its train item. 4 PROVE: all gates for the areas touched; each change verified on the local environment per the context file's "Verify by change type" table; <a real end-to-end run against a test fixture if the brief allows>. 5 Leave the local environment as you found it.`, { label: 'integrate', phase: 'Integrate' })
const verify = await agent(`${COMMON}\nYou are an independent VERIFIER. First question: does the integrated result solve THE PROBLEM on the most real surface available, including the failure mode that started the work? Do not trust the report: reproduce the gates from a NEW clone at the reported tip. Then probe what production would hit: bad and missing inputs on each new endpoint, cross-tenant access, a background job failing and retrying, a migration against existing rows, each train item passing its gates at its own commit. Review the integrated diff for duplication and naming across tracks. Do not deploy to the shared local environment; read its logs and data only.\nINTEGRATOR REPORT:\n${String(integration).slice(0, 12000)}`, { label: 'verify', phase: 'Verify', schema: VERIFY })
const fix = await agent(`${COMMON}\nYou are the INTEGRATOR again. For each finding: confirm it, fix it (name the train item) or explain. Re-run the evidence.\nVERIFIER FINDINGS:\n${JSON.stringify(verify)}`, { label: 'fix', phase: 'Fix' })
return { integration, verify, fix }
```

Expect the verifier to find what the integrator's "all green" hid: items that fail at their own commits, helpers duplicated across tracks, an untested failure path.

## P9. Fold every fix into its item, prove every item at its own commit

**When:** from the first integration until the PRs open, for any branch that becomes a train or stack; after that, pr-train's per-layer rules apply. Every brief carries: `git commit --fixup=<item sha>`, then `GIT_SEQUENCE_EDITOR=: git rebase -i --autosquash origin/<default branch>`; check that no `fixup!` or `amend!` subject remains. Before opening the PRs, a background script checks out each item's SHA in one fresh clone and runs that item's gates (the context file's Gates, scoped to the areas the item touches), saving a log and a `how-tested.md` per item. pr-train owns the split, the order and the descriptions.

## P10. Pre-push gate: fix, then a PUSH / DO-NOT-PUSH verifier

**When:** the last small fixes before a branch leaves the machine.

```js
const fix = await agent(`${COMMON}\nYou are the implementer. 1..n <the fixes, each folded into its item>. Then a secret and PII scan of the whole branch diff (API keys, bearer tokens, .env values, real phone numbers, account numbers, SSNs, real authorizer or requester data). Re-run on the tip: gates; each changed item passes at its own commit. Report the commit list, the evidence and the scan table.`, { label: 'fix', phase: 'Fix' })
const verify = await agent(`${COMMON}\nYou are an independent VERIFIER before this branch is pushed. (a) Re-run the secret and PII scan over every commit (git log -p) with your own patterns; no home paths, none of the Safety section's never-write strings. (b) Re-run the cheap evidence. (c) Every commit follows the context file's commit format and attribution rule, and none is a fixup. (d) No already-applied migration was edited, and any generated lockfile or checksum the repo requires is current. (e) git status --porcelain --ignored shows nothing that should be committed. Return PUSH or DO-NOT-PUSH.\nIMPLEMENTER REPORT:\n${String(fix).slice(0, 12000)}`, { label: 'verify', phase: 'Verify', schema: GATE })
return { fix, verify }
```

Push only on PUSH and the owner's yes, with `--force-with-lease=<branch>:<expected sha>`, and confirm with `git ls-remote origin <branch>` in a separate command: a readback chained after the push can make a good push look failed.

## P11. Real surface, findings file, iteration

**When:** the change passes locally. Run it where it will run: CI on the PR (read failing job logs with `gh run view --log-failed`), the environment a merge deploys to, a scheduled or cloud agent run on the pushed branch. Write each finding with its candidate fixes to `<scratch>/<run>-findings.md`. The next run names that file in `COMMON`, maps each finding to a train item, fixes and ends with a P10 gate. Production is observed, never changed: after a deploy, confirm the deployed version with the read-only access the context file names.

## P12. Write, review against the code, revise

**When:** any prose that becomes a repo artifact: a spec, a skill, a README, a routine prompt.

```js
const draft = await agent(`${COMMON}\nWrite ${OUT}: <numbered section plan>. Do not commit yet. Return the sections and any facts you could not confirm from the code.`, { label: 'write', phase: 'Write' })
const review = await agent(`${COMMON}\nYou are an adversarial REVIEWER of ${OUT}. Check every factual claim against the code (paths exist, commands and flags are real, numbers match the reports); that it does not paraphrase code or restate another skill, the repo's agent instructions or a README; no iteration framing (v2, legacy, old-X); completeness against the owner's ask.\nWRITER SUMMARY:\n${String(draft).slice(0, 4000)}`, { label: 'review', phase: 'Review', schema: REVIEW })
const revise = await agent(`${COMMON}\nApply the review, verifying each issue first. Commit it as its own commit. Report each issue as fixed or not valid.\nREVIEW:\n${JSON.stringify(review)}`, { label: 'revise', phase: 'Revise' })
```

Skills stay lean: positive instructions, one gate where a risky operation is documented, no ticket-number provenance.

## P13. Drafters paired with fact-checkers

**When:** bulk prose that must be accurate and uniform, such as a train's PR bodies.

```js
const GROUPS = [ITEMS.slice(0, 3), ITEMS.slice(3, 6), ITEMS.slice(6, 9)]
const results = await pipeline(GROUPS,
  (g) => agent(`${COMMON}\nYOUR ITEMS:\n${g.map((it) => `- item ${it.n} (${it.issue}): commits ${it.commits}. ${it.note}`).join('\n')}`, { label: `draft:${g.map((it) => it.n).join(',')}`, phase: 'Draft' }),
  (drafted, g) => agent(`${COMMON}\nYou are the REVIEWER for these items. Check every factual claim against the commits and the spec, and pr-train's "Keep it high-signal" rules. Fix the files directly.\nDRAFTER'S REPORT:\n${String(drafted).slice(0, 4000)}`, { label: `review:${g.map((it) => it.n).join(',')}`, phase: 'Review' }))
```

`COMMON` carries pr-train's PR description requirements and "Keep it high-signal", the context file's title format, its scope labels per item, reviewer questions pinned to their items, a literal `<!-- HOW TESTED -->` placeholder for P14 to fill, and read-only rules. Reviewers routinely fix dozens of factual errors across a train.

## P14. Prose by agents, facts by scripts

**When:** wherever a claim can be read from a log or a SHA. Small scripts in scratch space do the facts, from one list of `<n> <branch> <short sha> <labels>` lines, where each branch, named per the context file, is cut at its item's commit on the integration branch:

- the P9 script runs every item's gates in a fresh clone and keeps each item's logs and `how-tested.md`;
- a fill script asserts each body has exactly one `<!-- HOW TESTED -->` and replaces it with the item's SHA and its gate results read from the logs, plus the local-environment or end-to-end evidence where the item has it;
- an open script, run only on the owner's yes, pushes and opens the PRs. For a `gh stack` chain, follow pr-train's stack workflow (`gh stack submit --auto`, then `gh pr edit` each body). For hand-opened branches:

```bash
BRANCHES=<the list file>; BODIES=<the reviewed bodies>; base=<default branch>; prs=()
while read n b s labels; do
  [ "$(git rev-parse --short=8 "$b")" = "$s" ] || { echo "branch $b is not at $s"; exit 1; }
  git push -q origin "$b:refs/heads/$b" || exit 1
  url=$(gh pr create --draft --base "$base" --head "$b" --title "$(cat "$BODIES/$n.title")" --body-file "$BODIES/$n.md" --label "$labels") || exit 1
  prs+=("$url"); base=$b
done < "$BRANCHES"
gh stack link "${prs[@]}"
```

For a sequential train (pr-train's default), open only the first PR and drop the loop and the link. When an item's tip moves, re-verify at the new SHA before opening.

## P15. Reproduce, verify, then file

**When:** building and testing surfaced probable bugs outside the project's scope. File only what reproduces.

```js
const repro = await agent(`${COMMON}\nREPRODUCER: fresh clone. For EACH candidate: reproduce (unit test, the local environment if you are its driver, or a read-only production query), capture evidence under ${EVID}/<Cn>/, root cause file:line, fix sketch, acceptance criteria, needs_human_decision.\nCANDIDATES:\n${CANDIDATES}`, { label: 'reproduce', phase: 'Reproduce', schema: REPRO })
const verify = await agent(`${COMMON}\nAdversarial VERIFIER (read-only; you may read the tracker to dedupe). Mark each confirmed / corrected / not-a-bug / duplicate.\n${JSON.stringify(repro)}`, { label: 'verify', phase: 'Verify', schema: TRIAGE })
const filed = await agent(`${COMMON}\nFILER. Use the context file's tracker and any ticket skill the repo has. Search for existing issues first. File confirmed and corrected ones only, with the corrected facts; for duplicates, comment the new evidence; add a "Decision needed" section where a person must decide.\n${JSON.stringify(verify)}`, { label: 'file', phase: 'File' })
```

The filer runs only after the owner's yes to "file the bugs found". When several related tracker records must be created and cross-linked (a project and its issues), run parallel creators and then one EDITOR agent that adds relations (`blockedBy`, related) and does a clarity pass with minimal edits, changing no states or assignees. Writing rules for both: written for people and for agents with limited context and per-token cost; do not invent facts; never paste secrets or PII; never write a never-write string; create only what is asked.

## P16. Chunked audit with a refuting verifier per chunk

**When:** large generated artifacts that other agents will consume (a knowledge-base doc set, a batch of test fixtures, a skill set), and after any fan-out that followed one shared brief.

```js
const TASKS = [...CHUNKS.map((list, i) => ({ key: `chunk-${i + 1}`, prompt: `Audit ${list.join(', ')}. List every item you checked in checked.` })), { key: 'index', prompt: '<audit the index document>' }]
const results = await pipeline(TASKS,
  (t) => agent(`${COMMON}\nTASK (${t.key}):\n${t.prompt}`, { label: `audit:${t.key}`, phase: 'Audit', schema: FINDINGS }),
  (audit, t) => audit?.findings.length
    ? agent(`${COMMON}\nYou are an adversarial VERIFIER. For each finding, try to refute it by reading the cited files yourself. It holds only if you reproduce the evidence and the consuming agent really would get it wrong. Default to holds=false when the evidence does not reproduce. Re-rate severity; sharpen the fix.\n${JSON.stringify(audit.findings)}`, { label: `verify:${t.key}`, phase: 'Verify', schema: VERDICTS }).then((v) => ({ key: t.key, audit, verdicts: v?.verdicts ?? [] }))
    : { key: t.key, audit, verdicts: [] })
```

`COMMON` says who reads the artifact and why an error multiplies, limits fixes to a closed list of types, sets a severity rubric and bans style preferences. Fix every confirmed high-severity finding before asking to publish or push the artifact.

## P17. Calibrate, then fan out in a shared workspace

**When:** many similar artifacts produced in one worktree whose state the agents share, where worktree isolation would split what must stay together (per-integration fixtures, a set of knowledge-base docs). This runs as plain parallel subagents, not a scripted multi-stage run.

1. Write and grade the first few yourself.
2. Write one brief file in scratch space: the loop (produce only your set, check, grade, iterate); hard rules (edit only your set's files, never shared config, no git state changes, no shared local environment, no files holding real credentials, no machine-wide commands); and an escalation rule: when one root cause breaks 2 or more of your items, or once when it is config-level, stop and describe it for the orchestrator.
3. Launch parallel Agent calls: "Read and follow `<brief>` exactly. BATCH: `<name>` YOUR SET: `<items>`".
4. Check each batch yourself: spot-check outputs, and confirm the main checkout is clean.
5. Apply shared fixes only after every batch finishes.

Then run P16 on the result: every batch can grade itself good while the shared brief spread the same defect to all of them.

## Sizes and times

Rough calibration from one prior multi-track project; scale to yours.

| Shape | Agents | Time |
|---|---|---|
| P1, 3 areas | 7 | 30 to 40 min |
| P1, 9 areas | about 30 | about 2 h |
| P3, 2 spikes, 2 judges | 4 | about 70 min |
| P2 | 3 | about 85 min |
| P4 | 2 | 30 to 55 min |
| P5, 4 lenses | 4 | about 25 min |
| P7, 3 tracks | 9 | about 2 h |
| P8 | 3 | about 3 h 20 |
| P10 | 2 | about 1 h |
| P12 | 3 | about 40 min |
| P15 | 3 | about 45 min |
| P16, 3 chunks and an index | 8 | about 25 min |
| P13, 4 groups | 8 | about 20 min |

Build waves and integration take 2 to 4 hours each; research, review and audit shapes take 20 to 90 minutes, which is where extra lenses and verifiers are cheap.
