**EtharaOrion sample delivery — Quality Assessment**

**Scope:** 10 repos, 30 tasks, and 336 vendor rollouts. Opus-5 covers all 30 tasks; GLM-5.3 covers 12\.

**Benchmark categories**

| Category | Repo | Task type | Sampled work |
| ----- | ----- | ----- | ----- |
| Hard SWE and Real Coder | argos | Fix or add features in existing public repos from issue/PR descriptions | Scapy RTCP, Molecule theme API, Air documentation/code generation |
| Code Understanding | teresa | Read a large repo, trace code and dependencies, and write an explanation; no code change expected | Function localization in PyCBC; dependency tracing in ARO-HCP and IoTDB |
| Greenfield (spec-to-code) | deku | Build a complete web app from a long written product spec | Talent roster, mass-balance system, hardware storefront |
| Terminal Tasks | anubis | Inspect and operate a local simulator/service through CLI and API, then produce required state and reports | Service reconciliation, wire-data debugging, scorer recovery |
| MCP Tool Calling | yuji | Use MCP tools across several apps and source documents, then update state or produce reports | Fishery restatement, transport-program return, berth survey |
| Code Security | kakashi | Reproduce a vulnerability, submit a PoC and patch, and pass held-out checks | Rekor, SQLite, and PyJWT security bugs |
| DevOps | kanao | Diagnose and repair operational systems | CI/roster pipeline, monitoring diagnosis, IaC policy guardrails |
| Code Migration | thanatos | Move an existing project to a newer framework or client API while preserving behaviour | Flask→Django, date/test modernization, HTTP-client migration |
| Long Horizon | levi | Complete complex, multi-file issue work in mature repos | Reflex event namespace; Changedetection.io UI and API work |
| Multi-Repo RL Environments | envora | Read a reference repo while editing one target repo (read-across-edit-one) | Xarray, TiDB, and PD cross-repo tasks |

**Verdict**

What is good. The delivery covers 10 distinct task types: public-repo fixes, code understanding, greenfield apps, terminal operations, MCP tools, security, DevOps, migration, long-horizon work, and cross-repo work. All 336 vendor rollout traces are present, with real actions, eight runs per configuration, no missing run IDs, and no final tool-call truncation. Several tasks show useful deterministic signal once their setup issues are fixed.

Main concerns. Reward integrity is the largest problem: wrong or fake work can score highly, while correct work can score zero. The task files also target an old Harbor schema, the vendor runs depend on different harness wrappers that are not shipped, and key environment or grader artifacts are missing: 9 private images, Yuji's MCP server, Deku's grader modules, and the LLM judge used by all 30 tasks. These gaps make many failures look like model failures when they are setup or grading failures.

| Repo | What is good | Main concern |
| ----- | ----- | ----- |
| thanatos | Three distinct migration targets; detailed truth.md | Test channel is absent for all 3 tasks; 394d9d5c gold is broken |
| yuji | Diverse MCP research and cross-app state tasks; score components are preserved | MCP server is missing; Brackenmere fake trajectory gets channel A 1.0 |
| teresa | Real-repo code tracing; re-scored answers show usable differentiation | Stock Harbor loses the answer; keyword or negated answers can score 1.0 |
| deku | Rich end-to-end web-app specifications | Grader modules are missing and there is no working reference solution |
| argos | Real public-repo issue work; most score weight is deterministic | Images are private; sampled tests require hidden exact identifiers |
| levi | Complex multi-file public-repo work; most score weight is deterministic | Images are private; sampled tests contain hidden or out-of-scope checks |
| envora | Cross-repo read-across-edit-one design; xarray oracle reaches 496/496 after a one-line fix | Shipped xarray verifier has a cwd bug; an added conftest.py can disable tests |
| anubis | Stateful CLI/API tasks with complete, rich trajectories | Each sampled grader has an integrity issue: hidden token, self-reported state, or missing control data |
| kakashi | Clear PoC/patch/held-out stages; correct PyJWT patch can reach 1.0 | Partial fix can score below zero; real-CVE prompts were refused in our Harbor setup |
| kanao | Three distinct DevOps types; deterministic results reproduce | One task has a format floor, one is all-or-nothing, and one penalizes an allowed edit |

---

**1\. Cannot be built or scored**

| Sub-issue | Tasks | Evidence |
| ----- | ----- | ----- |
| Private images | argos 3, levi 3, thanatos 3 | Docker pull returns access denied |
| MCP server missing | yuji 3 | light-servers:latest has no source and cannot be pulled |
| Grader pieces missing | deku 3 | score.py, run\_workflows.py, appclient absent |
| Test channel absent | thanatos 3 | 24/24 runs vacuous; targets\_total \= 0 |
| Oracle fails shipped verifier | envora xarray | oracle gets 0/496; one-line cwd fix reaches 496/496 |
| Broken gold solution | thanatos 394d9d5c | builds 405 OK; its truth.md warns against this |
| Grader loses answer | teresa 3 | gold answer exists; grader says no answer |
| Model refuses under our setup | kakashi 2 | Harbor 0.20.0 \+ claude-code 2.1.270: Opus-5 refused 6/6; Sonnet also refused |

**1.1 Missing assets**

**Issue.** Twelve tasks cannot start from the delivered files.

**Evidence.** The 9 argos/levi/thanatos images point to a private ECR and return pull access denied. Yuji needs light-servers:latest; no build context exists and the image cannot be pulled.

**Citations.** Tasks: argos-samples/1213efa9-10ca-4f0e-bb27-2f6012454212/environment/Dockerfile, levi-samples/56e866ec-41f7-428b-9c91-51b9787ce934/environment/Dockerfile, thanatos-samples/394d9d5c-357d-56c2-81e5-e0a2d32ab101/environment/Dockerfile, yuji-samples/ef85f022-406d-450f-b299-081df04fac0b/environment/docker-compose.yaml. Environment-level issue; no rollout is needed to reproduce it.

**1.2 Missing or broken graders**

**Issue.** Some bundles cannot produce a valid score.

**Evidence.** Deku calls three missing modules and has no working reference solution. Thanatos has no test command or F2P/P2P config: all 24 runs are vacuous, even when repo tests pass.

Envora xarray runs pytest from the wrong directory, where xarray/typing.py shadows Python's typing. Its oracle moves from 0/496 and reward 0.0 to 496/496 and reward 1.0 after a one-line cwd fix.

**Thanatos gold is also broken.** 394d9d5c formats every WSGI status as f'{status\_code} OK', so a 405 becomes 405 OK—the exact bug its own truth.md warns against. The gold was never verified and Django is unavailable with network off.

**Citations.** Tasks: deku-samples/1b21d4ac-055a-52e7-b754-0620f337b0d4/tests/test.sh, thanatos-samples/394d9d5c-357d-56c2-81e5-e0a2d32ab101/tests/config.json, envora-samples/0a463270-a79e-45d1-8102-af28bec64c47/tests/run\_tests.py. Vendor trajectory: thanatos-samples/394d9d5c-357d-56c2-81e5-e0a2d32ab101/trajectories/claude-opus-5/run\_3/result.json. 

**1.3 Teresa loses answers between containers**

**Issue.** Stock Harbor cannot pass the answer to the separate verifier.

**Evidence.** Harbor's oracle wrote a 23,928-byte gold answer.md; the grader still raised no agent answer available to grade and returned the null floor. Re-scoring the same final replies at the expected path gave means 0.52 / 0.30 / 0.35 instead of 0.018 / 0.097 / 0.028.

**Citations.** Task: teresa-samples/7b2e7cd5-f024-42b1-bfb1-ee00b783ef43. Vendor trajectory: teresa-samples/7b2e7cd5-f024-42b1-bfb1-ee00b783ef43/trajectories/claude\_opus\_5/run\_1/.

**1.4 Security tasks trigger model safeguards in our setup**

**Issue.** The task asks for working exploits for real CVEs.

**Evidence.** Under our Harbor 0.20.0 \+ claude-code 2.1.270 setup, all 6 Opus-5 attempts ended safeguards flagged this message (AUP). One Sonnet-4-6 confirmation attempt also refused. The vendor's GitHub rollouts did not show refusals, so this is specific to our current model-access and policy setup; it does not prove every model or harness will refuse.

**Citations.** Tasks: kakashi-samples/7658f933-e5ad-4ce1-b9fa-0e1d75badb0e 2, kakashi-samples/6e02e468-4f80-4fa7-96aa-2c3b0db7c14e. 

---

**2\. Reward without doing the work**

| Task | Invalid submission | Score |
| ----- | ----- | ----- |
| teresa dc51ee50 | answer says the opposite of truth | **1.0** |
| teresa other 2 | short keyword list | **1.0** |
| yuji Brackenmere | fake trajectory \+ 4 junk files | **channel A 1.0** |
| anubis 28a5e9c3 | made-up report; service never starts | **1.0** |
| envora xarray | null code \+ xfail hook | **1.0** |
| kakashi pyjwt | correct patch \+ garbage reproducer | 0.75–0.96 |
| yuji Wraysbury | perfect state, nothing delivered | channel A 0.439 |
| kanao 8aef516b | wrong diagnosis with valid format | 0.074 |
| teresa, argos, levi | null submission | nonzero floor: 0.018–0.097 / about 0.045–0.058 |

**2.1 Text and trajectory matching can be faked**

**Issue.** Graders look for words, not truth.

**Evidence.** Teresa's linked() checks token distance with no negation handling. A 91-word answer saying ExecuteConvertRequest never calls mapstructure.Decode scored 1.0. Keyword lists also scored 1.0 on the other two tasks.

Yuji only checks that an MCP-shaped trajectory response contains 13 strings. A fabricated 6-step trajectory plus junk files scored channel A 1.0. The junk files alone scored 0.58, above every real run. In Yuji Wraysbury, perfect MCP state with nothing delivered scored channel A 0.439, 2.2 times the best real run.

**Citations.** Task: teresa-samples/dc51ee50-0468-41e6-9d58-3aab71e222f8. Teresa vendor trajectory: teresa-samples/dc51ee50-0468-41e6-9d58-3aab71e222f8/trajectories/claude\_opus\_5/run\_1/. Yuji vendor trajectories: yuji-samples/ef85f022-406d-450f-b299-081df04fac0b/trajectories/opus.5/run\_2/, yuji-samples/ef85f022-406d-450f-b299-081df04fac0b/trajectories/opus.5/run\_5/.

**2.2 Self-reported output can replace real work**

**Issue.** Anubis grades files the agent writes, not service activity.

**Evidence.** The task asks the agent to use a service through its CLI and API. But the grader only checks the final report files written by the agent. It does not verify that the service was actually used. For example, a script read plan.json, never started the service, and wrote the expected report. It scored 1.0 and matched the oracle output byte for byte.

**Citations.** Task: anubis-samples/28a5e9c3-0169-57f6-a810-d36a6a7db9d4. Vendor trajectories: anubis-samples/28a5e9c3-0169-57f6-a810-d36a6a7db9d4/trajectories/claude-opus-5/run\_7/, anubis-samples/28a5e9c3-0169-57f6-a810-d36a6a7db9d4/trajectories/glm-5.3/run\_4/.

**2.3 An added conftest.py can disable graded tests**

**Issue.** The agent can add a pytest hook that changes how the graded tests run.

**Evidence.** We added xarray/tests/conftest.py and marked the 3 F2P tests xfail. Reward changed 0.0 → 1.0 with no product-code change. Separate mode does not remove this file: it is part of the agent workspace that must be copied to the verifier. The grader hashes declared test files but does not reject a new conftest.py.

**Citations.** Task: envora-samples/0a463270-a79e-45d1-8102-af28bec64c47. Vendor trajectories: envora-samples/0a463270-a79e-45d1-8102-af28bec64c47/trajectories/opus-5/run\_7/, envora-samples/0a463270-a79e-45d1-8102-af28bec64c47/trajectories/opus-5/run\_6/.

**2.4 The pyjwt reproducer is almost ungraded**

**Issue.** Garbage input receives nearly full credit.

**Evidence.** With the correct patch, the real reproducer scores 1.0, not-a-token scores 0.958, and 16 random bytes score 0.75. Only 1 of 24 points verifies that the submitted input reproduces the bug.

**Citations.** Task: kakashi-samples/7658f933-e5ad-4ce1-b9fa-0e1d75badb0e 2. Vendor trajectories: kakashi-samples/7658f933-e5ad-4ce1-b9fa-0e1d75badb0e 2/trajectories/claude-opus-5/run\_4/, kakashi-samples/7658f933-e5ad-4ce1-b9fa-0e1d75badb0e 2/trajectories/claude-opus-5/run\_5/. 

**2.5 Floors reward form rather than correctness**

**Issue.** Some tasks give points for formatting or doing nothing.

**Evidence.** Kanao 8aef516b gives 8/27 points for valid shape and signed evidence before checking the diagnosis. After two fixed penalties, a wrong diagnosis scores 0.074074 — exactly all 8 vendor Opus runs.

Teresa's null floors are 0.018 / 0.097 / 0.028. Argos/levi soft checks give estimated null score\_eval 0.045–0.058, close to reported 6.32% and 3.03% on weak tasks.

**Citations.** Task: kanao-samples/8aef516b-702c-5660-a8f0-da85401c9170. Vendor trajectories: kanao-samples/8aef516b-702c-5660-a8f0-da85401c9170/trajectories/opus-5/run1/, kanao-samples/8aef516b-702c-5660-a8f0-da85401c9170/trajectories/glm-5.3/run1/.

---

**3\. Correct work scores poorly**

| Task | Single change | Deterministic before → after |
| ----- | ----- | ----- |
| anubis fb2f26ec | hidden emit → visible omit | 1.0 → **0.04** |
| kakashi pyjwt | remove one wiring hunk from real fix | 1.0 → **−0.04** |
| kanao e79449a4 | leave one fault of about 20 | 1.0 → **0.0** |
| anubis 45421e59 | follow instruction Rule 1 | 1.0 → **0.12** |
| envora pd | remove id from error text | F2P 4/4 → 3/4 |
| envora tidb | omit hidden cap(respChan)==18 | F2P 1/1 → 0/1 |
| kanao 58081829 | comment in allowed file | 1.0 → 0.88 |

**3.1 Tests require hidden implementation details**

**Issue.** Tests grade names, strings, paths, line numbers, or strategy invented by the gold patch.

**Evidence.** Examples:

* argos 46ab8719: brief shows getCurrentTheme(), tests require getColorThemeMode();  
* levi 8ab81969: tests insert hidden CSS class has-unread-changes about 101 times;  
* envora pd: exact text Load keyspace id 42 failed is required;  
* envora tidb: only F2P check requires private cap(tasks\[0\].respChan) \== 18;  
* teresa: literal source lines 102, 109, and 119 are required;  
* anubis 28a5e9c3: report.json, summary.json, and transcript\_summary.json must match the gold's exact keys, flat fields, values, and ordering;  
* thanatos: requires monkeypatch.setattr and rejects other valid mocking methods;  
* levi 5fee266c: grades UTF-8 work from PR \#613, outside every listed issue.

**Citations.** Tasks and vendor trajectories: argos-samples/46ab8719-a8fe-496f-95a5-42f3bc3def5d/trajectories/opus-5/run\_1/, levi-samples/8ab81969-37a0-4f3b-86af-d21560f386ce/trajectories/opus-5/run\_7/, envora-samples/0aa780ad-18f8-4351-8479-181363b32ea5/trajectories/opus-5/run\_1/, envora-samples/0aa40af6-f27f-4a2c-afda-d0ea4d0bc7e7/trajectories/opus-5/run\_4/, teresa-samples/dc51ee50-0468-41e6-9d58-3aab71e222f8/trajectories/claude\_opus\_5/run\_1/, thanatos-samples/72dcd7c9-00f7-5c07-a9db-749525a450e4/trajectories/claude-opus-5/run\_4/, levi-samples/5fee266c-fa53-41c7-bdbd-285e188670ac/trajectories/opus-5/run\_5/.

**3.2 Harsh gates erase useful partial credit**

**Issue.** One small mismatch can remove most or all reward.

**Evidence.** Anubis fb2f26ec requires hidden word emit, while visible sample code uses omit. Changing only report → emit in a shipped run lifts 0.041 → 0.863. The oracle with omit falls 1.0 → 0.041.

Kakashi pyjwt treats a real partial repair as cheating, cancels 6 tests, and scores −0.0417. Kanao e79449a4 has three deterministic tests of weights 5/1/5 that all check the same full condition; three different one-fault mutants each get deterministic score 0\. The reported nonzero reward comes from the separate judge channel.

**Citations.** Tasks: anubis-samples/fb2f26ec-6595-5389-8b6d-36e52ebf086b, kakashi-samples/7658f933-e5ad-4ce1-b9fa-0e1d75badb0e 2, kanao-samples/e79449a4-8366-58aa-aa5d-889f4bec9949. Vendor trajectories: anubis-samples/fb2f26ec-6595-5389-8b6d-36e52ebf086b/trajectories/claude-opus-5/run\_7/, kakashi-samples/7658f933-e5ad-4ce1-b9fa-0e1d75badb0e 2/trajectories/claude-opus-5/run\_5/, kanao-samples/e79449a4-8366-58aa-aa5d-889f4bec9949/trajectories/opus-5/run1/.

**3.3 Instructions conflict with graders**

**Issue.** Required or allowed work loses points.

**Evidence.** Kanao 58081829 allows workspace code edits, but adding one comment to run-roster reduces reward 1.0 → 0.88. Anubis 45421e59 tells the agent to read control figures, but the held-out corpus omits them; following the rule gives 26 missing-file errors and reward 0.124.

**Citations.** Tasks: kanao-samples/58081829-7357-565c-9c37-7ba5936394af, anubis-samples/45421e59-0daa-505b-9656-e565f93c491c. Vendor trajectories: kanao-samples/58081829-7357-565c-9c37-7ba5936394af/trajectories/opus-5/run6/, anubis-samples/45421e59-0daa-505b-9656-e565f93c491c/trajectories/claude-opus-5/run\_1/. 

---

**4\. LLM judge problems**

| Sub-issue | Example | Evidence |
| ----- | ----- | ----- |
| Judge trusts claims over tests | argos d7ecc24d | rubric 1.0; 16 test failures; 0/6 targets |
| Similar work gets different verdicts | thanatos 739bc356 | 3 criteria flip |
| Same code gets different verdicts | levi 56e866ec | maintainability flips |
| Judge grades intent | envora xarray | rubric passes while matching tests fail |
| Transcript is incomplete | anubis 28a5e9c3 | judge sees 0 calls; trace has 15 |
| Hidden judge rule | envora tidb | weight-5 unstated session variable |
| Judge is unpinned | several | no seed or temperature |
| Judge code absent | all 30 | full score cannot be recomputed |

**4.1 Judge and tests disagree**

**Issue.** Broken code can earn strong rubric credit.

**Evidence.** An argos d7ecc24d GLM run gets rubric 1.0 while failing 16 tests and hitting 0/6 targets. Envora xarray gets high-weight rubric passes while tests for the same behaviours fail.

**Citations.** Vendor trajectories: argos-samples/d7ecc24d-0b47-4f1e-a4a8-e941d31e6f5f/trajectories/glm-5.3/run\_6/, envora-samples/0a463270-a79e-45d1-8102-af28bec64c47/trajectories/opus-5/run\_7/, envora-samples/0a463270-a79e-45d1-8102-af28bec64c47/trajectories/opus-5/run\_6/.

**4.2 Judge results are inconsistent and unpinned**

**Issue.** Similar work gets different decisions, with no seed or temperature recorded.

**Evidence.** Three thanatos criteria flip across same-scope runs. Levi maintainability flips on byte-identical code. The review found judge-nondeterminism issues on yuji, deku, thanatos, and teresa. On kanao e79449a4 and two thanatos tasks, this channel owns effectively 100% of reward.

**Citations.** Vendor trajectory pairs: thanatos-samples/739bc356-7e4e-5f45-8af0-ada3a0429dde/trajectories/claude-opus-5/run\_2/ and thanatos-samples/739bc356-7e4e-5f45-8af0-ada3a0429dde/trajectories/claude-opus-5/run\_4/; levi-samples/56e866ec-41f7-428b-9c91-51b9787ce934/trajectories/opus-5/run\_7/ and levi-samples/56e866ec-41f7-428b-9c91-51b9787ce934/trajectories/opus-5/run\_2/; yuji-samples/ef85f022-406d-450f-b299-081df04fac0b/trajectories/opus.5/run\_2/ and yuji-samples/ef85f022-406d-450f-b299-081df04fac0b/trajectories/opus.5/run\_5/.

**4.3 Judge input and rules are wrong**

**Issue.** The judge can see incomplete evidence or enforce hidden requirements.

**Evidence.** Anubis's judge says no tool calls, while the trajectory has 15 and 84,668 characters of observations. Estimated loss is 12.8 points, enough to change its difficulty tier.

Other hidden rules include an envora session variable, an error style used by envora's gold, and migration of thanatos files not named in the task.

**Citations.** Task: anubis-samples/28a5e9c3-0169-57f6-a810-d36a6a7db9d4. Vendor trajectory and judge result: anubis-samples/28a5e9c3-0169-57f6-a810-d36a6a7db9d4/trajectories/claude-opus-5/run\_7/agent/trajectory.json, anubis-samples/28a5e9c3-0169-57f6-a810-d36a6a7db9d4/trajectories/claude-opus-5/run\_7/verifier/score.json. Other judge findings: envora-samples/0aa40af6-f27f-4a2c-afda-d0ea4d0bc7e7/trajectories/opus-5/run\_2/, thanatos-samples/739bc356-7e4e-5f45-8af0-ada3a0429dde/trajectories/claude-opus-5/run\_4/.

**4.4 Judge code is not shipped**

**Issue.** No task can recreate its full score.

**Evidence.** The runner, prompt, and reducer are absent. The judge owns 100% of reward on kanao e79449a4 and two thanatos tasks, about 5–10% on argos/levi/envora, and about 50% or more on most others.

**Citations.** Representative tasks and scored trajectories: kanao-samples/e79449a4-8366-58aa-aa5d-889f4bec9949/trajectories/opus-5/run1/, thanatos-samples/72dcd7c9-00f7-5c07-a9db-749525a450e4/trajectories/claude-opus-5/run\_1/, argos-samples/1213efa9-10ca-4f0e-bb27-2f6012454212/trajectories/opus-5/run\_1/.

---

**5\. Environment and reproducibility**

| Sub-issue | Scope | Evidence |
| ----- | ----- | ----- |
| Old Harbor schema | 24 tasks | pass on 0.2.0; fail on 0.3.0+ |
| Invalid TOML | deku 3 | fail on all 17 versions tested |
| Harness-specific output | teresa, envora | stock Harbor cannot reproduce vendor runs |
| Silent broken build | envora Go 2 | dependency fetch errors are ignored |
| Network mismatch | anubis, kanao, levi | internet allowed or used despite offline claims |
| Grading state leak | deku | browser pass changes data before pytest |
| Unpinned delivery | most tasks | CSV normally points at main |

**5.1 Old task schema**

**Issue.** Most tasks do not load on current Harbor.

**Evidence.** Across 17 releases, 30/33 task files validate on Harbor 0.1.45–0.2.0, but only 6/33 on 0.3.0–0.23.0. The denominator includes 30 CSV tasks plus 3 transient kanao tasks. Harbor 0.3.0 changed author, name, and network fields, so 24 tasks need migration rather than a rewrite.

Deku's 3 are truly invalid TOML: authors \= \[ { "email" } \] fails every tested version.

**Citations.** Task files: all \*-samples/\*/task.toml. Deku example: deku-samples/1b21d4ac-055a-52e7-b754-0620f337b0d4/task.toml.

**5.2 Harness-specific delivery**

**Issue.** Vendor runs depend on wrappers that are not documented or shipped.

**Evidence.** Teresa needs OpenHands to write answer.md. Envora blocks network, so stock Harbor cannot install claude-code, while vendor runs used claude-code 2.1.263. Only deku names a Harbor version.

**Citations.** Vendor harness evidence: teresa-samples/7b2e7cd5-f024-42b1-bfb1-ee00b783ef43/trajectories/claude\_opus\_5/run\_1/config.json, envora-samples/0aa780ad-18f8-4351-8479-181363b32ea5/trajectories/opus-5/run\_1/config.json.

**5.3 Builds and network settings hide failure**

**Issue.** Builds can succeed with no dependencies, and network settings do not match actual use.

**Evidence.** Envora wraps Go fetch/build commands in || true; 572 fetches failed, yet Docker exited 0 with an empty cache.

Anubis and kanao allow internet despite offline claims. Levi downloads 9–10 MB during verification despite network\_mode \= "none". Several graders also need undocumented keys or nonces.

**Citations.** Tasks: envora-samples/0aa40af6-f27f-4a2c-afda-d0ea4d0bc7e7/environment/Dockerfile, envora-samples/0aa780ad-18f8-4351-8479-181363b32ea5/environment/Dockerfile.

**5.4 Grading phases and source revisions are not isolated**

**Issue.** Grading can alter its own test state, and source can change during review.

**Evidence.** Deku runs browser workflows before pytest; a workflow creates records that later break exact-count tests. A shipped run also has 7 unresolved judge checks due to a 400 response.

Kanao main moved back two commits during review. The 3 CSV tasks stayed byte-identical, but only deku is pinned to a commit in the CSV. Every task should be pinned.

**Citations.** Task and vendor trajectories: deku-samples/1b21d4ac-055a-52e7-b754-0620f337b0d4/tests/test.sh, deku-samples/1b21d4ac-055a-52e7-b754-0620f337b0d4/trajectories/opus-5/run\_4/, deku-samples/1b21d4ac-055a-52e7-b754-0620f337b0d4/trajectories/opus-5/run\_5/. Kanao revision evidence: repo commits eebd0b2 and 66fcc4f; the three CSV task trees have no diff between them.

---

**6\. Rollouts and reporting**

| Sub-issue | Scope | Evidence |
| ----- | ----- | ----- |
| Rollout files are complete | all 336 | no gaps or truncation; real calls |
| Reward fields disagree | yuji | 3 meanings for reward |
| Setup failure counted as model failure | 5 families | missing state/tools/deps/network becomes 0 |

**6.1 Rollout structure is good**

**Strength.** All 336 vendor runs contain real action traces and 8 runs per configuration. We found no missing run IDs or final tool-call truncation.

**Citations.** All vendor rollout paths are indexed in \_review/rollouts.json. Example task: argos-samples/1213efa9-10ca-4f0e-bb27-2f6012454212/trajectories/ (16 runs).

**6.2 Reward fields are unclear**

**Issue.** One run can carry several different values called reward.

**Evidence.** Yuji Leith run 1 has combined percent 16.26, rubric-only 0.2877, and test-only percent 2.33 in three files. No common schema says which is authoritative.

**Citations.** Task and vendor trajectory: yuji-samples/4a0bf18e-5fb9-4a65-b73a-5b128920e357/trajectories/opus.5/run\_1/. Compare yuji-samples/4a0bf18e-5fb9-4a65-b73a-5b128920e357/trajectories/opus.5/run\_1/verifier/reward.json, yuji-samples/4a0bf18e-5fb9-4a65-b73a-5b128920e357/trajectories/opus.5/run\_1/verifier/score.json, and yuji-samples/4a0bf18e-5fb9-4a65-b73a-5b128920e357/trajectories/opus.5/run\_1/report.json.

**6.3 Setup failures are scored as model failures**

**Issue.** Pass rates mix capability with broken infrastructure.

**Evidence.** Yuji 83d7e97e never captures end\_env.json, so 11 high-weight tests fail regardless of work. Other examples: yuji timeout/tool errors; kanao collection errors; levi's forbidden network download; thanatos missing dependencies; teresa missing pytest. These should be invalid trials, not failures.

**Citations.** Vendor trajectories: yuji-samples/83d7e97e-2aed-4b23-a906-45f5a6a6a4da/trajectories/opus.5/run\_5/, yuji-samples/83d7e97e-2aed-4b23-a906-45f5a6a6a4da/trajectories/opus.5/run\_1/, levi-samples/8ab81969-37a0-4f3b-86af-d21560f386ce/trajectories/opus-5/run\_7/, thanatos-samples/394d9d5c-357d-56c2-81e5-e0a2d32ab101/trajectories/claude-opus-5/run\_3/.

