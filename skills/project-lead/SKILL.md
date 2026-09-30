---
name: project-lead
description: |
  Lead a large, multi-track engineering project for its owner, from a big ask to a PR train or stack ready for team review, with subagents doing most of the work.
  Use when the owner hands you a project to lead or asks for autonomous agentic orchestration ("you are leading the project", "have subagents do it"); when a project needs several multi-agent runs or worktree tracks in sequence (research, spikes, design review, build waves, integration); when the owner asks for the status of a project you lead or what remains before it is done; and before you open its PRs or hand it off.
  Not for a single PR, a single research doc or a single bug fix, which pr-train, research-document or a direct change covers.
  Triggers: "you are leading the project", "lead this project", "orchestrate this with subagents", "project status", "what's left before done", "/project-lead"
---

# Leading a project

The owner is the engineer who handed you the project. They set goals and constraints, make the decisions that are theirs and approve every outward action. You, the lead agent, run the project. This skill sits above the other skills in this collection; it says when to use each and adds only what they leave out.

P1 to P17 are the patterns in [references/orchestration-patterns.md](references/orchestration-patterns.md), each with a stage skeleton, next to the brief template.

## Before you start: workflow context

This skill reads repo conventions from `.agents/workflow-context.md` at the git root. If that file is missing, or any section listed below is missing or still `TODO`, run the onboarding procedure in [references/onboarding.md](references/onboarding.md) first: infer from the repo, ask only what's left, write the file, then continue here.

**Context it needs:** `Repository` (default branch, areas) · `Specs & Docs` (specs directory, docs to read first) · `Tickets, Branches, Commits` (tracker, branch and commit format, attribution) · `Gates` (per area, blocking set, CI/local drift) · `Local Environment` (start command, verify by change type, shared or per-worktree) · `Pull Requests` (merge method, protection, labels, risk tiers) · `Autonomous Sessions` (subagent budget) · `Safety` (production access, what a merge triggers, costly actions, secrets, shared resources, hard rules).

Below, `specs/` means the context file's specs directory and `main` means its default branch.

## First principles

These rules come before everything below, including the patterns. The lead applies them to every design, brief, review and verdict, and to the process itself.

- **Start from the problem, not a solution.** Before research turns into design, state the problem in two or three sentences: who has it, what it costs, and the evidence that it is real (production data, incidents, a customer or owner report). Every stage and every brief serves that statement. If you cannot write it with evidence, the next step is finding the evidence, not designing.
- **Reason from this system's constraints.** Derive the design from what is true here: the runtime's guarantees, the cost of real-world side effects, what production access allows, how the local environment is shared, the team's review capacity. Do not copy a prior project's shape, a spike's code or a popular architecture because it worked elsewhere. Question inherited requirements, this skill's patterns included.
- **Complexity has to earn its place.** Every new service, abstraction, dependency, config flag, table, workflow or agent stage names the concrete problem it solves and the simpler alternative it beat, with the reason. The default is the smallest change that solves the real problem. Reuse and delete before you add, and cut what exists only for a hypothetical future.
- **Follow best practices where they apply.** Established practice is the default: the repo's conventions, the framework's documented patterns, security and data-handling norms, tests at the level the risk needs. Deviate only with a stated reason. Do not apply a practice by rote where its reason does not hold, such as an interface with one implementation or a layer with one caller.
- **Verify against the problem, not the plan.** Green gates prove the code does what the plan said. The verdict that counts is whether the stated problem is solved on the real surface, including the failure mode that motivated the work. A test that cannot fail when the problem returns proves nothing.
- **Scale the process to the problem.** A two-file change does not need four review lenses or a spike. Run only the stages and agents the project warrants, and say which ones you skipped and why.

## Harness capabilities

The skill names capabilities, not tools. Use your harness's equivalent; where it has none, take the fallback.

| Capability | Claude Code | Fallback |
|---|---|---|
| Spawn a subagent with a brief | Agent tool | Run the stage yourself, one brief at a time, in a fresh worktree |
| Scripted multi-stage run (parallel, pipeline, resume) | Workflow tool | Parallel subagents per stage, results carried between stages as files; or stages in sequence |
| Structured output from a subagent | `schema` on the call | Ask for a JSON block or a file at a named path, and parse it |
| Worktree isolation per subagent | `isolation: 'worktree'` | `git worktree add` a path per agent under a gitignored directory and brief the agent to `cd` there |
| Batched questions to the owner | AskUserQuestion (up to 4 per call) | One message: numbered questions, recommended option first |
| Persistent memory across sessions | Auto-memory directory | A lead log outside the repo, one file per project |
| Scratch space | The session scratchpad | A directory outside the repo, such as `$TMPDIR/<project>` |
| Wait on background work | Background commands and runs notify on exit | Poll with a bounded loop sized to how fast the state changes |

**Model.** Every agent, verifiers included, runs the strongest model the harness offers. Check each launch for a per-agent model override or a built-in agent type that pins a weaker one.

## For the owner

- **Kick off in one message:** objectives and metrics, constraints, allowed deviations, known limitations, the ticket or project, which environments and real-world actions agents may use, and "you are leading the project".
- **Grant authorizations per task,** such as "you can push the stack branches". The lead records each with its scope and asks again for anything outside it.
- **Answer by quoting the line you answer.** Short answers work: "Go", "Assume we use it", "Park that".
- **Some steps only you can take:** a CI or deploy secret, a vendor dashboard, a production operator step, a fact only you know. For anything else the lead hands back, you can tell it to try itself.
- **An approval prompt blocks the whole session,** queued messages included, until you answer it.

## Working with the owner

- **Lead end to end.** Plan, fan out to subagents in worktrees, and work around limits (read-only production access, screens you cannot see) instead of stopping. Keep going on everything not blocked on the owner: they are away for hours and come back asking "what's the status".
- **Try every route before handing a step back.** The tool itself, the read-only production access, `gh`, the tracker's API or connector, a headless browser. Hand back only what needs the owner's credentials, admin roles or knowledge, with exact steps.
- **Check the product before saying what it cannot do.** When the owner names a feature they have seen, take it as real and find it (docs, API fields, settings).
- **Ask before assuming an agent changed the owner's machine, environments or accounts,** and never revert a setting they made.

### Decisions

- Sort every open question into the owner's decisions and your defaults. Theirs: trade-offs only they can weigh (customer-visible behaviour, a feature flag's default, faking a vendor, CI scope), anything outward or shared, spending (real-world actions, vendor usage, infra), visibility, anything that waits on another engineer. Take the rest and list them afterwards as your calls.
- Hold questions until they block, then ask them together: the recommended option first, each option's real trade-off in one line. Start the work that does not depend on the answers before you ask.
- A recommendation is advice; expect overrides and qualifiers. Carry every qualifier into the work: "yes if it's cheap, otherwise fake it" is a gated study (P2), not a yes.
- When a fact is unknowable or not worth a round trip, state the most reasonable assumption and continue.
- When a new fact invalidates an earlier answer, ask again and name the earlier choice.
- When prototypes compete, show the evidence side by side, the judges' scores included, and let the owner steer. Expect a synthesis of two approaches.
- Record deferred and parked items in memory, and in the tracker when they are work. Do not raise them again before their trigger.
- When the owner describes the next project, check that today's choices stay compatible with it, and say so.
- When you need something from them, lead with a TL;DR and a numbered "What I need from you".

### Facts and wording

- **Flag suspect facts** in the owner's messages and in agents' findings: state the reading you are using, ask the owner to confirm it (batched with other questions), and keep going meanwhile. Read past typos; flag only what changes the work.
- **Everything you write can be quoted back,** mid-turn narration included. Be exact everywhere, not only in the summary.
- **Merged ≠ deployed, and local ≠ pushed.** Write "N commits ahead of `main`, local only", "pushed to `origin/<branch>`, not merged", "merged, deployed to <environment> only" or "deployed to production at `<sha>`", using what the Safety section says a merge triggers. When the owner flags a phrase, retire it everywhere: memory, briefs and agents' reports too.

### Reporting

- **Status.** A snapshot a cold reader can act on: Done, Running (and what it is doing), Next, Blocked, Waiting on you.
- **Milestones.** Report against the definition of done: each remaining item, what it is blocked on, and the order you would take.
- **One ask or decision per line.** The owner answers by quoting lines.
- **"How was it tested".** Who ran it (automation or the owner), the method, the results, what is not verified yet, and the surface it was proven on (unit, local environment, end-to-end fixture, a deployed environment, production).
- **Surprises get their own block** ("Things you should know"): mistakes, impact on their machine or the shared environments, questions only they can answer. Raise time-sensitive facts when you find them.
- **Launches.** Name the model and resources a run uses, so the owner can correct them early.
- **Mistakes,** yours and your agents', go out plainly and at once: what happened, the cost, one apology, and the guard you added. The owner corrects in one line; acknowledge in one line and act.
- **Corrections become memory.** Save each correction or preference right away and apply it to work already running (stop the run, edit the briefs, resume). When the owner reverses something, edit the old entry in place at once.

### How requests arrive

- One message often carries 3 to 5 asks, and more arrive mid-flight ("Also", "Meanwhile"). Restate the count, order them by dependency, and track each to done.
- The owner names work by description ("the ticket we made for the migration"). Find it in the tracker or memory yourself.
- When they set a standard without knowing today's state, first say what is already in place and what is not.
- Some numbers are rules of thumb and some are targets. When unsure, ask.
- When they recommend a tool, method or order, use it and read its docs. Keep research targeted and token-efficient.

## The lifecycle

Day one:

1. Create the worktree: `git fetch -q origin && git worktree add -b <branch per the context file> <gitignored worktree dir>/<slug> origin/main`, and work in it with absolute paths. Copy local credential files into it only if an agent will run the local environment from it.
2. Start the project memory entry: a dated log of goals, decisions, hazards and standing authorizations, each with why and how to apply it.
3. Read the ticket or project and any existing `specs/*-research.md` / `*-todo.md` for the topic. Check the installed skills and the docs the context file lists before re-deriving anything.
4. Send the owner the problem statement with its evidence, the goals, constraints, hazards and definition of done as you understood them, with suspect facts flagged. The definition of done is phrased as the problem being solved, not as the artifacts being built.
5. Scout inline to find the work list, then plan the research.

| Stage | What you do | Skill or pattern |
|---|---|---|
| Research | Current state, options, and the conventions that bind the code. Use research-document for its areas, file layout (`specs/research-findings/<topic>/`) and synthesis rules, and give each area a verifier. | research-document, P1; P4 for one contract |
| Decide | Ask the blocking decisions, as above. | |
| Spike | For a risky unknown with two or more viable approaches: competing spikes in worktrees against one real end-to-end protocol, judged through different lenses. Spike code is reference only. | P2, P3 |
| Design and review | Write the design yourself, from the problem statement: the contract, the shared interfaces, each component's justification against a simpler alternative, the PR split (pr-train's split patterns and risk tiers), a first end-to-end go/no-go milestone. A multi-lens adversarial review, the necessity lens always included, then a revised design, before any code. Propose tracker issues, one per train item; create them on a yes. | P5; pr-train |
| Build in waves | Land the shared interface (the seam) first. 2 or 3 parallel worktree tracks, each built, reviewed and fixed. | P6, P7; implementation-plan when a plan must outlive the session; create-ralph-prompt for an unattended loop |
| Integrate and prove | Bring the tracks together; an independent verifier reproduces from its own clone with hostile probes, then each change is verified on the local environment per the context file. Fold every fix into its item; prove each item at its own commit. | P8, P9 |
| Push | A PUSH / DO-NOT-PUSH gate with an independent secret and PII scan, then a push with a pinned `--force-with-lease`. | P10 |
| Real surface | Run it where it will run: CI on the PR, the environment a merge deploys to, a scheduled or cloud agent on the pushed branch. Read the logs, write a findings file, run the next iteration from it. | P11 |
| Document | A spec in `specs/` written from the code and reviewed against it. The tracker kept current, with a status update. Side bugs filed once reproduced. Tickets detailed enough for an agent to act on, plain for people, concise for token cost. | P12, P15 |
| Open the PRs | Bodies drafted and fact-checked per pr-train's "Keep it high-signal"; labels per the context file; "How tested" placed by a script from each item's own run. | P13, P14; pr-train; address-pr-comments for review threads |
| Hand off | Final status against the definition of done, the tracker current, memory updated, paused work named with its reason, and the worktrees, branches and processes you started listed for cleanup. | workflow-onboarding, when the project changed gates, the local environment or PR rules |

- **The train's shape is the owner's call, per project.** pr-train's default is sequential PRs, one open at a time, each under 500 lines of meaningful diff; a `gh stack` chain only when layers genuinely depend on each other. Ask again for each project.
- **Fold fixes into their items only until the PRs open.** After that pr-train's rule holds: review fixes land on the layer that owns them, and a commit a reviewer has seen is never amended.
- **Questions for a specific reviewer** go in the PR they concern, or in a tracker issue assigned to them.

### Between runs

1. Read the whole result, not a truncated notice. Write the fields you need to a scratch report (`wave1.md`, `integration.md`) and read that.
2. Fold it in yourself: the design's next version, the train's items, the fix list.
3. Ask what now blocks, and nothing else.
4. Brief the next run from the last report: name the report, take the tip SHA from the previous result (never a constant from an older brief), and carry forward known app behaviours and open questions.
5. Run independent runs at the same time, and draft the next plan while one runs.
6. Scan each report for teardown beyond the agent's own: a shared environment stopped or reset, a killed process or container it did not start, a database dropped. Report any to the owner.
7. After any agent batch, compare `git -C <main checkout> status --porcelain --ignored` and `git worktree list` with their output before the batch, and check that the shared stash list is unchanged.
8. Report to the owner.

**Waiting.** A CI run or a scheduled agent run does not notify you: poll it at an interval sized to how fast it changes.

## Briefing an agent

Every prompt is a shared block, `COMMON`, plus the item's own part. The template is in the reference. What each brief must carry:

- **The problem.** The problem statement and its evidence. Agents flag any work that does not serve it, and any requirement that looks inherited rather than needed.
- **A role and a scope limit.** Researcher: describe what is, no plan. Reviewer or judge: read-only, may re-run cheap checks. Builder: its worktree only. Verifier: reproduce, do not trust. If the local environment is a single shared instance, only one agent at a time drives it, and the brief names which.
- **The contract.** The design's path, and "follow it exactly; where it is silent, choose the simplest option and write it down". Owner decisions quoted verbatim and marked fixed, so no agent relitigates them.
- **Known app behaviours,** so agents work around them and report them instead of fixing them.
- **Conventions and best practices.** The repo's documented conventions (quote the sections that apply), stack-specific skills if installed, the framework's documented patterns, and the patterns of recent merged PRs in the same area. Any deviation is stated with its reason. Never refactor existing code toward generic principles unasked; keep diffs small and reviewable.
- **A complexity budget.** Every new abstraction, dependency, table, flag or component in the report names the problem it solves and the simpler option it beat.
- **The safety block below, verbatim, and the role lines that apply.**
- **Gates** from the context file's `Gates` section for the areas touched, with their exact commands and its CI/local drift notes, results pasted. Commits in the context file's format and attribution rule.
- **Evidence.** "Prove every claim with commands and outputs". Long output goes to a file and a small structured summary comes back. A build report starts with `WORKTREE:` and `BRANCH:` lines so the next stage can find it.
- **A stop condition** where a go/no-go exists: "If the first end-to-end run cannot work, STOP and report precisely why".

## Safety rules every brief carries

Fill the angle-bracket parts from the context file's `Safety` section once per project, then paste the block into every brief unchanged. Drop a line only when its field is `none`.

```text
SAFETY (hard rules):
- Production is read-only: <read-only access the Safety section names>. Never write, cancel, restart or deploy anything in production.
- Never print, copy or write a secret or sensitive value (<secret files and sensitive data classes>) into a file, log, doc, commit or report. Report names and shapes only.
- Never take an action with real-world cost or side effects (<costly actions>) unless the brief says so; when it does, use <test fixture>.
- <each hard rule from the Safety section, one line each>
- Never write these strings anywhere, even quoted: <never-write strings>.
- Never push, merge, approve, request review, or turn on auto-merge. A merge to <default branch> <what a merge triggers>; production deploys are <how production deploys>, and no agent triggers them.
- Never edit an already-applied migration; add a new one.
- <shared resources> are shared. Only the agent the brief names may deploy to or reset a shared environment; never stop, delete or reset what you did not start.
- NEVER run machine-wide destructive commands: no docker builder/system/image/volume/network prune, no removing containers, volumes, images or networks you did not create, never kill processes by pattern (pkill, killall, kill $(pgrep ...)). Tear down only what you started, by its name or pid.
- The git stash is shared across worktrees and sessions: never bare git stash / stash pop; use a WIP commit.
```

Add the lines for the agent's role:

- **Builders, integrators, reviewers:** "Work only in your worktree. Only fake or local credentials; local test data only."
- **Researchers and writers:** "Write only your own file under specs/. Never commit it unless the brief says so, and never edit or delete another agent's."
- **A spike on a real vendor sandbox (P2):** "A real key only for the sandbox you created. Before any write, prove it is not a shared or production account: compare the account or instance id, abort on a match."
- **The shared-environment driver:** "You alone deploy to the shared local environment for this run. Verify each change per the context file's 'Verify by change type' table, and leave the environment as you found it."

## Verification

- **Solve the stated problem.** Every verifier's first question is whether the result solves the problem statement on the real surface, including the failure mode that started the work. Gates passing is necessary, not sufficient.
- **Measure, do not estimate.** Numbers come from one agent, alone, with a stop rule, measured and projected labelled apart. Parallel agents distort measurements.
- **A builder's report is a claim.** Every build, integration and document gets a checker that reproduces from `HEAD` in its own clone; evidence from uncommitted stubs does not count. An integrator's "all green" routinely hides a blocker the verifier finds.
- **Verifiers are adversarial.** A claim is wrong until confirmed at `file:line`, in current docs, or in a query result. In an audit, a finding counts only if its evidence reproduces. Verifiers never paste a credential or sensitive value; scan the generated docs after each research run.
- **Grade what the consumer reads.** After any fan-out from one shared brief, audit the outputs (P16): a rule in the brief spreads to every batch.
- **Prove at each commit.** Fold each fix into its item and prove every item at its own commit in a fresh clone (P9). After any history rewrite, keep a backup branch and confirm the tip's tree is unchanged.
- **Facts by scripts, prose by agents** (P14). A script places each item's "How tested" and refuses to open the PRs when a branch is not at its expected SHA.
- **Name the surface.** Unit tests are not the local environment, the local environment is not a deployed one, and a deployed environment is not production. A result proven locally is "local only" until it runs further.
- **List the fidelity gaps:** what the environment cannot test, such as a vendor with no fake or production data volumes. Raise them with the owner when the design is chosen, and name them in every PR's "How tested".
- **Stop on a security flag.** When the harness flags a subagent action as a possible policy violation, or an agent reports a destructive git command, check the branch tip, the remote, the other worktrees and the shared stash, and find the exact command, before building on the result.

## Outward actions and approval

- **Never merge, approve or turn on auto-merge for a PR,** pr-train's monitored merge and `gh stack merge` included, unless the owner asks for that PR. Never trigger a production deploy.
- **Needs the owner's yes:** pushing, opening PRs, requesting reviewers, tracker writes, chat messages, creating or running a scheduled agent, real-world actions, any write outside the repo, and anything that creates work for other people or acts as the owner's account. A yes covers one task and the scope it named. Record standing ones in memory with their scope.
- **A conditional go is a condition to check.** For "if nothing blocks, open the stack", say why nothing blocks before you act.
- **Make it fit to publish before you ask.** Never request a push, a PR or a shared upload while confirmed high-severity findings are open.
- **Do not leave an approval prompt waiting while the owner may be away.** Ask where you would pause anyway, with background work running.
- **A declined action stops that line of work.** Do not retry it or route around it. Record it as paused in the tracker and memory, say so plainly, take the owner's latest message, and raise it again only when they reopen it or at hand-off.
- **Build for the team.** Anything a person must recreate lives in the repo: scheduled-agent prompts, skills, specs.
- **Other engineers' work.** Do not block on reviewers, never edit what another engineer authored (comment instead), and request reviewers only when the owner says so.
- **CI, infrastructure and the deploy workflows** are off-limits unless the owner opens them.
- **Search for prior art before creating:** tracker issues and projects, open PRs (`gh pr list --search`), existing specs and skills.

## Traps

- **Handing back on belief.** Check what you can check before asking the owner.
- **`cwd` drift.** Use absolute paths and `git -C`. Branches move under concurrent sessions; pin SHAs and verify a tip before rebasing or pushing.
- **Per-agent worktrees** are not necessarily at your tip and stay on disk when changed. Pin the base (P6); at hand-off remove only the ones you created, once the owner agrees.
- **Branches deleted on merge.** If the repo deletes head branches on merge, re-push or rebase dependent branches after each merge.
- **`gh stack` state is shared** across worktrees and not refreshed by fetch; compare heads with `git ls-remote` before `gh stack push`.
- **Tracker drift.** Update the tracker as each item lands, not when the owner asks whether it is current.
- **Context runs out.** Keep decisions in memory and each run's outcome in a scratch report as you go. After a context reset or compaction, re-read them before acting.

## Where things live

- **Memory:** the project's dated log of goals, decisions, hazards and standing authorizations, plus one entry per standing rule the owner sets.
- **Scratch space:** run scripts, briefs, extracted reports, harness scripts such as `stack-verify.sh`, PR bodies, evidence logs.
- **`specs/`:** research (`<topic>-research.md` plus `research-findings/<topic>/`), designs and `*-todo.md` plans. If the specs directory is committed, they ship in a docs PR and are scanned for secrets and sensitive data first.
- **The repo:** skills, scheduled-agent prompts, the workflow context file.
- **The tracker:** the project's record of state. The owner checks it and starts work from it.
