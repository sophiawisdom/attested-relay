import base64,datetime,hashlib,hmac,json,pathlib,secrets,subprocess,sys,time,urllib.request
from attested_relay.client import InnerTLS,Relay
from attested_relay.transport import GetTransport
from attested_relay.verify import _authenticated_document,_bound_policy,AttestationError
from attested_relay.archive import verify_bundle
import cbor2

out=pathlib.Path(sys.argv[1]);mode=sys.argv[2];expected=sys.argv[3]
assert mode in ('diagnostic','production')
out.mkdir(parents=True,exist_ok=True)
pcr=json.loads((out/'pcrs.json').read_text())['Measurements']['PCR0']
endpoint=sys.argv[4] if len(sys.argv)>4 else 'http://127.0.0.1:18080'
deadline=time.monotonic()+300
while True:
 try:
  nonce=secrets.token_bytes(32)
  stream=InnerTLS(GetTransport(endpoint,insecure_local=True,timeout=30),'localhost')
  r=stream.request('/v1/attestation?nonce='+base64.urlsafe_b64encode(nonce).decode().rstrip('='),'localhost',limit=32768)
  assert r.status_code==200,r.status_code
  raw=base64.b64decode(r.json()['attestation_document_b64'],validate=True)
  doc=_authenticated_document(raw,pcr)
  assert hmac.compare_digest(doc['nonce'],nonce)
  policy,spki=_bound_policy(doc,stream.peer_der,require_graviton5=True,historical=True)
  assert policy['software_version']=='0.1.0+'+expected
  assert policy['egress']=='mullvad-wireguard'
  assert policy['paste_protocol_version']==1 and policy['paste_max_bytes']==102400
  if policy['mullvad_up'] and (mode=='production' or policy['state']=='ready'):break
 except Exception as e:
  print('Waiting for authenticated Nitro readiness:',type(e).__name__,str(e)[:120],flush=True)
 if time.monotonic()>deadline:raise RuntimeError('Nitro Mullvad readiness timeout')
 time.sleep(3)
v={'nitro_evidence_authenticated':True,'policy':policy,'timestamp_ms':doc['timestamp'],'pcr0':pcr,'document_b64':base64.b64encode(raw).decode(),'peer_certificate_der_b64':base64.b64encode(stream.peer_der).decode(),'nonce_b64':base64.b64encode(nonce).decode(),'tls_spki_sha256':hashlib.sha256(spki).hexdigest(),'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
if mode=='production':
 assert policy['segments']==84 and policy['iterations']==3647344 and policy['state']=='warming'
 try:Relay(endpoint,expected_pcr0=pcr,insecure_local=True,timeout=30).verify()
 except AttestationError as e:assert str(e)=='enclave is not ready',str(e)
 else:raise AssertionError('SDK accepted warming enclave')
 r=stream.request('/f/https/am.i.mullvad.net/json','localhost',limit=32768)
 assert r.status_code==503,r.status_code
 v.update(service_ready=False,ordinary_sdk_rejects_warming=True,forward_while_warming_status=503)
else:
 assert policy['segments']==84 and policy['iterations']==8 and policy['state']=='ready'
 relay=Relay(endpoint,expected_pcr0=pcr,insecure_local=True,timeout=60)
 verified=relay.verify();response=relay.get('https://am.i.mullvad.net/json')
 assert response.status_code==200 and response.json()['mullvad_exit_ip'] is True
 headers=dict(response.headers)
 (out/'response.json').write_bytes(response.content)
 def fetch(name):
  with urllib.request.urlopen(endpoint+'/v1/artifacts/'+name,timeout=30) as r:data=r.read(32*1024*1024+1)
  assert hashlib.sha256(data).hexdigest()==name[:64]
  path=out/name
  if path.exists():assert path.read_bytes()==data
  else:path.write_bytes(data)
  return data
 puzzle_name=headers['x-attested-relay-puzzle'];record_name=headers['x-attested-relay-record']
 with urllib.request.urlopen(endpoint+'/v1/artifacts/index.json?limit=256',timeout=30) as r:listing=json.load(r)
 names=[n for n in listing['artifacts'] if n.endswith('.bundle.json')]
 bundles=[verify_bundle(n,fetch,expected_pcr0=pcr) for n in names]
 bundle=next(b for b in bundles if b['puzzle_artifact']==puzzle_name)
 fetch(record_name);key=out/'diagnostic-epoch.key';native='/root/relay-paste-20260910/attested-relay-19a53a50c3b340a192ef28955789ad083eb7bc69/target/release/relay-timelock'
 subprocess.run([native,'solve','--manifest',str(out/puzzle_name),'--service-public-key',bundle['service_public_key'],'--checkpoint',str(out/'offline.checkpoint.json'),'--key-out',str(key),'--checkpoint-interval','1','--mode','light'],check=True,timeout=90)
 plaintext=out/'decrypted-record.cbor'
 subprocess.run([native,'decrypt-record','--manifest',str(out/puzzle_name),'--service-public-key',bundle['service_public_key'],'--epoch-key',str(key),'--record',str(out/record_name),'--plaintext-out',str(plaintext)],check=True,timeout=30)
 record=cbor2.loads(plaintext.read_bytes())
 assert record['request']['url']=='https://am.i.mullvad.net/json'
 assert base64.b64decode(record['exchanges'][-1]['response_body_b64'])==response.content
 relay.verify()  # Offline solving may outlast the transport idle timeout.
 tag=relay.new_paste_tag();other=relay.new_paste_tag()
 first=relay.write_paste(tag,b"Nitro tagged paste recovery test")
 second=relay.write_paste(tag,b"B"*102400)
 third=relay.write_paste(other,b"separate tag")
 assert first['tag_id']==second['tag_id'] and first['tag_id']!=third['tag_id']
 page=relay.read_pastes(tag,limit=1);assert page['next_cursor']
 page2=relay.read_pastes(tag,limit=1,after=page['next_cursor']);assert page2['next_cursor'] is None
 assert {p['id']:p['content'] for p in page['pastes']+page2['pastes']}=={first['id']:b"Nitro tagged paste recovery test",second['id']:b"B"*102400}
 assert relay.read_pastes(tag+'wrong')['pastes']==[]
 for written in (first,second,third):
  rawpaste=fetch(written['id']);paste=json.loads(rawpaste)
  assert paste['tag_id']==written['tag_id'] and tag.encode() not in rawpaste
  assert written['puzzle']==puzzle_name
 decoded=out/'decrypted-paste.bin'
 subprocess.run([native,'decrypt-paste','--manifest',str(out/puzzle_name),'--service-public-key',bundle['service_public_key'],'--epoch-key',str(key),'--paste',str(out/first['id']),'--plaintext-out',str(decoded)],check=True,timeout=30)
 assert decoded.read_bytes()==b"Nitro tagged paste recovery test"
 v.update(paste_write_read_passed=True,paste_100kib_passed=True,paste_pagination_passed=True,paste_wrong_tag_passed=True,paste_public_recovery_without_tag_passed=True,paste_artifacts=[x['id'] for x in (first,second,third)],public_tag_id=first['tag_id'])
 v.update(diagnostic_only=True,seven_day_claim=False,mullvad_exit=response.json(),response_sha256=hashlib.sha256(response.content).hexdigest(),offline_recovery_passed=True,record_artifact=record_name,puzzle_artifact=puzzle_name)
(out/'nitro-evidence.json').write_text(json.dumps(v,indent=2)+'\n')
print(json.dumps({k:v[k] for k in v if not k.endswith('_b64')},indent=2))
