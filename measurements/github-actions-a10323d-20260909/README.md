# Independent GitHub-hosted reproduction

[Run 34410069287](https://github.com/sophiawisdom/attested-relay/actions/runs/34410069287)
succeeded on 2026-09-09. Two fresh hosted ARM builds reproduced production source
a10323d's PCR0/1/2 and Docker image ID. A third hosted job recomputed measurements
from both EIF files and signed the report and actual EIF bytes. Complete EIF
hashes differ in unmeasured metadata; measured contents match production.

CI revision: `5d47234e2c7b0f0c77051c6fffe6bed363e69658`.
Application revision: `a10323dede4413fbf295916b8ad12e3dbad7514e`.

The report and portable Sigstore bundle are original downloaded bytes. Local
verification pinned repository, workflow path and exact revision, rejected
self-hosted signing, and verified public Rekor evidence. Altering the report or
requiring another workflow revision failed; the first actual EIF's signature
also verified. See local-verification.json for observed test outcomes.

[Client verification instructions](../../build/ci/README.md) describe the separate
live AWS Nitro/TLS check. This evidence does not establish service readiness or
absence of software bugs. It relies on reviewed workflow code, GitHub-hosted
execution/provenance, and AWS-distributed bootstrap binaries. Two hosted jobs
are two executions under one provider, not two providers.
