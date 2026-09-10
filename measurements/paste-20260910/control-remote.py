#!/usr/bin/env python3
"""Explicit control of this release only; all disk artifacts are preserved."""
import datetime,hashlib,json,os,pathlib,subprocess,sys
root=pathlib.Path('/home/ec2-user/paste-20260910')
name='production-paste-19a53a5'
image=pathlib.Path('/opt/attested-relay/releases')/name/'attested-relay.eif'
expected='d2803057c1a3e76f3926d582ef0062e14a29bf408c9512c5e2ca1d84f8b572cb'
mode=sys.argv[1];assert mode in ('status','stop','start')
current=json.loads(subprocess.check_output(['nitro-cli','describe-enclaves']))
if mode=='status':
 print(json.dumps({'enclaves':current,'host_online_cpus':pathlib.Path('/sys/devices/system/cpu/online').read_text().strip()},indent=2));sys.exit()
assert os.geteuid()==0, 'Run start/stop with sudo'
assert not current or (len(current)==1 and current[0]['EnclaveName']==name), 'Other enclave present; left untouched'
record={'action':mode,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'before':current}
if mode=='stop':
 if current:
  record['termination']=json.loads(subprocess.check_output(['nitro-cli','terminate-enclave','--enclave-id',current[0]['EnclaveID']]))
 pool=pathlib.Path('/sys/module/nitro_enclaves/parameters/ne_cpus')
 if pool.read_text().strip():
  fd=os.open(str(pool),os.O_WRONLY)
  try:os.write(fd,b'\n')
  finally:os.close(fd)
 huge=pathlib.Path('/sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages')
 fd=os.open(str(huge),os.O_WRONLY)
 try:os.write(fd,b'0\n')
 finally:os.close(fd)
 record['host_online_cpus']=pathlib.Path('/sys/devices/system/cpu/online').read_text().strip()
 record['hugepages_remaining']=huge.read_text().strip()
else:
 assert not current, 'Already running; no restart performed'
 assert hashlib.sha256(image.read_bytes()).hexdigest()==expected
 configured=pathlib.Path('/etc/attested-relay/host.env').read_text()
 assert 'RELAY_RELEASE=/opt/attested-relay/releases/'+name+'\n' in configured
 subprocess.run(['systemctl','restart','nitro-enclaves-allocator.service'],check=True)
 subprocess.run(['systemctl','restart','graviton5-credentials.service','graviton5-host.service'],check=True)
 record['launch']=json.loads(subprocess.check_output(['nitro-cli','run-enclave','--eif-path',str(image),'--cpu-count','14','--memory','8192','--enclave-cid','16','--enclave-name',name]))
path=root/('control-'+mode+'-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'.json')
with path.open('x') as f:json.dump(record,f,indent=2)
print(json.dumps(record,indent=2))
