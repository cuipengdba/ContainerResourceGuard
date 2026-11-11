#!/usr/bin/env python3
"""Disposable-test-only Agent activity session; never a product runtime feature.

Default CLI is inert. STOP/CONT require an owned fixture proof and stable pidfd.
A separate bounded watchdog resumes an armed target after owner pipe EOF/lease.
Host qualification children are distinct from actual vendor-container evidence.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import select
import signal
import stat
import subprocess
import sys
import time

MARKER = 'authorized-disposable-test-node-only'
ELF = 'dbc48aa5a4aa4d4a77c6af03d3294a9fcf08a6855672a80b003fccd1fed8a2c8'
CONTROLS = ['cpu.max', 'memory.max', 'io.max', 'cpu.weight', 'pids.max', 'io.weight', 'memory.high', 'memory.swap.max']


class Rejected(Exception):
    pass


def need(value, reason):
    if not value:
        raise Rejected(reason)


def read(path, maximum=65536, follow=False):
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | (0 if follow else os.O_NOFOLLOW))
    try:
        need(stat.S_ISREG(os.fstat(fd).st_mode), 'REGULAR_FILE_REQUIRED')
        raw = bytearray()
        while len(raw) <= maximum:
            part = os.read(fd, min(65536, maximum + 1 - len(raw)))
            if not part:
                break
            raw.extend(part)
        need(len(raw) <= maximum, 'READ_BOUND')
        return bytes(raw)
    finally:
        os.close(fd)


def fields(pid):
    need(type(pid) is int and pid > 1 and pid != os.getpid(), 'NON_SELF_NON_PID1_REQUIRED')
    raw = read('/proc/%d/stat' % pid, 4096)
    value = raw.rsplit(b')', 1)[1].split()
    return {'pid': pid, 'start_ticks': int(value[19]), 'state': value[0].decode(), 'ppid': int(value[1]),
            'user_ticks': int(value[11]), 'system_ticks': int(value[12]), 'threads': int(value[17])}


def group(pid):
    rows = read('/proc/%d/cgroup' % pid, 16384).decode().splitlines()
    paths = [v.split('::', 1)[1] for v in rows if v.startswith('0::')]
    need(len(paths) == 1, 'UNIFIED_CGROUP_REQUIRED')
    return '/sys/fs/cgroup' + paths[0].rstrip('/')


def proof(plan):
    need(os.environ.get('CRG_AGENT_ACTIVITY') == MARKER and sys.platform == 'linux' and os.geteuid() == 0,
         'EXPLICIT_LINUX_ROOT_LAB_REQUIRED')
    root = Path(plan['fixture_root'])
    need(re.fullmatch(r'/var/tmp/crg-agent-activity[0-9]+-[0-9]{8}(?:/runs/(?:a1|b1|b2|a2))?', str(root))
         and root.resolve() == root, 'FIXTURE_ROOT_REQUIRED')
    info = root.stat()
    need(stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and stat.S_IMODE(info.st_mode) == 0o700, 'PRIVATE_ROOT_REQUIRED')
    p = root/'agent-activity-owner.json'
    info = p.lstat()
    need(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and stat.S_IMODE(info.st_mode) == 0o600, 'PRIVATE_PROOF_REQUIRED')
    owner = json.loads(read(p))
    need(owner['schema'] == 'crg-agent-activity-owner-v1' and owner['kind'] == plan['kind'] and
         owner['nonce'] == plan['nonce'] and re.fullmatch('[0-9a-f]{32}', plan['nonce']), 'OWNERSHIP_MISMATCH')
    if plan['kind'] == 'owned-child':
        need(owner['owner_pid'] == plan['owner_pid'], 'CHILD_OWNER_MISMATCH')
    else:
        need(plan['kind'] == 'vendor-container' and plan['binary_sha256'] == ELF and
             plan['argv'] == ['/opt/crg/crg', 'run', '--config', '/etc/crg/config.json'], 'VENDOR_AGENT_REQUIRED')
        need(re.fullmatch(r'crg-vendor-lab-agent-activity[0-9]+-[0-9]{8}', owner['namespace']) and
             owner['pod_uid'] == plan['pod_uid'] and owner['container_id'] == plan['container_id'] and
             owner['container_pid'] == plan['container_pid'] and owner['container_start_ticks'] == plan['container_start_ticks'],
             'CONTAINER_PROOF_MISMATCH')
        need(re.fullmatch('[0-9a-f-]{36}', plan['pod_uid']) and re.fullmatch('[0-9a-f]{64}', plan['container_id']), 'CONTAINER_ID_BOUND')
    return root, owner


def identity(plan, allow_orphan=False):
    root, owner = proof(plan)
    current = fields(plan['pid'])
    need(current['start_ticks'] == plan['start_ticks'] and current['state'] not in ['Z', 'X'], 'PROCESS_CHANGED')
    status = read('/proc/%d/status' % plan['pid']).decode().splitlines()
    need(int(next(v.split()[1] for v in status if v.startswith('Tgid:'))) == plan['pid'], 'LEADER_REQUIRED')
    need(group(plan['pid']) == plan['cgroup'], 'CGROUP_CHANGED')
    argv = read('/proc/%d/cmdline' % plan['pid'], 8192).rstrip(b'\0').split(b'\0')
    need(argv == [os.fsencode(v) for v in plan['argv']], 'ARGV_CHANGED')
    need(hashlib.sha256(read('/proc/%d/exe' % plan['pid'], 16 * 1024 * 1024, True)).hexdigest() == plan['binary_sha256'], 'EXE_CHANGED')
    if plan['kind'] == 'owned-child':
        need(current['ppid'] == plan['owner_pid'] or (allow_orphan and current['ppid'] == 1), 'NOT_OWNED_CHILD')
    else:
        parent = fields(plan['container_pid'])
        need(parent['start_ticks'] == plan['container_start_ticks'] and plan['pid'] != plan['container_pid'], 'CONTAINER_PID1_CHANGED')
        need(Path(plan['cgroup']).name == 'cri-containerd-' + plan['container_id'] + '.scope' and
             ('pod' + plan['pod_uid'].replace('-', '_')) in Path(plan['cgroup']).parent.name, 'OWN_CONTAINER_LEAF_REQUIRED')
        marker = json.loads(read('/proc/%d/root/etc/crg/agent-activity-fixture.json' % plan['pid']))
        need(marker == {'fixture_root': str(root), 'nonce': plan['nonce'], 'namespace': owner['namespace']}, 'IN_CONTAINER_MARKER_REQUIRED')
        ancestor, visited = current['ppid'], set()
        while ancestor != plan['container_pid'] and len(visited) < 12:
            need(ancestor not in visited and ancestor > 1, 'ANCESTRY_CHANGED')
            visited.add(ancestor)
            ancestor = fields(ancestor)['ppid']
        need(ancestor == plan['container_pid'], 'NOT_OWN_CONTAINER_DESCENDANT')
    return current


def vector(plan):
    root, _ = proof(plan)
    directory = Path(plan['cgroup']) if plan['kind'] == 'vendor-container' else root/'controls'
    return {name: read(directory/name, 131072).decode() for name in CONTROLS}


def pidfd_matches(descriptor, pid):
    info = read('/proc/self/fdinfo/%d' % descriptor, 8192).decode().splitlines()
    return any(v.startswith('Pid:') and int(v.split()[1]) == pid for v in info)


def wait_line(descriptor, deadline):
    data = b''
    while b'\n' not in data:
        remaining = deadline - time.monotonic()
        need(remaining > 0 and select.select([descriptor], [], [], remaining)[0], 'WATCHDOG_HANDSHAKE_TIMEOUT')
        part = os.read(descriptor, 256 - len(data))
        need(part and len(data) + len(part) < 256, 'WATCHDOG_HANDSHAKE_EOF_OR_BOUND')
        data += part
    need(data.endswith(b'\n') and data.count(b'\n') == 1, 'WATCHDOG_HANDSHAKE_FORMAT')
    return data.rstrip(b'\n')


def watchdog(plan_path, pidfd, channel, ack, output, lease):
    plan = json.loads(read(plan_path));identity(plan)
    need(pidfd_matches(pidfd, plan['pid']), 'WATCHDOG_PIDFD_MISMATCH')
    os.write(ack, b'ready\n');armed, reason, count = False, 'owner-completed', 0
    deadline = time.monotonic() + lease
    try:
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                reason = 'lease-expired';break
            if not select.select([channel], [], [], min(left, 1))[0]:
                continue
            data = os.read(channel, 64)
            if data == b'arm\n':
                need(not armed, 'SINGLE_ARM_REQUIRED');armed = True;os.write(ack, b'armed\n')
            elif data == b'done\n':
                armed = False;break
            elif not data:
                reason = 'owner-pipe-eof';break
            else:
                reason = 'invalid-owner-command';break
        if armed:
            try:
                identity(plan, allow_orphan=True)
                if pidfd_matches(pidfd, plan['pid']):
                    signal.pidfd_send_signal(pidfd, signal.SIGCONT, None, 0);count = 1
            except (Rejected, FileNotFoundError, ProcessLookupError):
                reason += ':target-gone-or-identity-changed'
    finally:
        with Path(output).open('x', encoding='utf-8') as stream:
            json.dump({'schema':'crg-agent-activity-watchdog-v1','pid':plan['pid'],'start_ticks':plan['start_ticks'],
                       'armed_at_unwind':armed,'reason':reason,'CONT_count':count}, stream)
        os.close(pidfd);os.close(channel);os.close(ack)


class Session:
    def __init__(self, plan, label, record, pause=False, lease=900):
        need(re.fullmatch('[a-z][a-z0-9-]{0,47}', label) and type(pause) is bool and 2 <= lease <= 900, 'SESSION_ARGUMENTS')
        self.plan, self.label, self.record, self.pausing, self.lease = dict(plan), label, record, pause, lease
        self.fd, self.child, self.channel, self.ack = None, None, None, None
        self.stop_attempted, self.opened, self.closed = False, False, False
        self.record.update(schema='crg-agent-activity-session-v1',phase='not-opened',STOP_count=0,CONT_count=0)

    def inspect(self):
        current = identity(self.plan)
        need(self.fd is not None and pidfd_matches(self.fd, self.plan['pid']), 'PIDFD_CHANGED')
        states = []
        for task in Path('/proc/%d/task' % self.plan['pid']).iterdir():
            try:states.append(read(task/'stat',4096).rsplit(b')',1)[1].split()[0].decode())
            except (FileNotFoundError, ProcessLookupError):pass
        need(0 < len(states) <= 256, 'THREAD_BOUND')
        current['all_threads_stopped'] = all(v in ['T','t'] for v in states)
        current['controls'] = vector(self.plan)
        current['control_values_preserved'] = current['controls'] == self.before
        try:
            current['process_io']={key:int(value) for key,value in (row.split(':',1) for row in read('/proc/%d/io' % self.plan['pid'],8192).decode().splitlines())
                if key in ['rchar','wchar','syscr','syscw','read_bytes','write_bytes','cancelled_write_bytes']}
        except (OSError,ValueError):current['process_io']=None
        return current

    def __enter__(self):
        need(not self.opened, 'SINGLE_OPEN_REQUIRED');self.opened = True
        try:
            current = identity(self.plan);need(current['state'] not in ['T','t'], 'ALREADY_STOPPED')
            self.before = vector(self.plan);self.fd = os.pidfd_open(self.plan['pid'],0)
            need(pidfd_matches(self.fd,self.plan['pid']), 'PIDFD_CHANGED');identity(self.plan)
            root,_ = proof(self.plan);planfile=root/('activity-'+self.label+'-plan.json')
            with planfile.open('x',encoding='utf-8') as stream:json.dump(self.plan,stream)
            planfile.chmod(0o600)
            control_read,self.channel=os.pipe();self.ack,ack_write=os.pipe()
            output=root/('activity-'+self.label+'-watchdog.json')
            try:
                self.child=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--watchdog',str(planfile),
                    str(self.fd),str(control_read),str(ack_write),str(output),str(self.lease)],
                    stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                    pass_fds=(self.fd,control_read,ack_write),close_fds=True)
            finally:os.close(control_read);os.close(ack_write)
            self.output=output
            need(wait_line(self.ack,time.monotonic()+5)==b'ready','WATCHDOG_NOT_READY')
            self.record.update(watchdog_pid=self.child.pid,watchdog_start_ticks=fields(self.child.pid)['start_ticks'])
            if self.pausing:
                os.write(self.channel,b'arm\n');need(wait_line(self.ack,time.monotonic()+5)==b'armed','WATCHDOG_NOT_ARMED')
                identity(self.plan);self.stop_attempted=True
                signal.pidfd_send_signal(self.fd,signal.SIGSTOP,None,0);self.record['STOP_count']+=1
                deadline=time.monotonic()+2
                while True:
                    sample=self.inspect()
                    if sample['all_threads_stopped'] and sample['control_values_preserved']:break
                    need(time.monotonic()<deadline,'STOP_READBACK_TIMEOUT');time.sleep(.01)
            self.record.update(phase='paused' if self.pausing else 'active',initial=self.inspect())
            return self
        except BaseException:
            try:self.close()
            except BaseException as error:self.record['unwind_error']=type(error).__name__
            raise

    def close(self):
        if self.closed:return
        self.closed=True
        try:
            if self.stop_attempted:
                try:
                    current=fields(self.plan['pid'])
                    if current['start_ticks']!=self.plan['start_ticks'] or current['state'] in ['Z','X']:
                        self.record['target_gone_or_reused_before_resume']=True
                    else:
                        current=identity(self.plan)
                        if self.fd is not None and pidfd_matches(self.fd,self.plan['pid']):
                            signal.pidfd_send_signal(self.fd,signal.SIGCONT,None,0);self.record['CONT_count']+=1
                        deadline=time.monotonic()+2
                        while identity(self.plan)['state'] in ['T','t']:
                            need(time.monotonic()<deadline,'CONT_READBACK_TIMEOUT');time.sleep(.01)
                        self.record['resumed_same_instance']=True
                except (FileNotFoundError,ProcessLookupError):self.record['target_gone_before_resume']=True
            if self.channel is not None:
                try:os.write(self.channel,b'done\n')
                except BrokenPipeError:self.record['watchdog_pipe_already_closed']=True
            self.record['phase']='closed'
        except BaseException as error:
            self.record['close_error']=type(error).__name__
            raise
        finally:
            for name in ['channel','ack','fd']:
                descriptor=getattr(self,name)
                if descriptor is not None:os.close(descriptor);setattr(self,name,None)
            if self.child is not None:
                try:self.child.wait(timeout=7)
                except subprocess.TimeoutExpired:self.record['watchdog_still_running']=True
                if self.child.poll() is not None:
                    self.record['watchdog_exit']=self.child.returncode
                    if self.output.exists():self.record['watchdog']=json.loads(read(self.output))

    def __exit__(self,kind,value,trace):
        try:self.close()
        except BaseException as error:
            if kind is None:raise
            self.record['unwind_error']=type(error).__name__
        return False


def main():
    if len(sys.argv)>1 and sys.argv[1]=='--watchdog':
        need(len(sys.argv)==8,'WATCHDOG_ARGUMENTS')
        watchdog(Path(sys.argv[2]),int(sys.argv[3]),int(sys.argv[4]),int(sys.argv[5]),sys.argv[6],float(sys.argv[7]))
        return 0
    print(json.dumps({'phase':'read-only','executed':False,'scope':'import-only disposable test helper; not installed in containers'}))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
