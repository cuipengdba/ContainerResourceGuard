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

Current status: protocol prepared; no native result claimed by this document yet.
Raw reports, traces and failed attempts must be retained before this status is
updated. A test-driver correction requires a new frozen revision and keeps the
earlier failed evidence. Results can advance the generic concurrency evidence
for P03.3/P05.2; they do not close vendor/aged acceptance, actual legacy-binary
migration, or stable-release gates. The original 52 definitions remain intact.
