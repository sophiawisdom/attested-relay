# Attested relay: independent build evidence

This repository runs public GitHub-hosted reproductions of the measured attested
relay enclave. It contains the build verifier and pinned inputs; the complete
application source is available as the hash-pinned public archive below.

The service aims to keep request/response plaintext private from its operator
until a public time-lock puzzle is solved. AWS is trusted. Reproduction provides
source-to-measurement evidence; it is not proof that the source has no bugs.

- [Workflow and verification instructions](build/ci/README.md)
- [Public workflow runs](https://github.com/sophiawisdom/attested-relay/actions/workflows/reproduce-enclave.yml)
- [Explicit threat model](threatmodel.md)
- [Pinned application source and expected measurements](build/ci/release.json)
- [Complete frozen application source](https://attested-relay-releases-370686332139-us-west-2.s3.us-west-2.amazonaws.com/releases/19a53a50c3b340a192ef28955789ad083eb7bc69/attested-relay-19a53a50c3b340a192ef28955789ad083eb7bc69.tar.gz)

Application source commit: `19a53a50c3b340a192ef28955789ad083eb7bc69`.
The CI repository has its own separate commit identity. The threat model's
review links refer to files in the application archive; current deployment evidence
is also recorded in this repository.

Status: **independent reproduction passed** on 2026-09-10. Both GitHub-hosted
ARM builds reproduced production's Docker image and PCR0/1/2. A separate job
remeasured both EIFs and signed the report and actual artifacts. Local verification
accepted the report and actual EIF with the exact workflow revision pinned.

- [Successful build and signing run](https://github.com/sophiawisdom/attested-relay/actions/runs/34462293819)
- [Public signed report](https://attested-relay-releases-370686332139-us-west-2.s3.us-west-2.amazonaws.com/releases/19a53a50c3b340a192ef28955789ad083eb7bc69/reproduction.json) and [signature bundle](https://attested-relay-releases-370686332139-us-west-2.s3.us-west-2.amazonaws.com/releases/19a53a50c3b340a192ef28955789ad083eb7bc69/attestation-bundle.json)
- [Recorded measurements and verification](measurements/paste-20260910/)
- **CI revision to review and pin:** `6a8dcd564c7a66cf554f7f86520aca528e0a06b6`

Download `reproduction.json` and `attestation-bundle.json` into a directory, then:

```sh
bash build/ci/verify.sh ./verified-reproduction sophiawisdom/attested-relay 6a8dcd564c7a66cf554f7f86520aca528e0a06b6
```

The pin identifies the workflow revision that performed the build, even after
later documentation changes on main. It must be independently reviewed and
accepted. Verification needs GitHub CLI and Python, but no local application
build. Next verify a fresh AWS Nitro attestation and actual inner TLS peer using
the resulting PCR0. Build provenance does not establish current relay readiness
or prove that the source is harmless. Full EIF bytes differ in unmeasured metadata;
their measured contents match. Both jobs ran at one provider, GitHub.

Production `19a53a5` runs on 14 Graviton5 cores with 84 groups, nice 19 generation
and one Mullvad device. The new tagged paste API uses the same daily epoch keys.
Opaque tag IDs are public; the tag password stays private and provides immediate
read/write access. Public puzzle recovery unlocks contents without the password.
[Paste design](docs/paste-design.md) and [rollout evidence](measurements/paste-20260910/README.md).

A real short-work Nitro test passed relay traffic, 100 KiB paste write/read,
tag isolation, pagination and public epoch recovery. The same-size paste passed
through [relay.sparrowsystems.co](https://relay.sparrowsystems.co), and eight artifacts
passed anonymous S3 hash verification. PyPI 0.2.0a3 is published and deployed to
the fleet. The client-only streaming fix is in source `be4c866`; enclave and native
solver source remains the measured `19a53a5` release. The published wheel hashes
and both source archives are recorded in the rollout evidence.

Fresh public Nitro/TLS verification confirms the production pin and Mullvad up,
while it correctly rejects requests during warm-up. Full-duration generation,
rollover and recovery remain unverified. The RandomX work is not a guaranteed
seven-day wall clock. Automatic public key/plaintext publication, S3 Object Lock
and a third-provider replica remain unfinished.
