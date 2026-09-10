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
- [Complete frozen application source](https://attested-relay-releases-370686332139-us-west-2.s3.us-west-2.amazonaws.com/releases/92bd47508d7ad48442c98148f6b4e09c6169ab5e/attested-relay-92bd47508d7ad48442c98148f6b4e09c6169ab5e.tar.gz)

Application source commit: `92bd47508d7ad48442c98148f6b4e09c6169ab5e`.
The CI repository has its own separate commit identity. The threat model's
review links refer to files in the application archive; current deployment evidence
is also recorded in this repository.

Status: **independent reproduction passed** on 2026-09-10. Both GitHub-hosted
ARM builds reproduced production's Docker image and PCR0/1/2. A separate job
remeasured both EIFs and signed the report and actual artifacts. Local verification
accepted the report and actual EIF with the exact workflow revision pinned.

- [Successful build and signing run](https://github.com/sophiawisdom/attested-relay/actions/runs/34430163444)
- [Public evidence downloads](https://github.com/sophiawisdom/attested-relay/releases/tag/ci-92bd475-34430163444)
- [Recorded measurements and verification](measurements/graviton5-mullvad-92bd475-20260910/)
- **CI revision to review and pin:** `a0fad3334b501c610c20dbe27137edaa607c90b3`

Download `reproduction.json` and `attestation-bundle.json` into a directory, then:

```sh
bash build/ci/verify.sh ./verified-reproduction sophiawisdom/attested-relay a0fad3334b501c610c20dbe27137edaa607c90b3
```

The pin identifies the workflow revision that performed the build, even after
later documentation changes on main. It must be independently reviewed and
accepted. Verification needs GitHub CLI and Python, but no local application
build. Next verify a fresh AWS Nitro attestation and actual inner TLS peer using
the resulting PCR0. Build provenance does not establish current relay readiness
or prove that the source is harmless. Full EIF bytes differ in unmeasured metadata;
their measured contents match. Both jobs ran at one provider, GitHub.

Production uses one Mullvad WireGuard device, with its private key generated inside
Nitro. The real short-work Nitro request and offline audit-recovery tests passed.
Production remains warming; the public Cloudflare route is not yet deployed.
