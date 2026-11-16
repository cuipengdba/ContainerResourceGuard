#!/usr/bin/env python3
"""Save the exact live seven-day capture once; no business/controller mutations.

Pending/default calls write nothing. A seal is identity evidence, never acceptance.
"""
import argparse
import ctypes
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
CONTRACT_SHA='e5fb0badf18274a62ed6810f1085cc99d7670d502d6eb074e2450ad9aa1248b6'
ENTRY=Path('/var/tmp/crg-capture1958-tools-20261116/tests/live-capacity-aged-v1/capture-v3.py')
ROOT=Path('/var/tmp/crg-aged-source37-inputs-20261116')
PARENT=Path('/var/tmp')
SEAL='lineage-seal.json'
ATTEMPT='.capture-v1'


def require(ok,reason):
    if not ok:raise ValueError(reason)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()


def clean(path):
    path=Path(path);require(path.is_absolute() and '..' not in path.parts,'CLEAN_ABSOLUTE_PATH')
    for p in [path,*path.parents]:require(not p.is_symlink(),'SYMLINK_PATH')
    return path


def regular(path):
    path=clean(path);before=path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size<=8*1024**2,'REGULAR_BOUNDED_INPUT')
    with path.open('rb') as stream:raw=stream.read();after=os.fstat(stream.fileno())
    require((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns),'INPUT_CHANGED')
    return raw


def checked_sources(cfg):
    require(cfg['entry']==str(ENTRY) and cfg['input_root']==str(ROOT),'FIXED_CAPTURE_PATHS')
    root=clean(Path(cfg['capture_tools']))
    for name,expected in cfg['files_sha256'].items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts,'RELATIVE_FROZEN_PATH')
        require(sha(regular(root/name))==expected,'FROZEN_CAPTURE_SOURCE')


def load_capture():
    raw=regular(HERE/'capture-save-contract.json');require(sha(raw)==CONTRACT_SHA,'CAPTURE_SAVE_CONTRACT')
    cfg=json.loads(raw);checked_sources(cfg)
    spec=importlib.util.spec_from_file_location('source37_save_capture',ENTRY)
    c=importlib.util.module_from_spec(spec);sys.modules[spec.name]=c;spec.loader.exec_module(c)
    return c,cfg


def window(c):
    state,inputs=c.g.component()
    if state['phase']=='pending' and not state.get('capture_allowed'):
        return dict(phase='pending',reason='ORIGINAL_SEVEN_DAY_CAPTURE_WINDOW_NOT_OPEN',
            component_phase=state.get('component_phase'),capture_saved=False),state,inputs
    require(state['phase']=='pending' and state.get('capture_allowed') is True
        and state.get('runner_identity_verified_live') is True,'REAL_CAPTURE_WINDOW_CLOSED_OR_NOT_LIVE')
    for name in ['baseline','enforce']:
        require(state['reports'][name]['audit']['phase']=='passed'
            and inputs[2]['phases'][name]['native_accepted'] is True,'BOTH_ORIGINAL24H_REQUIRED')
    require(inputs[3]['phase']=='measuring','SEVEN_DAY_STILL_MEASURING')
    return {'phase':'ready-to-save','capture_saved':False},state,inputs


def validate(raw,c,state,inputs):
    value=json.loads(raw)
    require(value['schema']=='crg-aged-lineage-seal-v1' and value['phase']=='lineage-captured-not-accepted'
        and value['plan_sha256']==c.BINDING_SHA256 and value['source_revision']==c.BINDING['source_revision']
        and value['binary_sha256']==c.BINDING['binary_sha256'] and value['launch']==inputs[1]
        and value['namespace_uid']==inputs[2]['namespace_uid']
        and value['seal_is_not_acceptance'] is True and value['P10_complete'] is False
        and value['release_accepted'] is False and value['postflight_allowed'] is False,'EXACT_CAPTURE_SCHEMA_AND_SOURCE')
    require(value['fresh_three_phase_binding']=={'binding_sha256':c.BINDING_SHA256,
        'long_plan_sha256':c.BINDING['long_plan_sha256'],
        'baseline_report_sha256':state['reports']['baseline']['sha256'],
        'enforce_report_sha256':state['reports']['enforce']['sha256']},'ORIGINAL24H_REPORT_BINDING')
    require(set(value['roles'])=={'dbs','hisdbs'},'EXACT_TWO_ROLE_SET')
    c.g.base.audit.timestamp(value['capture_utc'])
    for role,row in value['roles'].items():
        original=inputs[2]['roles']['candidate1-'+role+'-bw64']
        require(row['controls']==original['enforce_controls'] and row['controls']['memory.high']=='20001980416'
            and row['controls']['memory.max']=='21474836480'
            and set(row['directories'])==set(c.DIRECTORIES)
            and set(row['files'])==set(c.immutable_files(role)) and row['log_prefixes'], 'CAPTURE_ROLE_SHAPE')
    return value


def sync_dir(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


def exclusive(path,raw):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
    sync_dir(path.parent)


def save_json(path,value):exclusive(path,(json.dumps(value,indent=2)+'\n').encode())


def publish_noreplace(source,destination):
    # Atomic same-filesystem publication, preserving one link and exact stdout.
    # Unsupported syscall/filesystem fails closed; never fall back to overwrite.
    regular(source);clean(destination)
    libc=ctypes.CDLL(None,use_errno=True);rename=libc.renameat2
    rename.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
    rename.restype=ctypes.c_int
    if rename(-100,os.fsencode(source),-100,os.fsencode(destination),1)!=0:
        number=ctypes.get_errno();raise OSError(number,os.strerror(number))
    sync_dir(source.parent);sync_dir(destination.parent)


def collect():
    result=subprocess.run([sys.executable,'-B',str(ENTRY),'--capture'],stdin=subprocess.DEVNULL,
        capture_output=True,timeout=45,cwd=ENTRY.parent)
    require(len(result.stdout)<=8*1024**2 and len(result.stderr)<=65536,'BOUNDED_CAPTURE_OUTPUT')
    return result.returncode,result.stdout,result.stderr


def save_once(c,cfg):
    ready,state,inputs=window(c)
    require(ready['phase']=='ready-to-save','READINESS_CHANGED_BEFORE_CAPTURE')
    checked_sources(cfg);clean(ROOT);require(ROOT.parent==PARENT,'FIXED_CAPTURE_PARENT')
    os.umask(0o077);ROOT.mkdir(mode=0o700,exist_ok=True)
    info=ROOT.lstat();require(stat.S_ISDIR(info.st_mode) and info.st_uid==os.geteuid()
        and stat.S_IMODE(info.st_mode)==0o700,'PRIVATE_OWNED_INPUT_ROOT')
    require(not (ROOT/SEAL).exists() and not (ROOT/SEAL).is_symlink(),'SEAL_ALREADY_EXISTS')
    attempt=ROOT/ATTEMPT;attempt.mkdir(mode=0o700,exist_ok=False);sync_dir(ROOT);sync_dir(ROOT.parent)
    try:
        save_json(attempt/'intent.json',{'schema':'crg-capture-save-intent-v1','entry':str(ENTRY),
            'adapter_sha256':cfg['files_sha256']['tests/live-capacity-aged-v1/capture-v3.py'],
            'saver_sha256':sha(regular(Path(__file__).resolve())),'contract_sha256':CONTRACT_SHA,
            'started_utc':utc(),'automatic_retry_allowed':False})
        code,raw,err=collect();exclusive(attempt/'stdout.candidate',raw);exclusive(attempt/'stderr.log',err)
        require(code==0,'CAPTURE_SUBPROCESS_EXIT');value=validate(raw,c,state,inputs)
        # Recheck real process/window and immutable 24h reports after collection.
        after,new_state,new_inputs=window(c);require(after['phase']=='ready-to-save','CAPTURE_WINDOW_CHANGED')
        validate(raw,c,new_state,new_inputs);checked_sources(cfg)
        publish_noreplace(attempt/'stdout.candidate',ROOT/SEAL)
        require(regular(ROOT/SEAL)==raw and stat.S_IMODE((ROOT/SEAL).stat().st_mode)==0o600,'PUBLISHED_EXACT_STDOUT')
        result={'schema':'crg-capture-save-receipt-v1','phase':'saved-lineage-not-accepted',
            'seal_path':str(ROOT/SEAL),'seal_sha256':sha(raw),'seal_bytes':len(raw),
            'capture_utc':value['capture_utc'],'saved_utc':utc(),
            'adapter_sha256':cfg['files_sha256']['tests/live-capacity-aged-v1/capture-v3.py'],
            'capture_saved':True,'actual_duration_accepted':False,'postflight_allowed':False,
            'P10_complete':False,'release_accepted':False,'automatic_retry_allowed':False}
        save_json(attempt/'receipt.json',result);return result
    except BaseException as error:
        save_json(attempt/'error.json',{'schema':'crg-capture-save-error-v1','reason':type(error).__name__,
            'ended_utc':utc(),'automatic_retry_allowed':False,'manual_inspection_required':True})
        raise


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--save',action='store_true');a=p.parse_args(argv)
    try:
        require(sys.platform=='linux' and os.geteuid()==0,'LINUX_TEST_NODE_ROOT_REQUIRED')
        c,cfg=load_capture();result,_,_=window(c)
        if a.save and result['phase']=='ready-to-save':result=save_once(c,cfg)
        result.update(P10_complete=False,release_accepted=False)
    except (OSError,TypeError,KeyError,AttributeError,ValueError,subprocess.SubprocessError) as error:
        result={'phase':'rejected','reason':str(error) if isinstance(error,ValueError) else type(error).__name__,
            'capture_saved':False,'P10_complete':False,'release_accepted':False}
    print(json.dumps(result,indent=2))
    return 2 if result['phase']=='pending' else 1 if result['phase']=='rejected' else 0


if __name__=='__main__':sys.exit(main())
