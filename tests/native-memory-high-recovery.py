#!/usr/bin/env python3
"""Exercise the actual CRG CLI and v2 controls in disposable PostgreSQL containers."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import tempfile
import time
import uuid


def command(*args, timeout=30):
    proc = subprocess.run([str(arg) for arg in args], capture_output=True, text=True, timeout=timeout)
    if proc.returncode:
        raise RuntimeError(f"{args[:2]} failed ({proc.returncode}): {proc.stdout[-2000:]}\n{proc.stderr[-2000:]}")
    return proc.stdout.strip()


def until(test, seconds, message):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if test():
            return
        time.sleep(0.1)
    raise AssertionError(message)


class Fixture:
    def __init__(self, root, name, binary, nonce, memory):
        self.folder = root
        self.nonce = nonce
        self.container = command(
            "docker", "run", "-d", "--network", "none", "--cgroupns", "host",
            "--privileged", "--label", f"crg.memory-test={nonce}", "--name", f"crg-recovery-{nonce}-{name}",
            "--memory", memory, "--memory-swap", memory, "--shm-size", "256m",
            "-e", "POSTGRES_HOST_AUTH_METHOD=trust",
            "-v", "/sys/fs/cgroup:/sys/fs/cgroup:rw",
            "-v", f"{binary}:/usr/local/bin/crg:ro", "-v", f"{root}:/state:rw",
            "postgres:16-bookworm", "-c", "shared_buffers=32MB",
        )

    def inspect(self):
        meta = json.loads(command("docker", "inspect", self.container))[0]
        assert meta["Id"] == self.container and meta["Config"]["Labels"]["crg.memory-test"] == self.nonce
        return meta

    def group(self):
        pid = self.inspect()["State"]["Pid"]
        membership = Path(f"/proc/{pid}/cgroup").read_text().strip()
        assert membership.startswith("0::/") and "\n" not in membership
        group = Path("/sys/fs/cgroup") / membership[4:]
        assert group.resolve() == group and group.name in (self.container, f"docker-{self.container}.scope")
        return group

    def exec(self, *args, timeout=30):
        return command("docker", "exec", self.container, *args, timeout=timeout)

    def wait_pg(self):
        until(
            lambda: subprocess.run(["docker", "exec", self.container, "pg_isready", "-U", "postgres"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
            and Path(f"/proc/{self.inspect()['State']['Pid']}/comm").read_text().strip() == "postgres",
            45, "PostgreSQL PID 1 did not become ready",
        )

    def config(self, value, interval=2, enabled=True, paused=False):
        config = {"mode": "enforce", "resource_mode": "manual", "limits": {"memory_high": value},
                  "interval_seconds": interval, "state_dir": "/state/runtime", "log_dir": "/state/logs",
                  "events_enabled": True}
        if enabled:
            config.update(memory_high_recovery=True, memory_high_recovery_paused=paused)
        candidate = self.folder / "config.next"
        candidate.write_text(json.dumps(config))
        candidate.replace(self.folder / "config.json")

    def start(self):
        command("docker", "exec", "-d", self.container, "crg", "run", "--config", "/state/config.json")

    def reload(self):
        return json.loads(self.exec("crg", "reload", "--config", "/state/config.json",
                                    "--state-dir", "/state/runtime"))["request_id"]

    def status(self):
        file = self.folder / "runtime/status.json"
        return json.loads(file.read_bytes()) if file.exists() else {}

    def journal(self):
        return json.loads((self.folder / "runtime/journal.json").read_bytes())

    def high(self):
        return (self.group_path / "memory.high").read_text().strip()

    def external_high(self, value):
        assert self.group() == self.group_path
        (self.group_path / "memory.high").write_text(str(value))
        assert self.high() == str(value)

    def wait_high(self, value, timeout=10):
        until(lambda: self.high() == str(value), timeout, f"kernel memory.high did not reach {value}")

    def wait_reload(self, identifier):
        until(lambda: self.status().get("configuration", {}).get("request_id") == identifier, 10, "reload not observed")

    def wait_reason(self, reason):
        until(lambda: any(item["reason_code"] == reason for item in self.status().get("items", [])),
              10, f"missing reason {reason}")

    def controls(self):
        fields = ["cpu.max", "cpu.weight", "io.max", "io.weight", "memory.max", "memory.swap.max", "pids.max"]
        return {field: (self.group_path / field).read_text().strip() for field in fields}

    def history(self):
        return self.journal()["mutations"]["memory.high:"]

    def logs(self):
        return [row for path in (self.folder / "logs").glob("crg-*.log")
                for line in path.read_text().splitlines() if (row := json.loads(line)).get("event", "").startswith("memory_high_")]

    def remove(self):
        self.inspect()
        command("docker", "rm", "-f", self.container)
        until(lambda: not self.group_path.exists(), 15, "fixture cgroup survived removal")


def pressure(group):
    result = {"current": int((group / "memory.current").read_text())}
    for file, keys in [("memory.events", ("high", "oom", "oom_kill")), ("memory.stat", ("pgscan", "pgsteal"))]:
        parsed = dict(row.split() for row in (group / file).read_text().splitlines())
        result.update({key: int(parsed[key]) for key in keys})
    result["psi"] = (group / "memory.pressure").read_text().strip()
    return result


def query_latency(fixture):
    output = fixture.exec("pgbench", "-n", "-c", "2", "-T", "6", "-R", "30", "-f", "/state/query.sql",
                          "-U", "postgres", "postgres", timeout=25)
    assert re.search(r"number of failed transactions: 0\b", output)
    assert int(re.search(r"number of transactions actually processed: (\d+)", output)[1]) >= 50
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert platform.system() == "Linux" and os.geteuid() == 0
    assert os.environ.get("CRG_NATIVE_MEMORY_TEST") == "ephemeral-github-vm-only"
    endpoint = json.loads(command("docker", "context", "inspect", "--format", "{{json .Endpoints.docker.Host}}"))
    assert endpoint in ("unix:///var/run/docker.sock", "unix:///run/docker.sock")
    binary = args.binary.resolve()
    report = {"kernel": platform.release(), "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
              "build": json.loads(command(binary, "build-info")), "checks": {}, "cleanup": []}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fixtures = []
    nonce = uuid.uuid4().hex[:12]
    gib = 1024 ** 3
    mib = 1024 ** 2

    def launch(folder, name, memory="40g"):
        item = Fixture(folder, name, binary, nonce, memory)
        fixtures.append(item)
        item.group_path = item.group()
        item.wait_pg()
        return item

    try:
        command("docker", "pull", "postgres:16-bookworm", timeout=180)
        report["postgres_image_id"] = command("docker", "image", "inspect", "--format", "{{.Id}}", "postgres:16-bookworm")
        with tempfile.TemporaryDirectory(prefix="crg-memory-recovery-") as directory:
            dbs_dir, his_dir = Path(directory) / "dbs", Path(directory) / "hisdbs"
            dbs_dir.mkdir()
            his_dir.mkdir()
            dbs = launch(dbs_dir, "dbs")
            dbs.external_high(38 * gib)
            dbs.config("30GiB", interval=60)
            dbs.start()
            dbs.wait_high(30 * gib)
            controls = dbs.controls()
            before = time.monotonic()
            dbs.external_high("max")
            dbs.wait_high(30 * gib, 63)
            elapsed = time.monotonic() - before
            assert elapsed <= 62 and dbs.controls() == controls
            until(lambda: any(event["reason"] == "memory_high_recovered" for event in dbs.history()["memory_high_recovery"].get("events", [])),
                  5, "recovery was not durably recorded")
            assert dbs.history()["original"] == str(38 * gib)
            report["checks"]["dbs_30GiB_next_60s_check"] = {"elapsed_seconds": elapsed, "actual": dbs.high(),
                                                            "original": dbs.history()["original"], "other_controls_match": True}

            his = launch(his_dir, "hisdbs")
            his.config("12GiB")
            his.start()
            his.wait_high(12 * gib)
            first_generation = his.status().get("configuration", {}).get("generation", 1)
            his.config("15GiB")
            his.wait_reload(his.reload())
            his.wait_high(15 * gib)
            assert his.status()["configuration"]["generation"] > first_generation
            his.config("15GiB", paused=True)
            his.wait_reload(his.reload())
            his.external_high("max")
            his.wait_reason("memory_high_recovery_paused")
            time.sleep(5)
            assert his.high() == "max" and not his.history().get("conflict")
            his.config("15GiB")
            his.wait_reload(his.reload())
            his.wait_high(15 * gib)
            report["checks"]["hisdbs_15GiB_reload_pause_resume"] = {"actual": his.high(), "paused_for_seconds": 5}

            his.config("96MiB", paused=True)
            his.wait_reload(his.reload())
            his.wait_high(96 * mib)
            his.external_high("max")
            his.wait_reason("memory_high_recovery_paused")
            his.exec("dd", "if=/dev/zero", "of=/dev/shm/crg-pressure", "bs=1M", "count=160")
            (his.folder / "query.sql").write_text("SELECT sum(i) FROM generate_series(1,100) AS i;\n")
            baseline = query_latency(his)
            before_pressure = pressure(his.group_path)
            assert before_pressure["current"] > 96 * mib
            other = his.controls()
            with ThreadPoolExecutor(max_workers=1) as pool:
                during = pool.submit(query_latency, his)
                his.config("96MiB")
                his.wait_reload(his.reload())
                his.wait_high(96 * mib, 12)
                pressured = during.result()
            after_pressure = pressure(his.group_path)
            assert after_pressure["oom_kill"] == before_pressure["oom_kill"] and his.controls() == other
            assert after_pressure["high"] > before_pressure["high"], "workload did not experience reclaim pressure"
            report["checks"]["above_high_reclaim_and_sql_latency"] = {
                "actual": his.high(), "before": before_pressure, "after": after_pressure,
                "sql_baseline": baseline, "sql_during_recovery": pressured, "other_controls_match": True,
            }
            his.exec("rm", "/dev/shm/crg-pressure")
            his.external_high("max")
            his.wait_reason("memory_high_recovery_backoff")
            time.sleep(5)
            assert his.high() == "max" and his.history()["conflict"]
            report["checks"]["repeated_overwrite"] = {"actual": his.high(), "journal": his.history()}

            old_id, old_inode = his.container, his.group_path.stat().st_ino
            old_identity = his.journal()["identity"]
            his.remove()
            fixtures.remove(his)
            report["cleanup"].append({"name": "hisdbs-original", "absent": True})
            replacement = launch(his_dir, "hisdbs-new")
            replacement.config("128MiB", enabled=False)
            replacement.start()
            replacement.wait_high(128 * mib)
            assert replacement.container != old_id and replacement.group_path.stat().st_ino != old_inode
            until(lambda: replacement.journal()["identity"] != old_identity, 5, "stale journal was reused")
            archived = json.loads((his_dir / "runtime/journal.previous.json").read_bytes())
            assert archived["identity"] == old_identity and archived["mutations"]["memory.high:"]["conflict"]
            replacement.external_high("max")
            replacement.wait_reason("external_conflict")
            assert replacement.high() == "max"
            report["checks"]["replacement_id_and_legacy_default"] = {"new_identity": True, "old_journal_retained": True}
            report["events"] = dbs.logs() + replacement.logs()
            assert any(row["event"] == "memory_high_recovered" for row in report["events"])
            assert any(row["event"] == "memory_high_recovery_backoff" for row in report["events"])
            report["phase"] = "passed"
    except BaseException as error:
        report.update(phase="failed", error=str(error))
        raise
    finally:
        for item in fixtures:
            try:
                item.remove()
                report["cleanup"].append({"name": item.folder.name, "absent": True})
            except Exception as error:
                report["cleanup"].append({"name": item.folder.name, "error": str(error), "absent": False})
                report["phase"] = "failed"
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        assert all(row["absent"] for row in report["cleanup"])


if __name__ == "__main__":
    main()
