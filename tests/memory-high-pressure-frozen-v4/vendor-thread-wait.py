#!/usr/bin/env python3
"""Bounded procfs wait metadata; never reads target memory or FD contents.

Only a caller that already pins one process/task may use capture(). Register
values, stack addresses and unapproved FD paths are discarded before returning.
Separate procfs reads are not an atomic snapshot and cannot prove root cause.
"""
import os
from pathlib import PurePosixPath
import re

MAX_STACK_BYTES, MAX_FRAMES, MAX_SYMBOL = 4096, 12, 96
FD_CALLS = {0:'read', 1:'write', 3:'close', 17:'pread64', 18:'pwrite64',
            19:'readv', 20:'writev', 74:'fsync', 75:'fdatasync', 306:'syncfs'}
ALLOWED_ROOTS = ('/opt/dbs/log/', '/opt/postgresql/data/', '/opt/postgresql/pg_log/',
                 '/opt/postgresql/basebackup/crg-', '/tmp/crg-', '/var/tmp/crg-')


class Rejected(Exception):
    pass


def require(value, reason):
    if not value:
        raise Rejected(reason)


def executable_abi(proc_fd):
    fd=os.open('exe',os.O_RDONLY,dir_fd=proc_fd)
    try:header=os.read(fd,20)
    finally:os.close(fd)
    if len(header)==20 and header[:6]==b'\x7fELF\x02\x01' and header[18:20]==b'\x3e\x00':
        return 'linux-x86_64'
    return 'unknown'


def syscall(text, abi):
    fields=text.strip().split()
    if fields==['running']:
        return {'available':False,'reason':'task-running'}
    require(1<=len(fields)<=9 and re.fullmatch(r'-?[0-9]{1,12}',fields[0]),'SYSCALL_FORMAT')
    number=int(fields[0])
    if number==-1:
        require(len(fields)==3 and all(re.fullmatch(r'0x[0-9a-fA-F]{1,16}',v) for v in fields[1:]),'SYSCALL_FORMAT')
        return {'available':False,'reason':'outside-system-call'}
    require(number>=0 and len(fields)==9 and all(re.fullmatch(r'0x[0-9a-fA-F]{1,16}',v) for v in fields[1:]),'SYSCALL_FORMAT')
    out={'available':True,'number':number,'abi':abi,'operation':'unknown','FD_argument_available':False}
    if abi=='linux-x86_64' and number in FD_CALLS:
        out['operation']=FD_CALLS[number]
        value=int(fields[1],16)
        if value<=65535:
            out.update(FD_argument_available=True,fd=value)
    # No other arguments, registers, pointers, PC or SP leave this function.
    return out


def kernel_stack(text):
    if not text.strip():return {'available':False,'reason':'empty-kernel-stack'}
    lines=text.splitlines();frames=[];unknown=0
    for line in lines[:32]:
        match=re.fullmatch(r'\s*(?:\[<[0-9a-fA-F]+>\]\s*)?([A-Za-z_][A-Za-z0-9_.]{0,95})(?:\+0x[0-9a-fA-F]+/0x[0-9a-fA-F]+)?(?:\s+\[[A-Za-z0-9_]+\])?\s*',line)
        if match:
            if len(frames)<MAX_FRAMES:frames.append(match[1])
        elif line.strip():unknown+=1
    return {'available':True,'frames':frames,'unknown_lines':unknown,
            'truncated':len(lines)>32 or len([v for v in lines if v.strip()])>MAX_FRAMES,
            'addresses_and_offsets_recorded':False}


def fd_metadata(value):
    deleted=value.endswith(' (deleted)')
    if deleted:value=value[:-10]
    if re.fullmatch(r'pipe:\[[0-9]+\]',value):return {'kind':'pipe'}
    if re.fullmatch(r'socket:\[[0-9]+\]',value):return {'kind':'socket'}
    if value.startswith('anon_inode:'):return {'kind':'anonymous-inode'}
    if len(value)<=512 and re.fullmatch(r'/[A-Za-z0-9_./-]+',value) and '..' not in PurePosixPath(value).parts and value.startswith(ALLOWED_ROOTS):
        return {'kind':'allowlisted-path','path':value,'deleted':deleted}
    return {'kind':'redacted-other-path','deleted':deleted}


def error_reason(error):
    if isinstance(error,Rejected):return str(error)
    name=type(error).__name__
    return name if name in ['PermissionError','FileNotFoundError','ProcessLookupError','UnicodeDecodeError','OSError','ValueError'] else 'diagnostic-error'


def capture(task_fd, proc_fd, expected, read_at, stat_fields, abi):
    """Read one already-bound task, then recheck task and syscall identity.

    Missing permissions/config/data stay unknown. A matching FD link before/after
    narrows races but does not establish atomic identity of an open description.
    """
    fd_dir=None
    try:
        before=stat_fields(read_at(task_fd,'stat'))
        require(all(before[k]==expected[k] for k in ['pid','start_ticks']),'TASK_CHANGED')
        text=read_at(task_fd,'syscall',512)
        call=syscall(text,abi)
        try:stack=kernel_stack(read_at(task_fd,'stack',MAX_STACK_BYTES))
        except Exception as error:stack={'available':False,'reason':error_reason(error)}
        link=None
        if call.get('FD_argument_available'):
            try:
                fd_dir=os.open('fd',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=task_fd)
                link=os.readlink(str(call['fd']),dir_fd=fd_dir)
                descriptor={'available':True,**fd_metadata(link)}
            except Exception as error:descriptor={'available':False,'reason':error_reason(error)}
        else:descriptor={'available':False,'reason':'no-allowlisted-FD-argument'}
        require(read_at(task_fd,'syscall',512)==text,'SYSCALL_CHANGED')
        if link is not None:
            require(os.readlink(str(call['fd']),dir_fd=fd_dir)==link,'FD_LINK_CHANGED')
        after=stat_fields(read_at(task_fd,'stat'))
        require(all(after[k]==expected[k] for k in ['pid','start_ticks']),'TASK_CHANGED')
        return {'available':True,'syscall':call,'kernel_stack':stack,'descriptor':descriptor,
                'state_before':before['state'],'state_after':after['state'],
                'task_identity_rechecked':True,'separate_reads_not_atomic':True}
    except Exception as error:
        return {'available':False,'reason':error_reason(error),'separate_reads_not_atomic':True}
    finally:
        if fd_dir is not None:os.close(fd_dir)
