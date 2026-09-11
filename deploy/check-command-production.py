#!/usr/bin/env python3
"""One-shot production acceptance check after full-work generation finishes.

Uses only disposable test content. Never restarts generation or a solver and
never retries an application command. Evidence files are created exclusively.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import time
import urllib.request

from attested_relay import Relay
from attested_relay.archive import verify_bundle
from attested_relay_timelock.follow import bundle_names

PCR0 = "23d68ee2a199e9044c9a317fbbff82e480a95641bf589f44feb886243390def2dd5996a1cb78b5da2ba13af447ad419d"
SOURCE = "30feebbeea8588fb1d1aa7b5ef40c9903bec0df5"
ENDPOINT = "https://relay.sparrowsystems.co"
ARCHIVE = "https://attested-relay-archive-370686332139-us-west-2.s3.us-west-2.amazonaws.com/artifacts/"


def save(directory, name, value):
    with (directory / name).open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def fetch(name, base=ENDPOINT + "/v1/artifacts/"):
    if not re.fullmatch(r"[0-9a-f]{64}\.(record|paste|puzzle|attestation|bundle)\.json", name):
        raise ValueError("invalid artifact name")
    request = urllib.request.Request(base + name, headers={"User-Agent": "attested-relay/2"})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read(32 * 1024 * 1024 + 1)
    if len(raw) > 32 * 1024 * 1024 or hashlib.sha256(raw).hexdigest() != name[:64]:
        raise ValueError("artifact hash or size mismatch")
    return raw


def solver_observation(state, identity, commitment):
    # A state file alone is insufficient: require a live native process and a
    # written checkpoint, or validate the completed key against the manifest.
    key = state / (identity + ".key")
    if key.exists():
        with key.open("rb") as stream:
            decoded = bytes.fromhex(stream.read(129).decode().strip())
        if len(decoded) != 32 or hashlib.sha256(decoded).hexdigest() != commitment:
            raise ValueError("recovered key commitment mismatch")
        return {"completed_key_verified": True}
    manifest = str(state / (identity + ".manifest.json")).encode()
    checkpoint = state / (identity + ".jsonl")
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            argv = (proc / "cmdline").read_bytes().split(b"\0")
            if b"solve" in argv and manifest in argv and checkpoint.stat().st_size > 0:
                return {"live_solver_pid": int(proc.name), "checkpoint_bytes": checkpoint.stat().st_size}
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--solver-state", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    # Do not accidentally replay POST or paste writes on a restarted checker.
    save(args.output, "started.json", {"at": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    deadline = time.monotonic() + 36 * 3600
    while True:
        relay = Relay(ENDPOINT, expected_pcr0=PCR0, timeout=60)
        try:
            verified = relay.verify()
            break
        except Exception as error:
            print("Waiting for verified production readiness:", type(error).__name__, flush=True)
        if time.monotonic() >= deadline:
            raise TimeoutError("production did not become verifiably ready within 36 hours")
        time.sleep(60)
    policy = verified["policy"]
    assert policy["software_version"] == "0.1.0+" + SOURCE
    assert policy["segments"] == 96 and policy["iterations"] == 4843750
    assert policy["instance_type"] == "c9g.8xlarge" and policy["mullvad_up"]
    save(args.output, "ready-attestation.json", verified)
    print("Fresh production attestation passed; testing public commands", flush=True)
    body = b"relay-production-acceptance\n".ljust(102400, b"P")
    response = relay.send_request("https://httpbingo.org/post", method="POST",
                                  headers={"Content-Type": "text/plain"}, body=body)
    assert response.status_code == 200 and response.json()["data"] == body.decode()
    headers = dict(response.headers)
    record = headers["x-attested-relay-record"]
    puzzle = headers["x-attested-relay-puzzle"]
    save(args.output, "post.json", {"passed": True, "bytes": len(body), "record": record, "puzzle": puzzle})
    tag = relay.new_paste_tag()
    paste = relay.write_pastebin(tag, body)
    page = relay.read_pastebin_tag(tag)
    assert any(item["id"] == paste["id"] and item["content"] == body for item in page["pastes"])
    assert not relay.read_pastebin_tag(tag + "wrong")["pastes"]
    assert paste["puzzle"] == puzzle
    save(args.output, "paste.json", {"passed": True, "bytes": len(body), "artifact": paste["id"]})
    deadline = time.monotonic() + 900
    bundle = None
    while bundle is None:
        for name in bundle_names(ENDPOINT):
            candidate = verify_bundle(name, fetch, expected_pcr0=PCR0)
            if candidate["puzzle_artifact"] == puzzle:
                bundle = candidate
                break
        if time.monotonic() >= deadline:
            raise TimeoutError("accepted request's public bundle was not discovered")
        if bundle is None:
            time.sleep(15)
    names = [record, paste["id"], puzzle, bundle["bundle_artifact"], bundle["attestation_artifact"]]
    pending = set(names)
    while pending:
        for name in list(pending):
            try:
                fetch(name, ARCHIVE)
                pending.remove(name)
            except Exception as error:
                print("Waiting for public archive:", name, type(error).__name__, flush=True)
        if pending:
            if time.monotonic() >= deadline:
                raise TimeoutError("public S3 artifact verification timed out")
            time.sleep(15)
    save(args.output, "s3.json", {"anonymous_hash_verified": names})
    identity = bundle["manifest_id"]
    while True:
        observation = solver_observation(args.solver_state, identity, bundle["manifest"]["puzzle"]["key_commitment"])
        if observation:
            save(args.output, "solver.json", {"manifest_id": identity, **observation})
            break
        if time.monotonic() >= deadline:
            raise TimeoutError("verified puzzle has no observed live checkpointing solver")
        time.sleep(15)
    save(args.output, "passed.json", {"passed": True, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                      "full_work": 465000000, "puzzle": puzzle})
    print("Production POST, paste, public archive and live solving passed", flush=True)


if __name__ == "__main__":
    main()
