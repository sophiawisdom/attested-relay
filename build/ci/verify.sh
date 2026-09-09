#!/usr/bin/env bash
# Verify downloaded evidence without compiling the application or running it.
# The expected repository/revision must come from an independently reviewed pin.
set -euo pipefail
[[ $# == 3 ]] || { echo 'usage: verify.sh EVIDENCE_DIRECTORY OWNER/REPO REVIEWED_CI_COMMIT' >&2; exit 1; }
TASK_EVIDENCE=$1
TASK_REPOSITORY=$2
TASK_REVISION=$3
[[ "$TASK_REPOSITORY" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]
[[ "$TASK_REVISION" =~ ^[a-f0-9]{40}$ ]]
gh attestation verify "$TASK_EVIDENCE/reproduction.json" \
  --bundle "$TASK_EVIDENCE/attestation-bundle.json" \
  --repo "$TASK_REPOSITORY" \
  --signer-workflow "$TASK_REPOSITORY/.github/workflows/reproduce-enclave.yml" \
  --signer-digest "$TASK_REVISION" --source-digest "$TASK_REVISION" \
  --deny-self-hosted-runners
python3 - "$TASK_EVIDENCE/reproduction.json" "$TASK_REPOSITORY" "$TASK_REVISION" <<'PY'
import json, sys
report = json.load(open(sys.argv[1]))
if report['schema'] != 'attested-relay-ci-reproduction-v1':
    raise SystemExit('unknown evidence format')
if report['ci_repository'] != sys.argv[2] or report['ci_commit'] != sys.argv[3]:
    raise SystemExit('unexpected evidence repository/revision')
if report['pcrs_reproduced'] is not True or report['docker_image_reproduced'] is not True:
    raise SystemExit('reproduction did not succeed')
print('Verified CI evidence for source', report['release']['source_commit'])
print('PCR0:', report['release']['pcrs']['PCR0'])
print('Use this PCR0 for an independent, fresh Nitro/TLS verification; this report is not a live attestation.')
PY
