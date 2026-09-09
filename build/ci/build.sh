#!/usr/bin/env bash
# Run on a fresh native ARM Linux builder. No caches or deployment credentials.
set -euo pipefail
TASK_CI=$(cd "$(dirname "$0")" && pwd)
TASK_OUT=$1
TASK_COPY=$2
[[ $(uname -s) == Linux && $(uname -m) == aarch64 ]]
[[ "$TASK_COPY" == 1 || "$TASK_COPY" == 2 ]]
[[ ! -e "$TASK_OUT" ]]
mkdir -p "$TASK_OUT"
TASK_OUT=$(cd "$TASK_OUT" && pwd)
python3 "$TASK_CI/fetch-source.py" "$TASK_OUT/source"
TASK_SOURCE=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["source_commit"])' "$TASK_CI/release.json")
TASK_BUILDKIT=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["buildkit_image"])' "$TASK_CI/release.json")
TASK_FRONTEND=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["dockerfile_frontend"])' "$TASK_CI/release.json")
TASK_BUILDER="relay-ci-$TASK_COPY"
TASK_IMAGE="relay-ci:$TASK_SOURCE-$TASK_COPY"
docker buildx create --name "$TASK_BUILDER" --driver docker-container --driver-opt "image=$TASK_BUILDKIT"
docker buildx build --builder "$TASK_BUILDER" --no-cache --progress plain \
  --file "$TASK_OUT/source/build/Dockerfile.graviton5" --platform linux/arm64 \
  --build-arg "TLPROXY_GIT_SHA=$TASK_SOURCE" --build-arg SOURCE_DATE_EPOCH=0 \
  --build-arg "BUILDKIT_SYNTAX=$TASK_FRONTEND" --target enclave \
  --output "type=docker,name=$TASK_IMAGE,rewrite-timestamp=true,dest=$TASK_OUT/enclave-image.tar" \
  "$TASK_OUT/source"
docker load -i "$TASK_OUT/enclave-image.tar"
mkdir "$TASK_OUT/evidence"
docker image inspect "$TASK_IMAGE" > "$TASK_OUT/evidence/docker-inspect.json"
docker buildx version > "$TASK_OUT/evidence/buildx-version.txt"
docker version > "$TASK_OUT/evidence/docker-version.txt"
nitro-cli --version > "$TASK_OUT/evidence/nitro-version.txt"
nitro-cli build-enclave --docker-uri "$TASK_IMAGE" \
  --output-file "$TASK_OUT/evidence/attested-relay.eif" > "$TASK_OUT/evidence/build-pcrs.json"
nitro-cli describe-eif --eif-path "$TASK_OUT/evidence/attested-relay.eif" > "$TASK_OUT/evidence/description.json"
python3 "$TASK_CI/evidence.py" build "$TASK_OUT/evidence" "$TASK_COPY"
