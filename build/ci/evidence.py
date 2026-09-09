#!/usr/bin/env python3
"""Fail closed on PCR mismatches and bind the actual built EIF bytes to evidence."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

CI = Path(__file__).resolve().parent


def sha(path):
    with path.open("rb") as source:
        state = hashlib.sha256()
        for block in iter(lambda: source.read(1024 * 1024), b""):
            state.update(block)
    return state.hexdigest()


def load(path):
    return json.loads(path.read_text())


def pcrs(description):
    return {key: description["Measurements"][key] for key in ("PCR0", "PCR1", "PCR2")}


def check(description, release):
    measured = pcrs(description)
    if measured != release["pcrs"]:
        raise ValueError(f"built PCRs differ from pinned production: {measured}")
    return measured


def write(path, value):
    with path.open("x") as target:
        json.dump(value, target, indent=2, sort_keys=True)
        target.write("\n")


def build(directory, copy, release):
    measurements = check(load(directory / "description.json"), release)
    check(load(directory / "build-pcrs.json"), release)
    image = load(directory / "docker-inspect.json")[0]["Id"]
    if image != release["docker_image_id"]:
        raise ValueError(f"Docker image differs from production: {image}")
    write(directory / "build.json", {
        "schema": "attested-relay-ci-build-v1", "copy": int(copy),
        "source_commit": release["source_commit"], "source_sha256": release["source_sha256"],
        "pcrs": measurements, "docker_image_id": image,
        "eif_sha256": sha(directory / "attested-relay.eif"),
        "ci_commit": os.environ.get("GITHUB_SHA"),
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "runner_environment": os.environ.get("RUNNER_ENVIRONMENT"),
        "build_inputs": release,
    })


def compare(inputs, output, release):
    output.mkdir(parents=True, exist_ok=False)
    builds = []
    for copy in (1, 2):
        directory = inputs / f"build-{copy}"
        record = load(directory / "build.json")
        for field, expected in (
            ("copy", copy), ("source_commit", release["source_commit"]),
            ("source_sha256", release["source_sha256"]),
            ("docker_image_id", release["docker_image_id"]), ("pcrs", release["pcrs"]),
            ("ci_commit", os.environ["GITHUB_SHA"]),
            ("run_id", os.environ["GITHUB_RUN_ID"]),
            ("run_attempt", os.environ["GITHUB_RUN_ATTEMPT"]),
            ("runner_environment", "github-hosted"), ("build_inputs", release),
        ):
            if record.get(field) != expected:
                raise ValueError(f"build {copy}: wrong {field}")
        eif = directory / "attested-relay.eif"
        if sha(eif) != record["eif_sha256"]:
            raise ValueError("EIF artifact digest mismatch")
        # Recompute measurements in this fresh verification job, never trusting
        # only the build job's JSON or running application code on this host.
        description = json.loads(subprocess.check_output([
            "nitro-cli", "describe-eif", "--eif-path", str(eif)
        ], text=True))
        check(description, release)
        write(output / f"verified-eif-{copy}.json", description)
        builds.append(record)
    write(output / "reproduction.json", {
        "schema": "attested-relay-ci-reproduction-v1", "release": release,
        "ci_repository": os.environ["GITHUB_REPOSITORY"],
        "ci_commit": os.environ["GITHUB_SHA"],
        "run_id": os.environ["GITHUB_RUN_ID"],
        "run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
        "workflow_ref": os.environ["GITHUB_WORKFLOW_REF"],
        "pcrs_reproduced": True, "docker_image_reproduced": True,
        "full_eif_bytes_equal": builds[0]["eif_sha256"] == builds[1]["eif_sha256"],
        "scope": "Two GitHub-hosted executions; same provider. PCRs and Docker image must match production. EIF metadata can differ.",
        "builds": builds,
    })


if __name__ == "__main__":
    release = load(CI / "release.json")
    if sys.argv[1] == "build":
        build(Path(sys.argv[2]), sys.argv[3], release)
    elif sys.argv[1] == "compare":
        compare(Path(sys.argv[2]), Path(sys.argv[3]), release)
    else:
        raise SystemExit("expected build or compare")
