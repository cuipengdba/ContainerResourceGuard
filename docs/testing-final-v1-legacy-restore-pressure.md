# Final candidate: legacy hard-memory restoration under concurrency

This is a new, independent native-kernel qualification, not a change to CRG's
current memory policy. New limits still use `memory.high`. The test harness alone
writes `memory.max` to simulate a previously owned legacy limit and an external
writer. No DBS/HISDBS test container or live long-duration job is touched.

The protocol is frozen in [the machine-readable plan](test-plan-final-v1-legacy-restore-pressure.json).
It uses the exact final-version ELF from source
`ced461705ebc27315a59aefe463f9b4af47130a3`, built with Go 1.27.3.
Production source files, the final ELF identities and the long-duration plan are
unchanged. Four native environments are planned: Ubuntu 22.04/24.04 on amd64/arm64.
The first dispatch is a single-environment pilot; only after its evidence is
reviewed may the remaining three environments use the same frozen protocol.

## Actual fixtures and acceptance

Each case owns one labelled scratch container, one placeholder PID1 and a bounded
memory-allocation/fsync worker. Only the stable-window case runs a persistent
Agent, with at most one Agent in that container. The candidate's read-only
discovery must match the harness's exact Docker leaf cgroup and process identity.
All writes and cleanup are guarded by that ownership. No parent cgroup is written.

The harness first records an actual 128MiB hard limit while use is safely lower,
raises it to 512MiB, and writes a valid version-1 journal with the candidate's
current discovered identity. **This journal is synthetic**: this does not prove
that an old published binary produced the state or that an actual old-version
upgrade was exercised.

1. With 192MiB physically touched allocation, restore must defer the unsafe
   hard-limit reduction, retain ownership, and complete after memory is released.
2. While the complete pending journal is still unpublished, allocate 192MiB.
   Restore must recheck safety after persistence and retain the 512MiB hard cap.
3. At the same persistence barrier, an external writer sets 384MiB. Restore must
   retain that value and persist a visible conflict, including on retry. Only
   when the external owner returns the original value may CRG forget the entry.
4. A live Agent applies a CPU-only manual policy while an unsafe legacy memory
   restoration remains pending. After release, the same Agent must observe its
   five-second stability window, restore memory, and subsequently disable/restore
   CPU without interrupting the placeholder or fsync worker.

Cases 2/3 use the system `strace` and
`-e inject=fsync:delay_enter=5s`. This delays entry to the real fsync syscall; it
does not inject successful return values. A complete uniquely named pending
temporary file, unchanged published journal before and after the concurrent
action, retained temporary file, and a matching `(DELAYED)` trace entry are all
required. These are deliberately delayed journal-persistence tests, **not a
measurement of a physically slow/full disk or a power-loss durability test**.
See the [upstream strace manual](https://github.com/strace/strace/blob/master/doc/strace.1.in)
for injection semantics.

Every case requires unchanged unrelated controls, continued fsync progress,
unchanged observed cgroup OOM counters, unchanged PID1, owned Docker/cgroup removal,
and termination of the process identities actually observed by this harness.
These counters describe this bounded run; they do not promise OOM is impossible.

## Scope and result status

The driver refuses non-GitHub-hosted execution, missing explicit test marker,
non-root, architecture mismatch, non-v2, a remote Docker endpoint, insufficient
host headroom, or another already running Docker fixture. It neither discovers
nor operates DBS/HISDBS containers. Test dependencies are copied into a scratch
image only; they are not part of the product or vendor image.

Current status (2026-11-16 CST): **116/116 checks, all 16 cases and owned
cleanup passed** across the four planned native environments. No driver, helper,
plan, runtime source or final ELF change was needed between pilot and remaining
dispatches. The initial pilot was independently reviewed before expansion.

| Runner | Actual architecture/kernel | Checks |
| --- | --- | --- |
| ubuntu-24.04 | amd64 / 7.0.0-1017-azure | 29/29 |
| ubuntu-22.04 | amd64 / 6.8.0-1070-azure | 29/29 |
| ubuntu-22.04-arm | arm64 / 6.8.0-1070-azure | 29/29 |
| ubuntu-24.04-arm | arm64 / 7.0.0-1017-azure | 29/29 |

Actual Actions runs: [pilot 43736213350](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/43736213350),
[remaining 43736560710](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/43736560710).
Both used qualification commit `09550dde8034171dedc36b2ece80d45742095ba7`;
the product source remains the separately pinned `ced4617...` revision above.

The [four exact downloaded ZIP archives](test-evidence-final-v1-legacy-restore-pressure.json.gz)
preserve all 108 member byte sequences, including reports, complete delayed-fsync
traces, worker acknowledgements, logs, journals, frozen inputs and environments.
Every full ZIP was checked against its GitHub artifact API SHA-256, then each
member was CRC/length/SHA-256 checked. Run identity/result fields are selected;
commit author emails are omitted from the public metadata, without altering any
ZIP or member. No credentials or signed download URLs are archived.
The [independent offline review](test-results-final-v1-legacy-restore-pressure.json)
recomputes all four identities, source/input bindings, named persistence barriers,
deferred/conflict/readback outcomes, OOM counter deltas, worker progress and
observed cleanup. It can be repeated without running CRG:

```sh
python3 tests/legacy-restore-pressure-v1/review.py \
  --evidence docs/test-evidence-final-v1-legacy-restore-pressure.json.gz \
  --plan docs/test-plan-final-v1-legacy-restore-pressure.json
```

Raw reports, traces and any failed attempts must remain archived. A test-driver
correction requires a new frozen revision and keeps earlier failed evidence. Results can advance the generic concurrency evidence
for P03.3/P05.2; they do not close vendor/aged acceptance, actual legacy-binary
migration, or stable-release gates. The original 52 definitions remain intact.
