#!/usr/bin/env bash
# Extract pinned AWS tooling; do not install RPM scriptlets, drivers or services.
# Usage: bash install-nitro.sh [--verify-only] ABSOLUTE_FRESH_DIRECTORY
# Prerequisites: Python 3, bsdtar (Ubuntu: libarchive-tools), Linux ARM64 to run.
set -euo pipefail
TASK_SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
python3 - "$TASK_SCRIPT_DIR/nitro-tooling.lock.json" "$@" <<'PY'
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
import urllib.request

lock_path = Path(sys.argv[1])
args = sys.argv[2:]
verify_only = bool(args and args[0] == '--verify-only')
if verify_only:
    args = args[1:]
if len(args) != 1 or not Path(args[0]).is_absolute():
    raise SystemExit('usage: install-nitro.sh [--verify-only] ABSOLUTE_FRESH_DIRECTORY')
if not verify_only and (platform.system(), platform.machine()) != ('Linux', 'aarch64'):
    raise SystemExit('executing Nitro requires Linux aarch64; --verify-only checks downloads elsewhere')
if shutil.which('bsdtar') is None:
    raise SystemExit('bsdtar is required (Ubuntu package: libarchive-tools)')
out = Path(args[0])
# mkdir without exist_ok rejects symlinks and previous results, including failed runs.
out.mkdir(parents=True)
out = out.resolve()
packages = out / 'packages'
packages.mkdir()
root = out / 'root'
root.mkdir()
upstream = out / 'aws-upstream-blobs'
upstream.mkdir()
lock = json.loads(lock_path.read_text())
if lock['schema'] != 1 or lock['architecture'] != 'aarch64':
    raise SystemExit('unsupported tooling lock schema/architecture')

def digest(path):
    state = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            state.update(block)
    return state.hexdigest()

def download(url, destination, expected):
    # All inputs are public AWS artifacts. Preserve a failed download for diagnosis.
    if not url.startswith('https://'):
        raise SystemExit('non-HTTPS artifact URL')
    total = 0
    with urllib.request.urlopen(url, timeout=120) as response, destination.open('xb') as target:
        if not response.geturl().startswith('https://'):
            raise SystemExit('artifact redirected outside HTTPS')
        while block := response.read(1024 * 1024):
            total += len(block)
            if total > 100 * 1024 * 1024:
                raise SystemExit('unexpectedly large tooling artifact')
            target.write(block)
    actual = digest(destination)
    if actual != expected:
        raise SystemExit(f'SHA-256 mismatch for {destination.name}: {actual}')
    return {'url': url, 'sha256': actual, 'bytes': total}

package_evidence = []
for package in lock['packages']:
    archive = packages / package['name']
    package_evidence.append(download(package['url'], archive, package['sha256']))
    # Extract only the explicitly pinned regular files, never package scriptlets.
    for filename in package['files']:
        if filename not in lock['file_sha256']:
            raise SystemExit(f'unpinned extracted file: {filename}')
    subprocess.run(['bsdtar', '-xf', str(archive), '-C', str(root),
                    *('./' + name for name in package['files'])], check=True)

file_evidence = {}
upstream_evidence = {}
for filename, expected in lock['file_sha256'].items():
    path = root / filename
    if not path.is_file() or path.is_symlink() or digest(path) != expected:
        raise SystemExit(f'extracted tooling file failed verification: {filename}')
    file_evidence[filename] = expected
    if filename.startswith('usr/share/nitro_enclaves/blobs/'):
        name = path.name
        # Record the separate AWS Git distribution. Some RPM-built blobs differ
        # from the Git tag; never substitute them in an exact production rebuild.
        url = (f'https://raw.githubusercontent.com/aws/aws-nitro-enclaves-cli/'
               f'{lock["aws_source_commit"]}/blobs/aarch64/{name}')
        upstream_evidence[name] = download(url, upstream / name,
                                          lock['github_tag_blob_sha256'][name])
        upstream_evidence[name]['matches_rpm'] = (
            upstream_evidence[name]['sha256'] == expected)

environment = {
    'NITRO_CLI_BLOBS': str(root / 'usr/share/nitro_enclaves/blobs'),
    'NITRO_CLI_ARTIFACTS': str(out / 'artifacts'),
    'NITRO_CLI_LOGS_PATH': str(out / 'logs'),
}
for variable in ('NITRO_CLI_ARTIFACTS', 'NITRO_CLI_LOGS_PATH'):
    Path(environment[variable]).mkdir()
bin_dir = root / 'usr/bin'
environment_text = ''.join(f'export {key}={shlex.quote(value)}\n'
                           for key, value in environment.items())
environment_text += f'export PATH={shlex.quote(str(bin_dir))}:"$PATH"\n'
with (out / 'environment.sh').open('x') as target:
    target.write(environment_text)

runtime = {'executed': False}
if not verify_only:
    child_env = dict(os.environ, **environment)
    version = subprocess.check_output([str(bin_dir / 'nitro-cli'), '--version'],
                                     env=child_env, text=True).strip()
    if version != lock['version']:
        raise SystemExit(f'unexpected Nitro version: {version}')
    runtime = {'executed': True, 'version': version,
               'dynamic_libraries': subprocess.check_output(
                   ['ldd', str(bin_dir / 'nitro-cli')], text=True)}

evidence = {'schema': 1, 'tooling_lock_sha256': digest(lock_path),
            'aws_source_commit': lock['aws_source_commit'],
            'packages': package_evidence, 'files': file_evidence,
            'aws_upstream_blobs': upstream_evidence, 'runtime': runtime,
            'trust': 'AWS HTTPS repositories and hash-pinned AWS binaries; not a bootstrap source rebuild'}
with (out / 'tooling-evidence.json').open('x') as target:
    json.dump(evidence, target, indent=2)
    target.write('\n')
print(f'Verified AWS Nitro tooling. Environment: {out / "environment.sh"}')
PY
