#!/usr/bin/env bash
# Isolated PostgreSQL engine regression, not vendor DBS/HISDBS API acceptance.
# Run as an unprivileged database OS user with PG_BINDIR and a NEW work path.
set -euo pipefail
: "${PG_BINDIR:?explicit PostgreSQL binary directory required}"
: "${CRG_PG_WORK:?new disposable working directory required}"
[[ $(id -u) != 0 ]] || { echo 'run as database OS user' >&2; exit 2; }
[[ "$CRG_PG_WORK" == /* && ! -e "$CRG_PG_WORK" ]] || { echo 'working path must be new and absolute' >&2; exit 2; }
mkdir -m 0700 -- "$CRG_PG_WORK"
export PATH="$PG_BINDIR:$PATH"
work="$CRG_PG_WORK"
mkdir -m 0700 "$work/socket" "$work/replica-socket" "$work/restore-socket"
cleanup() {
  for data in restore replica primary; do
    [[ ! -e "$work/$data/postmaster.pid" ]] || pg_ctl -D "$work/$data" -m fast -w -t 20 stop >/dev/null 2>&1 || :
  done
}
trap cleanup EXIT
initdb -D "$work/primary" -A trust --no-locale > "$work/initdb.log"
pg_ctl -D "$work/primary" -l "$work/primary.log" -w -t 30 \
  -o "-k $work/socket -p 16432 -c listen_addresses='' -c shared_buffers=32MB -c max_connections=20 -c wal_level=replica -c max_wal_senders=4 -c wal_keep_size=64MB" start
export PGHOST="$work/socket" PGPORT=16432 PGDATABASE=postgres
psql -v ON_ERROR_STOP=1 -c "CREATE TABLE crg_data(id integer PRIMARY KEY,payload text); INSERT INTO crg_data SELECT n,repeat(md5(n::text),4) FROM generate_series(1,20000)n;" > "$work/sql.log"
pg_dump -Fc -f "$work/backup.dump"
pg_basebackup -h "$PGHOST" -p "$PGPORT" -D "$work/replica" -X stream -R -c fast
pg_ctl -D "$work/replica" -l "$work/replica.log" -w -t 30 \
  -o "-k $work/replica-socket -p 16433 -c listen_addresses='' -c shared_buffers=32MB" start
psql -v ON_ERROR_STOP=1 -c "INSERT INTO crg_data VALUES(20001,repeat('streaming-replication',6));" >> "$work/sql.log"
for (( attempt=0; attempt<100; attempt++ )); do
  count=$(psql -h "$work/replica-socket" -p 16433 -Atqc 'SELECT count(*) FROM crg_data' 2>/dev/null || :)
  [[ "$count" == 20001 ]] && break
  sleep 0.1
done
[[ "$count" == 20001 ]] || { echo 'replication did not catch up' >&2; exit 1; }
# The logical backup predates the extra replicated row. Restore into an entirely
# new cluster and compare the original 20,000 rows, not an existing database.
initdb -D "$work/restore" -A trust --no-locale > "$work/restore-initdb.log"
pg_ctl -D "$work/restore" -l "$work/restore.log" -w -t 30 \
  -o "-k $work/restore-socket -p 16434 -c listen_addresses='' -c shared_buffers=32MB -c max_connections=10" start
pg_restore -h "$work/restore-socket" -p 16434 -d postgres --exit-on-error "$work/backup.dump"
query="SELECT count(*)::text||':'||md5(string_agg(id::text||payload,'' ORDER BY id)) FROM crg_data WHERE id<=20000"
original=$(psql -Atqc "$query")
restored=$(psql -h "$work/restore-socket" -p 16434 -Atqc "$query")
[[ "$original" == "$restored" ]] || { echo 'backup restore digest mismatch' >&2; exit 1; }
printf 'PASS postgres-sql rows=20000\nPASS postgres-logical-backup-restore digest=%s\nPASS postgres-streaming-replication rows=20001\n' "$restored"
