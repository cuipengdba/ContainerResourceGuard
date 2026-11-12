from pathlib import Path
import copy,hashlib,importlib.util,json

t=Path(__file__).parent;p=t/'crg-vendor-diagnostic706.py';spec=importlib.util.spec_from_file_location('candidate_diagnostic',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class FailedCheck(Exception):pass
def run(success):
 snapshots=[];checks=[];row={'native120':{'api':{'attempts':1,'errors':0 if success else 1}}}
 def check(name,value):
  checks.append({'name':name,'passed':bool(value)})
  if not value:raise FailedCheck(name)
 c={'role':'dbs','row':row,'check':check,'save':lambda:snapshots.append(copy.deepcopy(row))}
 request={'started_monotonic_ns':100,'finished_monotonic_ns':400,'local_port':30001,'server_port':8090,'success':success,'socket_timeout_seconds':4}
 entry={'call':'recvfrom','fd':14,'tid':123,'monotonic_ns':200 if success else 500,'fd_metadata':{'kind':'loopback_socket','local_port':8090,'remote_port':30001,'source':'event-time-safe-kernel-metadata'}}
 send={'call':'sendto','fd':14,'tid':123,'monotonic_ns':300 if success else 600,'fd_metadata':dict(entry['fd_metadata'])}
 stream={'phase':'collected','reason':'controller-stdin','incomplete':False,'perf_lost_samples':0,'bpf_output_failures':0,'diagnostic_errors':[],'all_owned_handles_closed':True,'detached_stream_drained_to_deadline':True,'kernel_metadata_layout':{'fields':{str(i):{} for i in range(16)}},'pairs':[{'entry':entry,'exit':{'return':1}},{'entry':send,'exit':{'return':262}}]}
 caught=False
 try:m.persist_association_summary(c,stream,[request])
 except FailedCheck:caught=True
 if success:
  assert not caught and len(checks)==2 and all(v['passed'] for v in checks) and len(snapshots)==2 and row['normal_fast_request_binding_accepted']
 else:
  assert caught and len(checks)==1 and not checks[0]['passed'] and len(snapshots)==1 and not snapshots[0]['normal_fast_request_binding_accepted'] and snapshots[0]['request_associations'][0]['recv_pairs']==0 and snapshots[0]['request_associations'][0]['send_or_write_pairs']==0
 assert snapshots[0]['request_associations'][0]['request']==request and snapshots[0]['no_observed_output_loss_and_owned_collector_cleanly_stopped'] and snapshots[0]['syscall_pair_boundary_incomplete'] is False and snapshots[0]['native120']['api']['errors']==(0 if success else 1)
 return {'input_success':success,'assertion_failed':caught,'save_snapshots':len(snapshots),'checks':checks,'raw_associations_retained_before_assertion':True,'late_events_or_error_count_regraded':False}
r={'schema':'crg-diagnostic-failure-persistence-unit-v1','phase':'passed','source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'cases':[run(False),run(True)],'synthetic_unit_only_not_vendor_runtime_qualification':True,'frozen_failed_vendor693_unchanged':True};dest=t/'crg-r706-persistence-test.json';assert not dest.exists();dest.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(json.dumps(r))
