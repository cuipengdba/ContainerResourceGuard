"""Test-only, bounded perf tracepoint stream for explicitly owned lab targets.

Caller supplies and retains disposable-fixture ownership. This module pins each
process and one shared cgroup; it never attaches ptrace, reads target memory or
buffers, signals a target, writes tracefs/cgroups, or creates a raw perf file.
perf streams are consumed in RAM; only selected integer metadata is retained.
"""
import hashlib
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import time

MARKER='authorized-disposable-loopback-only'
EVENTS=tuple('syscalls:sys_'+direction+'_'+call for call in ['write','recvfrom','sendto','accept','accept4'] for direction in ['enter','exit'])
MAX_EVENTS,MAX_STDERR,MAX_LINE=50000,16384,4096
LINE=re.compile(r'\s*(\d+)\s*/\s*(\d+)\s+(\d+)\.(\d{1,9}):\s+(syscalls:sys_(enter|exit)_([a-z0-9]+)):\s*(.*)')

class Rejected(Exception):pass

def need(ok,reason):
    if not ok:raise Rejected(reason)

def identity(pid):
    p=Path('/proc',str(pid));parts=(p/'stat').read_bytes().rsplit(b')',1)[1].split()
    return {'start_ticks':int(parts[19]),'state':parts[0].decode(),'cgroup':(p/'cgroup').read_text().strip()}

def validate(targets):
    need(1<=len(targets)<=2,'ONE_OR_TWO_OWN_PROCESSES');groups=set()
    for target in targets:
        need(type(target['pid']) is int and target['pid']>1,'TARGET_PID')
        actual=identity(target['pid']);need(actual['state'] not in ['Z','X'] and actual['start_ticks']==target['start_ticks'] and actual['cgroup']==target['cgroup'],'TARGET_IDENTITY')
        h=hashlib.sha256()
        with Path('/proc',str(target['pid']),'exe').open('rb') as f:
            for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
        need(h.hexdigest()==target['executable_sha256'],'TARGET_EXECUTABLE')
        groups.add(actual['cgroup'])
    need(len(groups)==1 and next(iter(groups)).startswith('0::/'),'ONE_V2_CGROUP')

def decode(line):
    m=LINE.fullmatch(line);need(m is not None,'UNPARSED_EVENT')
    row={'pid':int(m[1]),'tid':int(m[2]),'monotonic_ns':int(m[3])*1000000000+int(m[4].ljust(9,'0')),'direction':m[6],'call':m[7]}
    if row['direction']=='enter':
        # syscall tracepoint printf may also contain a user-buffer ADDRESS. It
        # is deliberately never copied to a record, error, or diagnostic file.
        values=dict(re.findall(r'\b(fd|count)\s*[:=]\s*(0x[0-9a-fA-F]+|[0-9]+)',m[8]))
        need('fd' in values,'ENTRY_FD_UNKNOWN')
        row.update({key:int(value,0) for key,value in values.items()})
        need(0<=row['fd']<=65535,'FD_BOUND')
    else:
        value=m[8].strip();need(re.fullmatch(r'-?(?:0x[0-9a-fA-F]{1,16}|[0-9]{1,20})',value) is not None,'EXIT_RETURN_UNKNOWN')
        ret=int(value,0)
        if ret>=1<<63:ret-=1<<64
        need(-(1<<63)<=ret<(1<<63),'RETURN_BOUND');row['return']=ret
    return row

def fd_metadata(pid,fd):
    p=Path('/proc',str(pid));linkpath=p/'fd'/str(fd)
    try:
        link=os.readlink(linkpath)
        if link in ['/opt/dbs/log/DBS.log','/opt/dbs/log/HISDBS.log']:value={'kind':'vendor-log','path':link}
        elif re.fullmatch(r'socket:\[[0-9]+\]',link):
            inode=link[8:-1];value={'kind':'socket','loopback_tuple_available':False}
            with (p/'net/tcp').open('rb') as f:raw=f.read(1024*1024+1)
            need(len(raw)<=1024*1024,'TCP_TABLE_BOUND')
            for line in raw.decode('ascii').splitlines()[1:]:
                fields=line.split()
                if len(fields)>9 and fields[9]==inode:
                    local,remote=fields[1].split(':'),fields[2].split(':')
                    if local[0]=='0100007F' and remote[0]=='0100007F':value.update(loopback_tuple_available=True,local_port=int(local[1],16),remote_port=int(remote[1],16))
                    break
        elif re.fullmatch(r'pipe:\[[0-9]+\]',link):value={'kind':'pipe'}
        else:value={'kind':'other-path-redacted'}
        need(os.readlink(linkpath)==link,'FD_LINK_CHANGED');return value
    except (OSError,Rejected) as e:return {'kind':'unknown','reason':str(e) if isinstance(e,Rejected) else type(e).__name__}

class Stream:
    def __init__(self,targets):
        need(os.environ.get('CRG_PERF_METADATA')==MARKER,'EXPLICIT_LAB_MARKER')
        validate(targets);need(shutil.which('perf') and shutil.which('stdbuf'),'PERF_AND_STDBUF_REQUIRED')
        self.targets={v['pid']:dict(v) for v in targets};self.exe_inodes={pid:(os.stat('/proc/%d/exe'%pid).st_dev,os.stat('/proc/%d/exe'%pid).st_ino) for pid in self.targets};self.selector=selectors.DefaultSelector();self.buffers={};self.stderr={'record':bytearray(),'script':bytearray()};self.events=[];self.errors={};self.other_pids=0;self.bytes=0;self.record=self.script=None;self.pidfd=None;self.control=None;self.started=time.monotonic();self.cpu=time.process_time();self.ready=False;self.result=None;self.ack_bytes=0;self.owned_processes={}
    def error(self,reason):self.errors[reason]=self.errors.get(reason,0)+1
    def start(self):
        ctl_r,ctl_w=os.pipe();ack_r,ack_w=os.pipe();self.control=ctl_w
        args=['perf','record','--quiet','--no-buildid','--no-buildid-cache','--clockid','mono','--timestamp','--mmap-pages','16','--delay=-1','--control','fd:%d,%d'%(ctl_r,ack_w),'--event',','.join(EVENTS),'--output','-','--pid',','.join(str(v) for v in self.targets)]
        try:
            self.record=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,pass_fds=(ctl_r,ack_w));self.pidfd=os.pidfd_open(self.record.pid);self.owned_processes['record']={'pid':self.record.pid,'start_ticks':identity(self.record.pid)['start_ticks']}
            self.script=subprocess.Popen(['stdbuf','--output=L','perf','script','--ns','--input','-','--fields','trace:pid,tid,time,event,trace'],stdin=self.record.stdout,stdout=subprocess.PIPE,stderr=subprocess.PIPE);self.record.stdout.close()
            self.owned_processes['script']={'pid':self.script.pid,'start_ticks':identity(self.script.pid)['start_ticks']}
            for f,label in [(self.script.stdout,'events'),(self.script.stderr,'script'),(self.record.stderr,'record')]:
                os.set_blocking(f.fileno(),False);self.selector.register(f,selectors.EVENT_READ,label);self.buffers[label]=bytearray()
            os.set_blocking(ack_r,False);os.write(ctl_w,b'enable\n');end=time.monotonic()+10;ack=bytearray()
            while time.monotonic()<end:
                self.pump(.05)
                try:ack.extend(os.read(ack_r,128))
                except BlockingIOError:pass
                if b'ack\n' in ack:break
                need(self.record.poll() is None and self.script.poll() is None,'PERF_EARLY_EXIT')
            self.ack_bytes=len(ack)
            # Upstream evlist__ctlfd_ack writes sizeof("ack\n"), including
            # the terminal C NUL. Accept only the two exact known framings.
            need(bytes(ack) in [b'ack\n',b'ack\n\0'],'PERF_ENABLE_HANDSHAKE');validate(list(self.targets.values()));self.ready=True
            return self
        except BaseException:
            self.finish();raise
        finally:
            for fd in [ctl_r,ack_r,ack_w]:os.close(fd)
    def metadata(self,pid,fd):
        try:
            target=self.targets[pid]
            for stage in ['before','after']:
                now=identity(pid);exe=os.stat('/proc/%d/exe'%pid)
                need(now['start_ticks']==target['start_ticks'] and now['cgroup']==target['cgroup'] and (exe.st_dev,exe.st_ino)==self.exe_inodes[pid],'FD_TARGET_IDENTITY')
                if stage=='before':value=fd_metadata(pid,fd)
            return value
        except (OSError,Rejected) as e:return {'kind':'unknown','reason':str(e) if isinstance(e,Rejected) else type(e).__name__}
    def line(self,raw):
        try:
            need(len(raw)<=MAX_LINE,'LINE_BOUND');row=decode(raw.decode('ascii'))
            if row['pid'] not in self.targets:self.other_pids+=1;return
            need(len(self.events)<MAX_EVENTS,'EVENT_BOUND')
            if row['direction']=='enter':row['fd_metadata']=self.metadata(row['pid'],row['fd'])
            elif row['call'] in ['accept','accept4'] and 0<=row['return']<=65535:row['accepted_fd_metadata']=self.metadata(row['pid'],row['return'])
            self.events.append(row)
        except (Rejected,UnicodeError,ValueError) as e:self.error(str(e) if isinstance(e,Rejected) else type(e).__name__)
    def pump(self,timeout=0):
        need(time.monotonic()-self.started<=930,'STREAM_LIFETIME_BOUND')
        for key,mask in self.selector.select(timeout):
            raw=os.read(key.fileobj.fileno(),65536);label=key.data
            if not raw:self.selector.unregister(key.fileobj);continue
            self.bytes+=len(raw);need(self.bytes<=32*1024*1024,'STREAM_BYTES_BOUND')
            if label!='events':
                self.stderr[label].extend(raw[:max(0,MAX_STDERR-len(self.stderr[label]))])
                if len(self.stderr[label])>=MAX_STDERR:self.error('STDERR_BOUND')
                continue
            self.buffers[label].extend(raw)
            while b'\n' in self.buffers[label]:
                row,_,rest=self.buffers[label].partition(b'\n');self.buffers[label]=bytearray(rest)
                if row.strip():self.line(row)
            need(len(self.buffers[label])<=MAX_LINE,'PARTIAL_LINE_BOUND')
    def finish(self):
        if self.result is not None:return self.result
        if self.record is not None and self.record.poll() is None:
            # pidfd is for this Popen perf process, never either traced target.
            signal.pidfd_send_signal(self.pidfd,signal.SIGINT)
        deadline=time.monotonic()+5
        while self.script is not None and (self.script.poll() is None or self.selector.get_map()) and time.monotonic()<deadline:
            try:self.pump(.05)
            except BaseException as e:self.error(type(e).__name__);break
        for name,child in [('record',self.record),('script',self.script)]:
            if child is None:continue
            try:child.wait(timeout=.2)
            except subprocess.TimeoutExpired:
                self.error(name.upper()+'_FORCED_OWN_CLEANUP');child.kill();child.wait(timeout=2)
        for f in [self.record.stderr if self.record else None,self.script.stdout if self.script else None,self.script.stderr if self.script else None]:
            if f is not None:f.close()
        self.selector.close()
        if self.pidfd is not None:os.close(self.pidfd);self.pidfd=None
        if self.control is not None:os.close(self.control);self.control=None
        known_control=[];unknown_stderr={}
        for label,data in self.stderr.items():
            unknown=[line for line in data.splitlines() if line.strip() and not (label=='record' and line in [b'Events enabled',b'Events disabled'])]
            known_control.extend(line.decode('ascii') for line in data.splitlines() if label=='record' and line in [b'Events enabled',b'Events disabled'])
            unknown_stderr[label]=bool(unknown)
            if unknown:self.error(label.upper()+'_STDERR_UNKNOWN')
        if self.buffers.get('events'):self.error('UNTERMINATED_EVENT')
        pairs=[];pending={}
        for row in self.events:
            key=(row['pid'],row['tid'],row['call'])
            if row['direction']=='enter':
                if key in pending:self.error('DUPLICATE_ENTER')
                pending[key]=row
            elif key in pending:
                entry=pending.pop(key);pairs.append({'entry':entry,'exit':row,'elapsed_ns':row['monotonic_ns']-entry['monotonic_ns']})
            # Initial exit and final unfinished calls stay explicitly unknown.
        self.result={'schema':'crg-perf-metadata-stream-v1','enable_handshake':self.ready,'ack_bytes':self.ack_bytes,'owned_collector_processes':self.owned_processes,'record_exit':self.record.returncode if self.record else None,'script_exit':self.script.returncode if self.script else None,'events':self.events,'pairs':pairs,'unfinished_entries':list(pending.values()),'diagnostic_errors':self.errors,'stderr_present':{k:bool(v.strip()) for k,v in self.stderr.items()},'stderr_unknown_present':unknown_stderr,'known_control_messages':known_control,'raw_metadata_stream_bytes_consumed':self.bytes,'elapsed_seconds':time.monotonic()-self.started,'collector_CPU_seconds':time.process_time()-self.cpu,'other_inherited_PIDs_omitted':self.other_pids,'target_signals_or_control_writes':0,'raw_perf_files_target_buffers_addresses_or_payload_saved':False,'FD_snapshots_are_nonatomic':True}
        return self.result
