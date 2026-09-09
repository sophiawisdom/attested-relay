#!/usr/bin/env python3
"""Fetch the fixed public release; never execute its host-side scripts."""
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import sys
import tarfile
import urllib.request


def extract(data, destination, release):
    if hashlib.sha256(data).hexdigest() != release["source_sha256"]:
        raise ValueError("source archive SHA256 mismatch")
    destination.mkdir(parents=True, exist_ok=False)
    prefix = "attested-relay-" + release["source_commit"]
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        for member in archive.getmembers():
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts or path.parts[0] != prefix:
                raise ValueError("noncanonical source path")
            target = destination.joinpath(*path.parts[1:])
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile() and member.size <= 8 * 1024 * 1024:
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as output:
                    output.write(archive.extractfile(member).read())
                target.chmod(member.mode & 0o755)
            else:
                raise ValueError("source links or special/oversize files are forbidden")


if __name__ == "__main__":
    release = json.loads(Path(__file__).with_name("release.json").read_text())
    with urllib.request.urlopen(release["source_url"], timeout=120) as response:
        data = response.read(8 * 1024 * 1024 + 1)
    extract(data, Path(sys.argv[1]), release)
    print("Verified source", release["source_commit"], release["source_sha256"])
