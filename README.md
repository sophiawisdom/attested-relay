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
- [Complete frozen application source](https://attested-relay-releases-370686332139-us-west-2.s3.us-west-2.amazonaws.com/releases/30feebbeea8588fb1d1aa7b5ef40c9903bec0df5/attested-relay-30feebbeea8588fb1d1aa7b5ef40c9903bec0df5.tar.gz)

Application source commit: `30feebbeea8588fb1d1aa7b5ef40c9903bec0df5`.
The CI repository has its own separate commit identity. The threat model's
review links refer to files in the application archive; current deployment evidence
is also recorded in this repository.

Status: **independent reproduction passed** on 2026-09-11. Both GitHub-hosted
ARM builds reproduced production's Docker image and PCR0/1/2. A separate job
remeasured both EIFs and signed the report and actual artifacts. Local verification
accepted the report and actual EIF with the exact workflow revision pinned.

- [Successful build and signing run](https://github.com/sophiawisdom/attested-relay/actions/runs/34584883837)
- [Public signed report](https://attested-relay-releases-370686332139-us-west-2.s3.us-west-2.amazonaws.com/releases/30feebbeea8588fb1d1aa7b5ef40c9903bec0df5/reproduction.json) and [signature bundle](https://attested-relay-releases-370686332139-us-west-2.s3.us-west-2.amazonaws.com/releases/30feebbeea8588fb1d1aa7b5ef40c9903bec0df5/attestation-bundle.json)
- [Recorded measurements and verification](measurements/commands-20260911/)
- **CI revision to review and pin:** `468d8e359fafb098ac5f8503de9a9d96fb559a98`

Download `reproduction.json` and `attestation-bundle.json` into a directory, then:

```sh
bash build/ci/verify.sh ./verified-reproduction sophiawisdom/attested-relay 468d8e359fafb098ac5f8503de9a9d96fb559a98
```

The pin identifies the workflow revision that performed the build, even after
later documentation changes on main. It must be independently reviewed and
accepted. Verification needs GitHub CLI and Python, but no local application
build. Next verify a fresh AWS Nitro attestation and actual inner TLS peer using
the resulting PCR0. Build provenance does not establish current relay readiness
or prove that the source is harmless. Full EIF bytes differ in unmeasured metadata;
their measured contents match. Both jobs ran at one provider, GitHub.

Production `30feebb` runs on 24 reserved Graviton5 cores of a 32-core parent.
Its 96 groups require **465,000,000 sequential RandomX hashes** for recovery.
Generation runs at nice 19. One Mullvad device is reused.

The new [command protocol](protocol.md) supports GET transport carrying upstream
GET, HEAD, POST, PUT, PATCH, DELETE or OPTIONS, plus password-tagged paste
write/read commands. Request bodies and individual pastes are capped at 100 KiB.
Tags remain private; opaque tag IDs are public. Paste recovery uses the same
public epoch puzzle and does not require knowing the password.

Real short-work Nitro tests passed a 100 KiB POST through Mullvad, paste write/read,
tag isolation, pagination, and exact offline audit recovery on Mac ARM and Linux
ARM/x86. Public GET transport and anonymously retrieved S3 artifacts passed checks.
Both PyPI packages are published as **0.2.0a4**.

[Key-production dashboard](https://relay-key-production.sophia-wisdom1999.chatgpt.site)
(owner access) shows the public aggregate progress feed. These values are host
telemetry, not signed attestation. Fresh Nitro verification confirms the current
production image and Mullvad up while it warms; commands are rejected until
publication of the first puzzle. A new solver follower waits for that puzzle;
the older published epoch continues solving.

Full-work generation, rollover and new-epoch recovery remain unverified. The
work factor is not a guaranteed seven-day wall clock. Stored public artifact
versions have **30-day COMPLIANCE Object Lock**. S3 replication is asynchronous;
the enclave checks a host persistence acknowledgement. Automatic public
key/plaintext publication and a third-provider replica remain unfinished.
