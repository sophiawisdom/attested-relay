# Public reproduction evidence

Production source `30feebbeea8588fb1d1aa7b5ef40c9903bec0df5` includes required
Mullvad egress, native hardening, the optimized ARM JIT, 96-group generation, method commands, tagged paste storage and aggregate progress. Two fresh GitHub-hosted ARM builds reproduced
its deployed Docker image and PCR0/1/2. A separate job recomputed the EIF
measurements and signed both EIFs and the comparison report.

[Run 34584883837](https://github.com/sophiawisdom/attested-relay/actions/runs/34584883837)
passed on 2026-09-11. The downloaded report and an actual EIF passed local Sigstore
verification with the exact workflow/source revision and hosted-runner restriction.

**CI revision to review and pin:** `468d8e359fafb098ac5f8503de9a9d96fb559a98`.
[Public report](https://attested-relay-releases-370686332139-us-west-2.s3.us-west-2.amazonaws.com/releases/30feebbeea8588fb1d1aa7b5ef40c9903bec0df5/reproduction.json) and [portable signature bundle](https://attested-relay-releases-370686332139-us-west-2.s3.us-west-2.amazonaws.com/releases/30feebbeea8588fb1d1aa7b5ef40c9903bec0df5/attestation-bundle.json)
are available anonymously from S3. The actual EIFs are retained in the Actions
artifacts for 90 days.
Download the report and bundle into one directory, then run:

```sh
bash build/ci/verify.sh ./verified-reproduction sophiawisdom/attested-relay 468d8e359fafb098ac5f8503de9a9d96fb559a98
```

This pin remains the verification revision after later documentation changes.
The previous `a10323d` release remains available in
[run 34410069287](https://github.com/sophiawisdom/attested-relay/actions/runs/34410069287),
with CI revision `5d47234e2c7b0f0c77051c6fffe6bed363e69658`.

## What a client can verify without compiling

The evidence chain is:

1. An independently reviewed **exact CI repository commit** fixes the workflow,
   source archive SHA256, Dockerfile frontend and BuildKit image digests, and
   AWS Nitro tooling hashes. The application source commit and the CI repository
   commit are different identities and are both recorded.
2. GitHub's signed certificate identifies that workflow revision and hosted
   runner environment. The Sigstore bundle binds the downloaded report's bytes.
3. The reviewed workflow binds those bytes to the two freshly built EIFs and
   their independently recomputed measurements. An operator's supplied PCR JSON
   cannot satisfy the check without matching the built EIF measurements.
4. The client independently verifies a **fresh** AWS Nitro attestation, including
   the nonce, exact resulting PCR0, hardware/readiness policy and actual inner-TLS
   peer's public key, before sending its request.

Download the `verified-reproduction` artifact (report and portable Sigstore bundle)
from the successful run or the public S3 downloads linked above. The two `build-*`
Actions artifacts also contain their actual EIFs and diagnostics. Actions artifacts
have a 90-day retention period; the S3 report and bundle have no Actions expiry.
The bundle can be mirrored to any host without trusting that host's assertions.

With GitHub CLI and Python installed, verification requires no application build:

```sh
bash build/ci/verify.sh ./verified-reproduction OWNER/REPO REVIEWED_CI_COMMIT
```

The repository and full 40-character CI commit must come from the verifier's
independently accepted policy, not the same untrusted download being verified.
The command verifies the supplied Sigstore bundle and pins the signer workflow,
signer commit, source-repository commit, and GitHub-hosted runner restriction.
`--source-digest` refers to the CI repository commit; the application archive
SHA256 is fixed by that reviewed revision and included in the signed report.
Do not replace these checks with a green badge or just `--repo OWNER/REPO`.

`verify.sh` prints the resulting PCR0. It does not perform the subsequent live
Nitro/TLS handshake. A literal fetch-only client unable to execute cryptographic
verification needs a trusted verifier to do these checks; reading JSON alone
does not establish them.

## Reproduction scope

The source archive is fetched over public HTTPS and checked against a fixed SHA256
before extraction. Its Dockerfile and application files remain unchanged. The
Dockerfile's mutable frontend tag is overridden with its fixed digest using the
supported `BUILDKIT_SYNTAX` argument. BuildKit is also fixed by image digest;
the runner's Docker/Buildx versions are recorded. The Rust image is digest-pinned,
Debian packages use the source's snapshot date, and Cargo uses its lockfile.

The expected result is equality of PCR0/1/2 and Docker image IDs. The complete
EIF SHA256 can differ because of unmeasured metadata. Both actual hashes are
reported and attested; no claim of byte-identical EIF files is made.

AWS is trusted. The [Nitro tooling notes](NITRO-TOOLING.md) explain which AWS
packaged binaries are used and the differences from AWS's Git release. This
reproduces application measurements using fixed AWS bootstrap binaries; it is
not a source rebuild of AWS's kernel, compiler or Nitro toolchain.

The two runs are independent executions at **one provider**, GitHub. GitHub
provenance authenticates the workflow and artifact bytes; it does not establish
that the workflow or application is harmless. Reviewing and pinning the exact
workflow is essential: the repository owner could otherwise change it to sign
invented claims. Another organization maintaining a reviewed builder would add
an independent trust decision. Runtime isolation still depends on AWS/Nitro,
and reproducible builds do not rule out bugs, side channels or malicious source.

## Public repository staging

The public CI repository should contain only this reviewed `build/ci` directory,
`.github/workflows/reproduce-enclave.yml`, the threat model and a short root README.
Initialize it in a fresh directory; do not push the local working repository's
history. Frozen application source remains publicly available at the hash-pinned
URL in `release.json`. This keeps the CI provenance revision explicit without
rewriting the original measured application's source identity.

Local checks:

```sh
python3 -m unittest discover -s build/ci -p 'test_*.py' -v
bash -n build/ci/build.sh build/ci/install-nitro.sh build/ci/verify.sh
```

References: [GitHub hosted runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners),
[artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations),
[verification policy and workflow-controlled claims](https://cli.github.com/manual/gh_attestation_verify).
