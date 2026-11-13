"""Observe only a single disposable Pod UID's real kubelet probe counters."""
import json,math,re,subprocess,time
from pathlib import Path

LABELS=re.compile(r'(\w+)=("(?:\\.|[^"\\])*")')
EXPECTED_KEYS={'container','namespace','pod','pod_uid','probe_type','result'}

def selected_counters(text,expected):
    selected=[]
    for line in text.splitlines():
        if not line.startswith('prober_probe_total{'):continue
        if 'pod_uid='+json.dumps(expected['pod_uid']) not in line:continue
        match=re.fullmatch(r'prober_probe_total\{(.*)\}\s+(\S+)',line)
        if match is None:raise ValueError('OWN_PROBE_METRIC_SYNTAX')
        matches=list(LABELS.finditer(match[1]));labels={key:json.loads(value) for key,value in (m.groups() for m in matches)}
        if len(labels)!=len(matches) or set(labels)!=EXPECTED_KEYS or ','.join(m[0] for m in matches)!=match[1]:raise ValueError('OWN_PROBE_METRIC_LABELS')
        if any(labels.get(key)!=value for key,value in expected.items()):continue
        value=float(match[2])
        if not math.isfinite(value) or value<0 or value!=int(value):raise ValueError('OWN_PROBE_METRIC_COUNTER')
        if any(v['result']==labels['result'] for v in selected):raise ValueError('OWN_PROBE_DUPLICATE_RESULT')
        selected.append({'result':labels['result'],'counter':int(value),'exact_metric_line':line})
    return selected

def observe(row,namespace,pod,container,node_name,reserve,save):
    expected={'namespace':namespace,'pod':pod,'pod_uid':row['pod_uid'],'container':container,'probe_type':'Liveness'}
    result={'phase':'observing','expected_own_labels':expected,'samples':[],'maximum_gate_to_probe_observation_seconds':720,'no_other_container_metrics_saved':True}
    row['real_kubelet_probe']=result;save()
    deadline=row['gate_monotonic']+720
    while time.monotonic()<deadline:
        reserve()
        if not Path(row['group']).is_dir():result.update(phase='failed',reason='OWN_CONTAINER_GROUP_DISAPPEARED');save();return result
        sample={'gate_elapsed_seconds':time.monotonic()-row['gate_monotonic']}
        try:
            query=subprocess.run(['kubectl','get','--raw','/api/v1/nodes/'+node_name+'/proxy/metrics/probes','--request-timeout=15s'],capture_output=True,text=True,timeout=20)
            if query.returncode or len(query.stdout.encode())>1048576:sample['error']='PROBER_ENDPOINT_FAILED_OR_OVERSIZED'
            else:
                rows=selected_counters(query.stdout,expected);sample['selected_own_counters']=rows
                if any(v['result']!='successful' and v['counter']>0 for v in rows):result.update(phase='failed',reason='OWN_LIVENESS_NON_SUCCESS_COUNTER')
                elif sum(v['counter'] for v in rows if v['result']=='successful')>=1:result.update(phase='passed',reason='OWN_UID_ACTUAL_LIVENESS_SUCCESS_WITHOUT_RECORDED_FAILURE')
        except (subprocess.TimeoutExpired,ValueError) as error:sample['error']=type(error).__name__
        result['samples'].append(sample);assert len(result['samples'])<=64
        result['gate_elapsed_seconds']=time.monotonic()-row['gate_monotonic'];save()
        if result['phase']!='observing':return result
        time.sleep(min(15,max(0,deadline-time.monotonic())))
    result.update(phase='failed',reason='NO_VERIFIED_OWN_LIVENESS_SUCCESS_WITHIN_PREDECLARED_WINDOW');save();return result
