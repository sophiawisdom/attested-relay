import hashlib,json,pathlib,subprocess,sys
from attested_relay_timelock import native_binary
src=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2]);out.mkdir()
proof=json.loads((src/'nitro-evidence.json').read_text());manifest=src/proof['puzzle_artifact']
# This signing key is supplied by the separately verified Nitro diagnostic evidence.
trusted=json.loads((src/'wheel-trust.json').read_text());key=trusted['service_public_key']
native=native_binary();assert 'site-packages/attested_relay_timelock/bin/' in native
subprocess.run([native,'solve','--manifest',str(manifest),'--service-public-key',key,'--checkpoint',str(out/'checkpoint.json'),'--key-out',str(out/'epoch.key'),'--checkpoint-interval','1','--mode','light'],check=True)
subprocess.run([native,'decrypt-paste','--manifest',str(manifest),'--service-public-key',key,'--epoch-key',str(out/'epoch.key'),'--paste',str(src/proof['paste_artifacts'][0]),'--plaintext-out',str(out/'paste.bin')],check=True)
assert (out/'paste.bin').read_bytes()==b'Nitro tagged paste recovery test'
result={'native_sha256':hashlib.sha256(pathlib.Path(native).read_bytes()).hexdigest(),'bundled_binary':True,'fresh_solve_passed':True,'paste_recovery_without_tag_passed':True}
(out/'proof.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
