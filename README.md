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

Status: workflow prepared and locally checked; see actual Actions results for
whether a public reproduction has completed. Do not treat this README as a
successful-build claim. A verifier must pin a reviewed CI revision, verify its
Sigstore bundle, then verify a fresh AWS Nitro attestation bound to the actual
TLS connection and matching enclave measurement.
