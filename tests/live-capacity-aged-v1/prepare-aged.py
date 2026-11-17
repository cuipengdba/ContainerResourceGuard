#!/usr/bin/env python3
"""Prepare exact aged inputs once after original terminal and trusted capture.

No workload/controller mutations. Pending/default calls create no targets.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
CONTRACT_SHA='dc8272198e7f0762971950ee77aba06a8d621301b41439cd649bade19476b370'
ATTEMPT='.authority-v2'


def require(ok,reason):
    if not ok:raise ValueError(reason)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m;spec.loader.exec_module(m);return m


def checked_sources(cfg):
    for base,files in cfg['source_sets'].items():
        base=Path(base);require(base.is_absolute() and '..' not in base.parts,'CLEAN_SOURCE_ROOT')
        for name,expected in files.items():
            require(not Path(name).is_absolute() and '..' not in Path(name).parts,'RELATIVE_SOURCE')
            p=base/name;require(all(not x.is_symlink() for x in [p,*p.parents]),'SOURCE_SYMLINK')
            require(p.is_file() and p.stat().st_nlink==1 and sha(p.read_bytes())==expected,'FROZEN_PREPARATION_SOURCE')


def load_runtime():
    raw=(HERE/'prepare-contract.json').read_bytes();require(sha(raw)==CONTRACT_SHA,'PREPARE_CONTRACT_SHA')
    cfg=json.loads(raw);checked_sources(cfg)
    e=load('source37_prepare_executor',Path(cfg['executor']))
    s=load('source37_prepare_saver',Path(cfg['saver']));c,_=s.load_capture()
    require(e.CONTRACT_SHA==cfg['executor_contract_sha256'] and s.CONTRACT_SHA==cfg['saver_contract_sha256'],'EXACT_DEPENDENCY_CONTRACTS')
    return e,s,c,cfg


def private_file(s,path):
    raw=s.regular(path);info=Path(path).lstat()
    require(info.st_uid==os.geteuid() and stat.S_IMODE(info.st_mode)==0o600,'PRIVATE_OWNED_INPUT')
    return raw


def authority_value(e,seal_sha):
    p=e.CONTRACT['previous']
    return {'schema':'crg-source37-aged-execution-authority-v2',
        'contract_sha256':e.CONTRACT_SHA,'executor_sha256':e.gate.digest(Path(e.__file__))['sha256'],
        'lineage_sha256':e.LINEAGE_SHA,'binding_sha256':e.lineage.BINDING_SHA256,
        'seal_path':e.CONTRACT['seal_path'],'seal_sha256':seal_sha,
        'previous_sha256':e.PINS['previous'],'previous_source_revision':p['source_revision'],
        'previous_tag':p['tag'],'previous_release_id':p['release_id']}


def inspect(e,s,c,cfg,seal_sha=None,receipt_sha=None):
    e.checked_contract();state,inputs=e.lineage.component()
    if state['phase']=='pending':return {'phase':'pending','reason':'ORIGINAL_THREE_STAGES_NOT_TERMINAL','prepared':False},None
    require(state['phase']=='component-accepted','ORIGINAL_COMPONENT_NOT_ACCEPTED')
    if seal_sha is None and receipt_sha is None:
        return {'phase':'pending','reason':'TRUSTED_SEAL_AND_CAPTURE_RECEIPT_DIGESTS_REQUIRED','prepared':False},None
    require(re.fullmatch('[0-9a-f]{64}',seal_sha or '') and re.fullmatch('[0-9a-f]{64}',receipt_sha or ''),'TRUSTED_CAPTURE_DIGEST_PAIR')
    root=s.clean(Path(e.CONTRACT['seal_path']).parent);info=root.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid==os.geteuid() and stat.S_IMODE(info.st_mode)==0o700,'PRIVATE_CAPTURE_ROOT')
    seal_raw=private_file(s,Path(e.CONTRACT['seal_path']));require(sha(seal_raw)==seal_sha,'TRUSTED_SEAL_SHA')
    receipt_raw=private_file(s,root/'.capture-v1/receipt.json');require(sha(receipt_raw)==receipt_sha,'TRUSTED_CAPTURE_RECEIPT_SHA')
    intent=json.loads(private_file(s,root/'.capture-v1/intent.json'));receipt=json.loads(receipt_raw)
    require(intent['schema']=='crg-capture-save-intent-v1' and intent['entry']==cfg['capture_entry']
        and intent['adapter_sha256']==cfg['capture_sha256'] and intent['saver_sha256']==cfg['saver_sha256']
        and intent['contract_sha256']==cfg['saver_contract_sha256'] and intent['automatic_retry_allowed'] is False,'CAPTURE_INTENT_SOURCE')
    require(receipt['schema']=='crg-capture-save-receipt-v1' and receipt['phase']=='saved-lineage-not-accepted'
        and receipt['seal_path']==e.CONTRACT['seal_path'] and receipt['seal_sha256']==seal_sha
        and type(receipt['seal_bytes']) is int and receipt['seal_bytes']==len(seal_raw)
        and receipt['adapter_sha256']==cfg['capture_sha256'] and receipt['capture_saved'] is True
        and all(receipt[n] is False for n in ['actual_duration_accepted','postflight_allowed','P10_complete','release_accepted','automatic_retry_allowed']), 'CAPTURE_RECEIPT_BINDING')
    seal=s.validate(seal_raw,c,state,inputs);require(receipt['capture_utc']==seal['capture_utc'],'CAPTURE_TIME_BINDING')
    stamp=e.gate.audit.timestamp
    require(stamp(intent['started_utc'])<=stamp(seal['capture_utc'])<=stamp(receipt['saved_utc']),'CAPTURE_RECORD_ORDER')
    ready=e.lineage.readiness(state,inputs,seal,seal_sha,seal_sha)
    require(ready.get('postflight_allowed') is True,'REAL_RETAINED_LINEAGE_NOT_READY')
    e.no_other_mounts([Path(e.lineage.BINDING['component_root'])/'fixture'/(r+'-business') for r in ['dbs','hisdbs']])
    data=private_file(s,Path(cfg['previous_staging']))
    require(len(data)==e.CONTRACT['previous']['size'] and sha(data)==e.PINS['previous']
        and sha(data)!=e.CONTRACT['original_legacy_previous']['sha256'],'HIGH_COMPATIBLE_PREVIOUS_CONTENT')
    require(data[:6]==b'\x7fELF\x02\x01' and struct.unpack('<H',data[18:20])[0]==62,'AMD64_ELF_HEADER')
    for path in cfg['execution_targets']:require(not s.clean(Path(path)).exists(),'NO_EXECUTION_ATTEMPT_ALREADY_PRESENT')
    checked_sources(cfg)
    result={'phase':'ready-to-prepare','prepared':False,'seal_sha256':seal_sha,'capture_receipt_sha256':receipt_sha,
        'previous_sha256':sha(data),'previous_bytes':len(data),'actual_postflight_executed':False}
    return result,{'root':root,'seal_sha':seal_sha,'receipt_sha':receipt_sha,'previous':data,'lineage':ready}


def prepare_once(e,s,c,cfg,seal_sha,receipt_sha):
    ready,proof=inspect(e,s,c,cfg,seal_sha,receipt_sha);require(ready['phase']=='ready-to-prepare','READINESS_CHANGED')
    root=proof['root'];previous=Path(e.CONTRACT['previous']['path']);authority=Path(e.CONTRACT['authority_path'])
    require(previous.parent==authority.parent==root,'EXACT_INPUT_PARENT')
    require(not previous.exists() and not previous.is_symlink() and not authority.exists() and not authority.is_symlink(),'PREPARATION_INPUT_ALREADY_EXISTS')
    os.umask(0o077);attempt=root/ATTEMPT;attempt.mkdir(mode=0o700,exist_ok=False);s.sync_dir(root)
    try:
        s.save_json(attempt/'intent.json',{'schema':'crg-aged-prepare-intent-v1','started_utc':s.utc(),
            'helper_sha256':sha(s.regular(Path(__file__).resolve())),'contract_sha256':CONTRACT_SHA,
            'seal_sha256':seal_sha,'capture_receipt_sha256':receipt_sha,'automatic_retry_allowed':False})
        s.exclusive(attempt/'previous.candidate',proof['previous'])
        s.publish_noreplace(attempt/'previous.candidate',previous)
        value=authority_value(e,seal_sha);raw=(json.dumps(value,indent=2)+'\n').encode();digest=sha(raw)
        s.exclusive(attempt/'authority.candidate',raw);s.publish_noreplace(attempt/'authority.candidate',authority)
        require(e.checked_authority(authority,digest)==value,'ORIGINAL_AUTHORITY_READER')
        actual,plan=e.readiness(authority,digest)
        require(actual.get('postflight_allowed') is True and plan is not None,'ORIGINAL_EXECUTOR_READINESS_AFTER_PREPARE')
        require(sha(private_file(s,Path(e.CONTRACT['seal_path'])))==seal_sha
            and sha(private_file(s,root/'.capture-v1/receipt.json'))==receipt_sha,'CAPTURE_CHANGED_DURING_PREPARE')
        result={'schema':'crg-aged-prepare-receipt-v1','phase':'prepared-not-executed','prepared':True,
            'authority_path':str(authority),'authority_sha256':digest,'seal_sha256':seal_sha,
            'capture_receipt_sha256':receipt_sha,'previous_sha256':sha(proof['previous']),
            'executor_readiness_verified':True,'ended_utc':s.utc(),'postflight_allowed':False,
            'actual_postflight_executed':False,'P10_complete':False,'release_accepted':False,'automatic_retry_allowed':False}
        s.save_json(attempt/'receipt.json',result);return result
    except BaseException as error:
        s.save_json(attempt/'error.json',{'schema':'crg-aged-prepare-error-v1','reason':type(error).__name__,
            'ended_utc':s.utc(),'automatic_retry_allowed':False,'manual_inspection_required':True})
        raise


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare',action='store_true')
    p.add_argument('--seal-sha256');p.add_argument('--capture-receipt-sha256');a=p.parse_args(argv)
    if bool(a.seal_sha256)!=bool(a.capture_receipt_sha256):p.error('supply both actual trusted capture digests together')
    try:
        require(sys.platform=='linux' and os.geteuid()==0,'LINUX_TEST_NODE_ROOT_REQUIRED')
        e,s,c,cfg=load_runtime();result,_=inspect(e,s,c,cfg,a.seal_sha256,a.capture_receipt_sha256)
        if a.prepare and result['phase']=='ready-to-prepare':result=prepare_once(e,s,c,cfg,a.seal_sha256,a.capture_receipt_sha256)
        result.update(P10_complete=False,release_accepted=False)
    except (OSError,TypeError,KeyError,AttributeError,ValueError,struct.error) as error:
        result={'phase':'rejected','reason':str(error) if isinstance(error,ValueError) else type(error).__name__,
            'prepared':False,'P10_complete':False,'release_accepted':False}
    print(json.dumps(result,indent=2));return 2 if result['phase']=='pending' else 1 if result['phase']=='rejected' else 0


if __name__=='__main__':sys.exit(main())
