#!/usr/bin/env python3
"""Synthetic gate/rollback-safety tests, never a duration or business acceptance."""
import ast
import contextlib
import copy
import hashlib
import importlib.util
import inspect
import io
import json
import os
from pathlib import Path,PurePosixPath
import sys
import unittest
from unittest.mock import patch,Mock
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('source37_aged_executor_v2',HERE/'executor-v2.py')
e=importlib.util.module_from_spec(spec);sys.modules[spec.name]=e;spec.loader.exec_module(e)

def authority():
 return {'schema':'crg-source37-aged-execution-authority-v2','contract_sha256':e.CONTRACT_SHA,
  'executor_sha256':'e'*64,'lineage_sha256':e.LINEAGE_SHA,'binding_sha256':e.lineage.BINDING_SHA256,
  'seal_path':e.CONTRACT['seal_path'],'previous_sha256':e.PINS['previous'],
  'previous_source_revision':e.CONTRACT['previous']['source_revision'],
  'previous_tag':e.CONTRACT['previous']['tag'],'previous_release_id':e.CONTRACT['previous']['release_id'],
  'seal_sha256':'s'*64}

def native():
 bounds=[.001,.005,.01,.02,.05,.1,.25,.5,1,2,5,'over-5']
 return dict(schema='crg-vendor-soak-v1',phase='passed',run_id='test',test_phase='smoke',
  requested_duration_seconds=600,elapsed_seconds=600.1,interrupted=False,threads_stopped=True,
  payload_integrity=True,primary_not_restarted=True,primary_start_time_initial='same',primary_start_time_final='same',
  initial_checksum=[16384,134225920,67108864,'payload',0],final_checksum=[16384,134225920,67108864,'payload',100],
  criteria=dict(sql_period_seconds=2,api_period_seconds=5,maximum_seconds=5,p95_upper_bound_seconds=1,maximum_errors=0,minimum_scheduled_samples_fraction=.98),
  latency_bucket_upper_seconds=bounds,
  **{kind:dict(attempts=n,successes=n,errors=0,max_seconds=.1,histogram=[0]*5+[n]+[0]*6,p95_bucket_upper_seconds=.1) for kind,n in [('sql',300),('api',120)]})

class Checks(unittest.TestCase):
 def test_pending_never_reads_seal_previous_inventory_or_constructs_execution(self):
  pending=dict(phase='pending',component_phase='measuring-baseline',postflight_allowed=False)
  with patch.object(e.lineage,'component',return_value=(pending,None)),patch.object(e.gate,'read_json',side_effect=AssertionError('late read')),patch.object(e.gate,'digest',side_effect=AssertionError('late artifact')),patch.object(e,'no_other_mounts',side_effect=AssertionError('late inventory')),patch.object(e,'Execution',side_effect=AssertionError('mutation')):
   value,plan=e.readiness(Path('/not/an/authority'),'0'*64)
  self.assertEqual(value['phase'],'pending');self.assertFalse(value['postflight_allowed']);self.assertIsNone(plan)

 def test_execute_flag_and_marker_still_pending_without_writes(self):
  with patch.object(e.lineage,'component',return_value=({'phase':'pending'},None)),patch.object(e.sys,'platform','linux'),patch.object(e.os,'geteuid',return_value=0,create=True),patch.dict(os.environ,CRG_AGED_POSTFLIGHT='authorized-disposable-test-node-only'),patch.object(e,'Execution',side_effect=AssertionError('mutation')),contextlib.redirect_stdout(io.StringIO()) as out:
   code=e.main(['--execute'])
  self.assertEqual(code,2);self.assertFalse(json.loads(out.getvalue())['postflight_allowed'])

 def test_original_three_stage_failure_propagates(self):
  with patch.object(e.lineage,'component',side_effect=e.Rejected('NATIVE_DURATION')),self.assertRaisesRegex(e.Rejected,'NATIVE_DURATION'):e.readiness()

 def test_accepted_component_without_actual_authority_is_pending(self):
  with patch.object(e.lineage,'component',return_value=({'phase':'component-accepted'},None)),patch.object(e.gate,'read_json',side_effect=AssertionError('seal read')):
   value,plan=e.readiness()
  self.assertEqual(value['reason'],'ACTUAL_AUTHORITY_REQUIRED');self.assertIsNone(plan)

 def test_exact_authority_and_each_foreign_or_legacy_binding_rejected(self):
  good=authority();good['seal_sha256']='b'*64
  path=Path(e.CONTRACT['authority_path'])
  with patch.object(e.gate,'digest',return_value={'sha256':'e'*64}),patch.object(e.gate,'read_json',return_value=(good,'a'*64)):
   self.assertEqual(e.checked_authority(path,'a'*64),good)
  for key in good:
   bad=copy.deepcopy(good);bad[key]='wrong'
   if key=='previous_sha256':bad[key]=e.CONTRACT['original_legacy_previous']['sha256']
   with self.subTest(key=key),patch.object(e.gate,'digest',return_value={'sha256':'e'*64}),patch.object(e.gate,'read_json',return_value=(bad,'a'*64)),self.assertRaisesRegex(e.Rejected,'AUTHORITY_EXACT_BINDINGS'):e.checked_authority(path,'a'*64)
  with patch.object(e.gate,'read_json',return_value=(good,'a'*64)),self.assertRaisesRegex(e.Rejected,'AUTHORITY_DIGEST'):e.checked_authority(path,'c'*64)

 def test_authority_rejects_missing_path_or_digest(self):
  for path,digest in [(None,None),(Path('/wrong'),'a'*64),(Path(e.CONTRACT['authority_path']),'bad')]:
   with self.subTest(path=str(path)),self.assertRaises(e.Rejected):e.checked_authority(path,digest)

 def test_ready_requires_original_lineage_and_exact_programs(self):
  seal={'roles':{r:{'files':{'pod.json':{'sha256':'p'*64}}} for r in ['dbs','hisdbs']}}
  def digest(path):
   if path.name=='pod.json':return {'sha256':'p'*64}
   if path.name=='containercacheguard':return {'sha256':e.PINS['cache']}
   if path.as_posix()==e.CONTRACT['previous']['path']:return {'sha256':e.PINS['previous'],'size':e.CONTRACT['previous']['size']}
   if path.as_posix()==e.CONTRACT['worker']:return {'sha256':e.PINS['worker']}
   return {'sha256':e.PINS['binary']}
  with patch.object(e.lineage,'component',return_value=({'phase':'component-accepted'},('inputs',))),patch.object(e,'checked_authority',return_value={'seal_path':e.CONTRACT['seal_path'],'seal_sha256':'b'*64}),patch.object(e.gate,'read_json',return_value=(seal,'b'*64)),patch.object(e.lineage,'readiness',return_value={'phase':'ready-for-postflight','postflight_allowed':True}) as original,patch.object(e.gate,'lab_root'),patch.object(e.gate,'path_clean',side_effect=Path),patch.object(e.gate,'digest',side_effect=digest),patch.object(e,'no_other_mounts') as mounts:
   value,plan=e.readiness(Path(e.CONTRACT['authority_path']),'a'*64)
   original.assert_called_once();mounts.assert_called_once();self.assertFalse(value['original_legacy_managed_resume_accepted'])
   self.assertEqual(plan['roles']['dbs']['aged_run_id'],'202611161882')
   with patch.object(e.gate,'digest',side_effect=lambda p:dict(digest(p),sha256='bad') if p.as_posix()==e.CONTRACT['previous']['path'] else digest(p)),self.assertRaisesRegex(e.Rejected,'HIGH_COMPATIBLE_PREVIOUS_ARTIFACT'):e.readiness(Path(e.CONTRACT['authority_path']),'a'*64)

 def test_execute_requires_marker_and_rechecks_readiness_before_constructor(self):
  ready={'phase':'ready-for-postflight','postflight_allowed':True}
  with patch.object(e.sys,'platform','linux'),patch.object(e.os,'geteuid',return_value=0,create=True),patch.object(e,'Execution') as execution:
   with patch.dict(os.environ,{},clear=True),patch.object(e,'readiness',return_value=(dict(ready),{})),contextlib.redirect_stdout(io.StringIO()) as out:
    self.assertEqual(e.main(['--execute']),1)
   self.assertEqual(json.loads(out.getvalue())['reason'],'EXPLICIT_LAB_MARKER');execution.assert_not_called()
   with patch.dict(os.environ,CRG_AGED_POSTFLIGHT='authorized-disposable-test-node-only'),patch.object(e,'readiness',side_effect=[(dict(ready),{}),({'phase':'pending','postflight_allowed':False},None)]),contextlib.redirect_stdout(io.StringIO()) as out:
    self.assertEqual(e.main(['--execute']),1)
   self.assertEqual(json.loads(out.getvalue())['reason'],'READINESS_CHANGED');execution.assert_not_called()

 def test_exact_high_and_all_five_external_controls(self):
  original=dict.fromkeys(e.CONTROLS,'unchanged');active=dict(original)
  active.update({'cpu.max':'720000 100000','memory.high':'20001980416','io.max':'8:0 rbps=67108864 wbps=67108864 riops=4096 wiops=4096'})
  state={'items':[{'file':n,'state':'applied'} for n in ['cpu.max','memory.high','io.max']]}
  e.validate_managed_controls(active,original,state)
  for key in e.CONTRACT['unchanged_external_controls']+['cpu.max','memory.high','io.max']:
   bad=dict(active);bad[key]='changed'
   with self.subTest(control=key),self.assertRaisesRegex(e.Rejected,'EXACT_THREE_CONTROLS'):e.validate_managed_controls(bad,original,state)
  for items in [state['items']+[state['items'][0]], [{'file':'memory.max','state':'applied'}], [dict(x,state='skipped') for x in state['items']]]:
   with self.assertRaisesRegex(e.Rejected,'EXACT_THREE_CONTROLS'):e.validate_managed_controls(active,original,{'items':items})

 def test_native_original600s_thresholds_and_strict_counter_types(self):
  e.validate_native(native(),'test')
  faults=[lambda v:v.update(elapsed_seconds=599),lambda v:v.update(primary_not_restarted=False),lambda v:v['api'].update(errors=1),lambda v:v['sql'].update(max_seconds=5.01),lambda v:v['api'].update(successes=True),lambda v:v['sql'].update(errors=False),lambda v:v['api'].update(attempts=100,successes=100,histogram=[0]*5+[100]+[0]*6),lambda v:v.update(requested_duration_seconds=120),lambda v:v['sql'].update(histogram=[300]+[0]*10+[1]),lambda v:v['api'].update(histogram=[0]*9+[120,0,0],p95_bucket_upper_seconds=2)]
  for i,f in enumerate(faults):
   value=native();f(value)
   with self.subTest(case=i),self.assertRaises(e.Rejected):e.validate_native(value,'test')

 def test_original_consumers_guard_rejects_direct_data_or_writable_parent(self):
  root=PurePosixPath('/var/tmp/crg-aged-original/fixture/dbs-business')
  def pod(path,readonly=False,constrained=False):
   c={'volumeMounts':[{'name':'data','readOnly':readonly}]}
   if constrained:c['securityContext']={'allowPrivilegeEscalation':False,'capabilities':{'drop':['ALL']}}
   return {'spec':{'volumes':[{'name':'data','hostPath':{'path':path}}],'containers':[c]}}
  # realpath uses the native OS; use stable POSIX-like identity in these synthetic fixtures.
  with patch.object(e.os.path,'realpath',side_effect=lambda x:x):
   for value in [pod(str(root),True,True),pod(str(root.parent))]:
    with patch.object(e.gate,'command',return_value=json.dumps({'items':[value]})),self.assertRaisesRegex(e.Rejected,'AGED_DATA_ALREADY_MOUNTED'):e.no_other_mounts([root])
   with patch.object(e.gate,'command',return_value=json.dumps({'items':[pod(str(root.parent),True,True)]})):e.no_other_mounts([root])

 def test_v1_class_guards_and_all_original_criteria_retained(self):
  proof=json.loads((HERE/'executor-v2-derivation.json').read_bytes());original=(HERE/'executor.py').read_bytes()
  self.assertEqual(hashlib.sha256(original).hexdigest(),proof['v1_executor_sha256'])
  source=original.decode();tree=ast.parse(source)
  transformed=ast.get_source_segment(source,next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Execution'))
  for change in proof['exact_replacements']:
   if change['before'] in transformed:transformed=transformed.replace(change['before'],change['after'])
  self.assertEqual(inspect.getsource(e.Execution).strip(),transformed.strip())
  self.assertEqual(e.CRITERIA,proof['criteria_original_exact']);self.assertEqual(e.CRITERIA['native_seconds_each_role'],600)

 def test_resumed_process_requires_fresh_managed_snapshot_and_identity(self):
  original=dict.fromkeys(e.CONTROLS,'unchanged');original.update({'cpu.max':'800000 100000','memory.max':'21474836480','memory.high':'max','io.max':''})
  active=dict(original);active.update({'cpu.max':'720000 100000','memory.high':'20001980416','io.max':'8:0 rbps=67108864 wbps=67108864 riops=4096 wiops=4096'})
  status={'state':'managed','plan':{'environment':{'identity':'owned'}},'items':[{'file':n,'state':'applied'} for n in ['cpu.max','memory.high','io.max']]}
  args=[[[100,200,e.PINS['previous']]],e.PINS['previous'],[1,2,3],[4,5,6],status,'owned',active,original]
  self.assertTrue(e.managed_resumption(*args))
  cases=[(0,[]),(0,[[100,200,e.PINS['binary']]]),(0,[[True,200,e.PINS['previous']]]),(3,[1,2,3]),(3,[4,1,6]),(3,[4,True,6]),(4,dict(status,state='degraded')),(5,'other')]
  for index,value in cases:
   bad=copy.deepcopy(args);bad[index]=value
   with self.subTest(index=index,value=value):self.assertFalse(e.managed_resumption(*bad))
  bad=copy.deepcopy(args);bad[6]['memory.max']='20001980416'
  with self.assertRaisesRegex(e.Rejected,'EXACT_THREE_CONTROLS'):e.managed_resumption(*bad)

 def test_user_decision_rejects_legacy_max_and_keeps_historical_record(self):
  policy=e.CONTRACT['user_rollback_scope']
  self.assertFalse(policy['legacy_managed_resume_required']);self.assertTrue(policy['legacy_rejection_required'])
  self.assertFalse(policy['historical_legacy_pass_claim'])
  self.assertNotEqual(e.PINS['previous'],e.CONTRACT['original_legacy_previous']['sha256'])

if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
 print(json.dumps({'schema':'crg-source37-aged-executor-checks-v2','phase':'passed' if result.wasSuccessful() else 'failed','tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'synthetic_only':True,'postflight_executed':False,'duration_accepted':False,'release_accepted':False},indent=2))
 sys.exit(0 if result.wasSuccessful() else 1)
