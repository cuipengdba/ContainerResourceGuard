#!/usr/bin/env python3
"""Native Linux checks for the read-only owner collector, not a business SLA."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def qualify(module):
    checks = []
    evidence = []
    def check(name, condition):
        assert condition, name
        checks.append({'name': name, 'passed': True})
    child_source = '''import json,os,socket,sys
a=socket.socket();a.bind(('127.0.0.1',0));a.listen(1);port=a.getsockname()[1]
u=socket.socket(socket.AF_UNIX);path='.s.PGSQL.'+str(port);u.bind(path);u.listen(1)
v=None
try:
 v=socket.socket(socket.AF_INET6);v.setsockopt(socket.IPPROTO_IPV6,socket.IPV6_V6ONLY,1);v.bind(('::1',port));v.listen(1)
except OSError:
 if v is not None:v.close()
 v=None
print(json.dumps({'pid':os.getpid(),'port':port,'ipv6':v is not None}),flush=True)
sys.stdin.readline()
a.close();u.close()
if v is not None:v.close()
os.unlink(path)
'''
    with tempfile.TemporaryDirectory(prefix='crg-port-owner-qualification-') as directory:
        child = subprocess.Popen([sys.executable, '-u', '-c', child_source],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True, cwd=directory)
        try:
            row = json.loads(child.stdout.readline())
            expected = module.identity(child.pid)
            result = module.collect(expected, [row['port']])
            evidence.append(result)
            owners = [p for item in result['listeners'] for p in item['owners']]
            tcp = [v for v in result['listeners'] if v['table'] == 'tcp']
            unix = [v for v in result['listeners'] if v['table'] == 'unix']
            check('actual-own-TCP4-listener-inode-and-stable-owner',len(tcp)==1 and any(v['pid']==child.pid and v['start_ticks']==expected['start_ticks'] for v in tcp[0]['owners']))
            check('actual-own-PG-style-unix-listener-and-stable-owner',len(unix)==1 and unix[0]['endpoint'].endswith('.s.PGSQL.'+str(row['port'])) and any(v['pid']==child.pid for v in unix[0]['owners']))
            check('actual-IPv6-if-supported-or-explicitly-unavailable',any(v['table']=='tcp6' and any(p['pid']==child.pid for p in v['owners']) for v in result['listeners']) if row['ipv6'] else not any(v['table']=='tcp6' for v in result['listeners']))
            check('owner-membership-namespace-and-observed-CWD',bool(owners) and all(v['pid']==child.pid and v['net_namespace_inode']==expected['net_namespace_inode'] and v['same_cgroup'] and v['cwd_observed']==directory for v in owners))
            check('target-identity-retained-and-no-availability-claim',result['target_identity_stable'] and not result['atomic_snapshot'] and not result['port_availability_claimed'] and child.poll() is None)
            for key,value in [('start_ticks',expected['start_ticks']+1),('net_namespace_inode',expected['net_namespace_inode']+1),('cgroup_membership',expected['cgroup_membership']+'invalid')]:
                wrong=dict(expected);wrong[key]=value;v=module.collect(wrong,[row['port']]);check('reject-wrong-target-'+key,v['phase']=='partial' and v['listeners']==[] and v['issues']==['target-identity-mismatch-before-read'])
            for ports in [[],[0],[65536],[True],[1.2],list(range(1,18))]:
                try:module.collect(expected,ports)
                except ValueError:check('reject-invalid-ports-'+repr(ports),True)
                else:raise AssertionError('invalid ports accepted')
            for key in ['max_seconds','max_processes','max_fds','max_sockets','max_table_bytes']:
                try:module.collect(expected,[row['port']],**{key:0})
                except ValueError:check('reject-zero-'+key,True)
                else:raise AssertionError('zero bound accepted')
            limited=module.collect(expected,[row['port']],max_table_bytes=16)
            check('oversized-tables-report-partial-not-empty-success',limited['phase']=='partial' and any(v.startswith('table-byte-limit-') for v in limited['issues']))
            limited=module.collect(expected,[row['port']],max_sockets=1)
            check('listener-count-limit-retains-partial',limited['phase']=='partial' and 'listener-count-limit' in limited['issues'])
            limited=module.collect(expected,[row['port']],max_processes=1)
            check('process-count-limit-is-partial',limited['phase']=='partial' and 'process-count-limit' in limited['issues'])
            limited=module.collect(expected,[row['port']],max_fds=1)
            check('descriptor-count-limit-is-partial',limited['phase']=='partial' and 'fd-count-limit' in limited['issues'])
            # Controlled identity-fault injection; no real process is recycled.
            original=module.identity;seen=[0]
            def changed(pid,*args):
                value=original(pid,*args)
                if pid==child.pid:
                    seen[0]+=1
                    if seen[0]>=3:value=dict(value,start_ticks=value['start_ticks']+1)
                return value
            module.identity=changed
            try:changed_result=module.collect(expected,[row['port']])
            finally:module.identity=original
            check('injected-owner-or-final-target-change-retains-unknown',changed_result['phase']=='partial' and any('identity-changed' in v for v in changed_result['issues']))
            check('collector-does-not-stop-or-change-own-fixture',module.identity(child.pid)==expected and child.poll() is None)
        finally:
            # Only this newly created child receives EOF; no kill or signal.
            stdout,stderr=child.communicate('\n',timeout=10)
            assert child.returncode==0,(stdout,stderr)
        check('own-child-and-unix-fixture-cleanup',not Path('/proc',str(child.pid)).exists() and not list(Path(directory).glob('.s.PGSQL.*')))
        dead=module.collect(expected,[row['port']]);check('exited-target-is-partial-not-free-port',dead['phase']=='partial' and not dead['target_identity_stable'] and not dead['port_availability_claimed'])
    return {'schema':'crg-readonly-port-owner-native-qualification-v1','phase':'passed','checks':checks,'count':len(checks),'ipv6_fixture_available':row['ipv6'],'native_snapshot':evidence[0],'product_or_other_business_changed':False,'business_SLA_accepted':False,'harness_integrated':False}


if __name__=='__main__':
    spec=importlib.util.spec_from_file_location('port_owners',sys.argv[1]);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);print(json.dumps(qualify(module)))
