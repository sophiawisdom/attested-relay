"""Activate only the explicitly selected, frozen 84-group rollout images."""
import datetime,hashlib,json,pathlib,subprocess,sys
mode=sys.argv[1];assert mode in ('diagnostic','production')
root=pathlib.Path('/home/ec2-user/paste-20260910')
rev={'diagnostic':'5dfd2e5c4e9d4fac605cffa094ecfe61953c61c5','production':'19a53a50c3b340a192ef28955789ad083eb7bc69'}[mode]
name=mode+'-paste-'+rev[:7]
source=root/('source-diagnostic' if mode=='diagnostic' else 'source')
build=root/('build-diagnostic' if mode=='diagnostic' else 'build')
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD']).decode().strip()==rev
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain']).strip()
info=json.loads((build/'build-info.json').read_text());assert info['source_commit']==rev
assert info['eif_sha256']==hashlib.sha256((build/'attested-relay.eif').read_bytes()).hexdigest()
pcr=json.loads((build/'pcrs.json').read_text())['Measurements']
desc=json.loads(subprocess.check_output(['nitro-cli','describe-eif','--eif-path',str(build/'attested-relay.eif')]))
assert desc['CheckCRC'] and all(desc['Measurements'][k]==pcr[k] for k in ('PCR0','PCR1','PCR2'))
assert ('iterations = 8\n' if mode=='diagnostic' else 'iterations = 3647344\n') in (source/'config/relay-v2.toml').read_text()
old=json.loads(subprocess.check_output(['nitro-cli','describe-enclaves']))
if mode=='diagnostic':
 assert len(old)==1 and old[0]['EnclaveName']=='production-groups84-2737c45' and old[0]['Flags']=='NONE'
else:
 assert len(old)==1 and old[0]['EnclaveName']=='diagnostic-paste-5dfd2e5' and old[0]['Flags']=='NONE'
 proof=json.loads((root/'verified-reproduction.json').read_text())
 assert proof['pcrs_reproduced'] and proof['release']['source_commit']==rev
 assert all(proof['release']['pcrs'][k]==pcr[k] for k in ('PCR0','PCR1','PCR2'))
 diagnostic=json.loads((root/'diagnostic-nitro-evidence.json').read_text())
 assert diagnostic['offline_recovery_passed'] and diagnostic['policy']['segments']==84
 assert diagnostic['paste_public_recovery_without_tag_passed'] and diagnostic['paste_100kib_passed']
 assert diagnostic['policy']['software_version']=='0.1.0+5dfd2e5c4e9d4fac605cffa094ecfe61953c61c5'
evidence=root/(name+'-launch');evidence.mkdir()
(evidence/'prior-enclaves.json').write_text(json.dumps(old,indent=2)+'\n')
if old:
 (evidence/'terminated-diagnostic.json').write_bytes(subprocess.check_output(['nitro-cli','terminate-enclave','--enclave-id',old[0]['EnclaveID']]))
subprocess.run(['sudo','systemctl','restart','nitro-enclaves-allocator.service'],check=True)
subprocess.run(['sudo','bash',str(source/'deploy/graviton5-install-release.sh'),str(build),name],check=True)
(evidence/'launched-at.txt').write_text(datetime.datetime.now(datetime.timezone.utc).isoformat()+'\n')
run=subprocess.check_output(['nitro-cli','run-enclave','--eif-path',str(build/'attested-relay.eif'),'--cpu-count','14','--memory','8192','--enclave-cid','16','--enclave-name',name])
(evidence/'run-enclave.json').write_bytes(run)
print(run.decode())
