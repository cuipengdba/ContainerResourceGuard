from pathlib import Path
import importlib.util,json,tempfile
spec=importlib.util.spec_from_file_location('pg_observer',Path(__file__).with_name('pg-process-observer.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);checks=[]
def check(name,value):assert value,name;checks.append(name)
uid='12345678-1234-1234-1234-123456789abc';cid='a'*64;group=Path('/sys/fs/cgroup/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-pod'+uid.replace('-','_')+'.slice/cri-containerd-'+cid+'.scope');row={'group':group.as_posix(),'container_id':cid,'pod_uid':uid}
check('exact-own-declared-leaf',m.group_path(row)==group)
for name,change in [('host-root',{'group':'/sys/fs/cgroup'}),('sibling',{'container_id':'b'*64}),('wrong-Pod',{'pod_uid':'87654321-1234-1234-1234-123456789abc'}),('parent-traversal',{'group':group.as_posix()+'/../other'}),('invalid-ID',{'container_id':'bad'}),('backslash',{'group':group.as_posix().replace('/','\\')}),('noncanonical',{'group':group.as_posix().replace('/kubepods.slice/','//kubepods.slice/')})]:
 try:m.group_path(dict(row,**change))
 except ValueError:check('reject-'+name,True)
 else:raise AssertionError(name)
with tempfile.TemporaryDirectory() as folder:
 root=Path(folder);proc=root/'100';proc.mkdir();state=['S','1']+['0']*17+['123']+['0']*4;(proc/'stat').write_text('100 (postgres) '+' '.join(state));(proc/'cgroup').write_text('0::/'+group.relative_to('/sys/fs/cgroup').as_posix()+'\n')
 for name,text in {'wchan':'pipe_write','stack':'[<0>] pipe_write+0x1/0x2','syscall':'1 0x1 0x2 4096','io':'read_bytes: 4096\nwrite_bytes: 8192','status':'Name:\tpostgres\nNSpid:\t100\t55\nVmRSS:\t1024 kB\nSensitive:\twithheld'}.items():(proc/name).write_text(text)
 links={'exe':'/opt/postgresql/pgsql/bin/postgres','0':'/dev/null','1':'pipe:[456]','2':'/private/path-withheld'}
 def link(path):return links[path.name]
 value=m.process(100,group,root,link);check('captures-own-wait-state-and-numeric-identity',value['wchan']=='pipe_write' and value['start_ticks']==123 and value['parent_pid']==1 and value['status']=={'NSpid':'100\t55','VmRSS':'1024 kB'})
 check('fd-links-classified-no-contents-or-paths',value['standard_fds']['1']=={'kind':'pipe','inode':456} and value['standard_fds']['2']=={'kind':'other','path_withheld':True} and '/private/' not in json.dumps(value))
 (proc/'cgroup').write_text('0::/foreign\n');check('foreign-cgroup-no-observation',m.process(100,group,root,link) is None)
 (proc/'cgroup').write_text('0::/'+group.relative_to('/sys/fs/cgroup').as_posix()+'\n');links['exe']='/bin/other';check('non-PG-no-observation',m.process(100,group,root,link) is None)
 links['exe']='/opt/postgresql/pgsql/bin/postgres';(proc/'stack').unlink();check('missing-stack-explicit-unavailable',m.process(100,group,root,link)['stack']=={'unavailable':'FileNotFoundError'})
 (proc/'wchan').write_text('x'*257);check('oversized-proc-field-explicit-unavailable',m.process(100,group,root,link)['wchan']=={'unavailable':'ValueError'})
 def reused(path):
  value=link(path)
  if path.name=='2':(proc/'stat').write_text('100 (postgres) '+' '.join(state[:19]+['124']+state[20:]))
  return value
 check('PID-reuse-during-sample-rejected',m.process(100,group,root,reused) is None)
 (proc/'stat').write_text('100 (postgres) '+' '.join(state))
 def moved(path):
  value=link(path)
  if path.name=='2':(proc/'cgroup').write_text('0::/foreign\n')
  return value
 check('cgroup-migration-during-sample-rejected',m.process(100,group,root,moved) is None)
print(json.dumps({'checks':checks,'count':len(checks),'product_resource_settings_not_modified':True}))
