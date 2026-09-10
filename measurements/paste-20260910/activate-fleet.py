from pathlib import Path
import hashlib,json,shutil,subprocess
base=Path('/opt/attested-relay-fleet-v2');venv=base/'venv-0.2.0a3'
subprocess.run([str(venv/'bin/python'),'-c','from importlib.metadata import version; from attested_relay import Relay; assert version("attested-relay")==version("attested-relay-timelock")=="0.2.0a3"; assert hasattr(Relay,"write_paste")'],check=True)
def preserve(p):
 raw=p.read_bytes();backup=p.with_name(p.name+'.before-paste-'+hashlib.sha256(raw).hexdigest())
 if not backup.exists():shutil.copy2(p,backup)
 return raw.decode()
p=base/'run-fleet.py';s=preserve(p);assert 'RELEASE = "0.2.0a2"' in s;p.write_text(s.replace('RELEASE = "0.2.0a2"','RELEASE = "0.2.0a3"'))
p=Path('/etc/attested-relay-fleet-v2/fleet.json');config=json.loads(preserve(p));assert config['expected_pcr0']=='d48f4df3b4e369ac6c97bb4b7ba0157c21ddbc4708abbe488a152ad2eead54f2418f65e622a2272f678090ad63997c42';config['expected_pcr0']='316983ca57a71682e2ffd4945248651ea6b8b28d601398f9c60cf508e6084491464baac0895e884cabb4298ee2a6e878';p.write_text(json.dumps(config,indent=2)+'\n')
for unit,role in [('attested-relay-solvers-v2','solver'),('attested-relay-mirror-v2','mirror')]:
 p=Path('/etc/systemd/system')/(unit+'.service.d');p.mkdir(exist_ok=True)
 with (p/'zz-paste-a3.conf').open('x') as f:f.write('[Service]\nEnvironment=PYTHONPATH=\nEnvironment=RELAY_TIMELOCK_BIN=\nExecStart=\nExecStart='+str(venv/'bin/python')+' '+str(base/'run-fleet.py')+' '+role+'\n')
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','restart','attested-relay-solvers-v2','attested-relay-mirror-v2'],check=True)
subprocess.run(['systemctl','is-active','attested-relay-solvers-v2','attested-relay-mirror-v2'],check=True)
print(json.dumps({'version':'0.2.0a3','expected_pcr0':config['expected_pcr0'],'workers':config['max_workers'],'bundled_solver':True}))
