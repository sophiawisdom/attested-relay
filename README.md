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
- [Complete frozen application source](https://attested-relay-releases-370686332139-us-west-2.s3.us-west-2.amazonaws.com/releases/a10323dede4413fbf295916b8ad12e3dbad7514e/attested-relay-a10323dede4413fbf295916b8ad12e3dbad7514e.tar.gz)
- [Operator build and Nitro evidence manifest](https://attested-relay-releases-370686332139-us-west-2.s3.us-west-2.amazonaws.com/releases/a10323dede4413fbf295916b8ad12e3dbad7514e/manifest.json)

Application source commit: `a10323dede4413fbf295916b8ad12e3dbad7514e`.
The CI repository has its own separate commit identity. The threat model's
relative measurement/review links refer to files in the application archive.

Status: **independent reproduction passed** on 2026-09-09. Both GitHub-hosted
ARM builds reproduced production's Docker image and PCR0/1/2. A separate job
remeasured both EIFs and signed the report and actual artifacts. Local verification
accepted the authentic evidence and rejected an altered report and wrong workflow
revision.

- [Successful build and signing run](https://github.com/sophiawisdom/attested-relay/actions/runs/34410069287)
- [Public evidence downloads](https://github.com/sophiawisdom/attested-relay/releases/tag/ci-a10323d-34410069287)
- [Recorded measurements and verification](measurements/github-actions-a10323d-20260909/)
- **CI revision to review and pin:** `5d47234e2c7b0f0c77051c6fffe6bed363e69658`

Download `reproduction.json` and `attestation-bundle.json` into a directory, then:

```sh
bash build/ci/verify.sh ./verified-reproduction sophiawisdom/attested-relay 5d47234e2c7b0f0c77051c6fffe6bed363e69658
```

The pin identifies the workflow revision that performed the build, even after
later documentation changes on main. It must be independently reviewed and
accepted. Verification needs GitHub CLI and Python, but no local application
build. Next verify a fresh AWS Nitro attestation and actual inner TLS peer using
the resulting PCR0. Build provenance does not establish current relay readiness
or prove that the source is harmless. Full EIF bytes differ in unmeasured metadata;
their measured contents match. Both jobs ran at one provider, GitHub.
