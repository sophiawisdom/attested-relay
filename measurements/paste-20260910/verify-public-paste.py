import datetime,hashlib,json,pathlib,time,urllib.request
from attested_relay import Relay
root=pathlib.Path('/root/relay-paste-20260910');pcr=json.loads((root/'diagnostic-proof/pcrs.json').read_text())['Measurements']['PCR0']
relay=Relay('https://relay.sparrowsystems.co',expected_pcr0=pcr,timeout=90)
start=time.monotonic();v=relay.verify();print('Public Nitro verified',flush=True)
tag=relay.new_paste_tag();content=bytes(range(256))*400
written=relay.write_paste(tag,content);print('Public 100 KiB upload passed',flush=True)
page=relay.read_pastes(tag);assert page['pastes'][0]['content']==content
url='https://relay.sparrowsystems.co/v1/artifacts/'+written['id']
req=urllib.request.Request(url,headers={'User-Agent':'attested-relay/2'})
with urllib.request.urlopen(req,timeout=30) as response:raw=response.read(220000)
assert hashlib.sha256(raw).hexdigest()==written['id'][:64]
assert json.loads(raw)['tag_id']==written['tag_id'] and tag.encode() not in raw
proof={'endpoint':relay.endpoint,'pcr0':pcr,'policy':v['policy'],'public_100kib_write_read_passed':True,'public_artifact_hash_verified':True,'opaque_tag_id_public':True,'artifact':written['id'],'elapsed_seconds':time.monotonic()-start,'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(root/'public-paste-proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof,indent=2))
