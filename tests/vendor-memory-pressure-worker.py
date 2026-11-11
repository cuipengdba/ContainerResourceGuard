#!/usr/bin/env python
"""Bounded anonymous-memory holder for an explicitly isolated vendor fixture.

Python 2/3 compatible. This is a test process, never an Agent or a cgroup writer.
One synchronous command leases the memory for at most ten seconds. EOF, invalid
input, TERM, the lease, or the 240-second lifetime all release the allocation.
"""
from __future__ import print_function
import gc,json,os,resource,signal,struct,sys,time

CHUNK=64*1024*1024
MAXIMUM=12*1024*1024*1024
LEASE=10
LIFETIME=240
MARKER='authorized-disposable-loopback-only'

def emit(value):
    sys.stdout.write(json.dumps(value,separators=(',',':'))+'\n');sys.stdout.flush()

def permitted(command,allocated):
    if not isinstance(command,dict) or set(command)!=set(['op']):
        raise ValueError('command must have only op')
    op=command['op']
    if op not in ['allocate','ping','release','exit']:
        raise ValueError('unknown command')
    if op=='allocate' and allocated+CHUNK>MAXIMUM:
        raise ValueError('fixed twelve GiB allocation cap')
    return op

def main():
    if sys.platform!='linux' or struct.calcsize('P')!=8 or os.environ.get('CRG_MEMORY_PRESSURE_TEST')!=MARKER:
        emit({'phase':'rejected','allocated_bytes':0,'reason':'explicit isolated Linux64 fixture marker required'});return 1
    clock=getattr(time,'monotonic',lambda:os.times()[4])
    blocks=[];allocated=0;entered=clock();reason='EOF';result=0
    def ended(signum,frame):
        raise RuntimeError('lease-or-signal-'+str(signum))
    for name in ['SIGALRM','SIGTERM','SIGINT']:signal.signal(getattr(signal,name),ended)
    try:
        # This bound applies only to this helper, never PostgreSQL or CRG.
        resource.setrlimit(resource.RLIMIT_AS,(MAXIMUM+2*1024*1024*1024,MAXIMUM+2*1024*1024*1024))
        emit({'phase':'ready','pid':os.getpid(),'chunk_bytes':CHUNK,'maximum_bytes':MAXIMUM,'lease_seconds':LEASE,'lifetime_seconds':LIFETIME})
        while True:
            remaining=LIFETIME-(clock()-entered)
            if remaining<=0:raise RuntimeError('lifetime exceeded')
            signal.alarm(max(1,min(LEASE,int(remaining))))
            line=sys.stdin.readline(4097)
            if not line:break
            if len(line)>4096 or not line.endswith('\n'):raise ValueError('bounded newline command required')
            op=permitted(json.loads(line),allocated)
            if op=='allocate':
                block=bytearray(CHUNK)
                for offset in range(0,CHUNK,4096):block[offset]=1
                blocks.append(block);block=None;allocated+=CHUNK
            elif op in ['release','exit']:
                del blocks[:];gc.collect();allocated=0
            emit({'phase':'ack','op':op,'pid':os.getpid(),'allocated_bytes':allocated})
            if op=='exit':reason='exit-command';break
    except BaseException as error:
        result=1;reason=type(error).__name__+':'+str(error)
    finally:
        signal.alarm(0);del blocks[:];gc.collect()
        emit({'phase':'released','allocated_bytes':0,'reason':reason,'lifetime_seconds':clock()-entered})
    return result

if __name__=='__main__':sys.exit(main())
