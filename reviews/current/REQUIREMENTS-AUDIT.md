# Requirement audit — 2026-09-09

Source: the final detailed design and subsequent corrections in the shared
conversation `6aa158ab-3844-83e8-b1a2-c4712dfe7367`. Later corrections replace raw
NLB/TAP ingress with GET-carried inner TLS, remove ACME and capability billing,
and acknowledge that a fetch-only tool cannot independently execute TLS/COSE.
The project owner explicitly confirmed that AWS is trusted; earlier exploration
of a malicious-AWS scenario is outside the agreed threat model.

This is a completion audit, not a claim that the work is finished.

| Requirement | Current authoritative evidence | Status / remaining work |
|---|---|---|
| Rust enclave on c9g.4xlarge, 12 CPUs/24 GiB, separate parent | Real nondebug diagnostic and production run evidence under measurements/graviton5-* | Replacement a10323d diagnostic verified (only iterations changed to8); actual production source reproduced and running with fresh signed warming evidence |
| Parent/Cloudflare cannot impersonate the authenticated inner TLS endpoint or read plaintext | Actual Nitro SDK challenge, PCR pin and peer SPKI verification; synthetic-chain/MITM tests | Inner transport verified; live Cloudflare hop pending authentication |
| GET reqid buffering/send/poll preserves ordered TLS bytes with bounded memory | Rust host tests; installed client suite; live SSH-carried GET transport | Verified on host; Cloudflare retry/cache/URL-limit validation still pending |
| Exact published source/PCRs, reproducible measured image | Current a10323d source and Nitro evidence publicly published; two clean operator-hosted builds and two GitHub-hosted ARM builds match PCR0/1/2 and Docker image ID; measurements/github-actions-a10323d-20260909 records separate measurement/signing job and verified Sigstore bundle | Public CI run34410069287 passed. Exact reviewed workflow revision must be pinned. Measured contents reproduce; complete EIF metadata differs. Source safety and live Nitro identity remain separate checks |
| TLS and signing secrets stay in enclave | Measured TLS and signing code; NSM peer-key binding | Direct NSM boot/secret generation passed real Nitro diagnostic; no claim of formal memory-safety proof |
| Current Graviton5 hardware evidence, not stale IID | Actual enclave MIDR, fresh local NSM PCR4, live authenticated AWS DescribeInstances | Verified on nondebug diagnostic and production image |
| NSM-generated epoch key and private puzzle seeds | Direct fallible NSM API and privileged bootstrap reseed in a10323d; successful-boot.log and authenticated diagnostic evidence | Verified inside real Nitro diagnostic and the deployed production image |
| GET-only HTTPS443 relay, redirects, 30s/10MiB bounds, no cookies/auth, SSRF denial | Unit/integration tests, actual example.com request, trailers/large/failed-response capture | Updated source passes four integrations and actual Nitro GET/recovery; hostile parent-line and DoH body bounds added and tested |
| Capture and encrypted durable publication before returning plaintext | Real host ACK, disconnect/timeout/partial-body integration tests | Host durability verified; malicious host can lie about storage. S3-confirmed retention is a separate unimplemented stronger guarantee |
| Canonical CBOR audit plaintext and authenticated context | New v2_proxy patch emits canonical CBOR v3 with software_version; historic image emits JSON v2 | Canonical encoder/integrations and actual Nitro recovery passed; independent network-isolated Hetzner recovery matched exact response bytes; old data stays supported |
| Seven independent native RandomX v2.0.1 segments, shared per-puzzle dataset, serial chained unwrap | Pinned native source/hash checks, full/light known-answer tests on ARM/x86, native recoveries | Verified implementation and interoperability; not a proven VDF or ASIC lower bound |
| Calibrated approximately seven solver days / one parallel generator day | 50k-sample Graviton5 solo and seven-worker measurements | M43768124 projects25.14h generation; full production duration unobserved; fail-closed daily gaps expected if estimate holds |
| Private future puzzles, publish-before-use, expiry erasure, late-generation refusal | Watchdog, delayed ACK, rotation and disconnect lease tests | Local lifecycle verified; actual production first completion/rollover unobserved |
| History recoverable after enclave/AWS disappearance | Actual public Nitro artifacts solved/decrypted offline, including network-disabled ARM container and independent Hetzner wheel | Short-work recovery verified; production-duration key recovery pending actual puzzle |
| Independent continuous checkpointed solver fleet | Enabled Hetzner services, persistent restricted direct SSH tunnel, fresh production pin verification; nine-worker benchmark and systemd health evidence | Nine workers upgraded to published0.2.0a2 and freshly verified a10323d production pin; active awaiting first puzzle. Measured 15.44% capacity margin and estimated recovery7.82–8.69days; sustained production solving unobserved |
| Three independent providers retain ciphertext/puzzles/attestations | Actual diagnostic S3 and Hetzner upload/readback, hash receipts, continuous mirror services | Two providers verified; Cloudflare R2 third replica pending authentication/provisioning |
| Public archives and independently verified historical signatures | Content-addressed host endpoints, archive verifier, real Nitro archive test | Protocol verified; publicly reachable HTTPS origin pending Cloudflare |
| Python packages and CLIs published on PyPI | 0.2.0a1 pureclient plus macOS ARM/Linuxx86/LinuxARM native wheels, PyPI hashes, installed tests | 0.2.0a2 high-level API published with all three native platform wheels; installed recovery and all public downloaded hashes verified |
| Independent open-source model scrutiny through Pi/OpenRouter | DeepSeek, Kimi, Qwen review outputs and checked responses | DeepSeek reviewed NSM/CBOR; separate requested Astra review found two memory-bound gaps, both fixed and independently inspected before a10323d freeze |
| Open unauthenticated service with no billing/capability machinery | v2 routing and admission configuration | Implemented; bounded admission is not guaranteed availability under abuse |
| Literal web_fetch-only independent cryptographic proof | Final source conversation explicitly acknowledges missing crypto primitive | Impossible under that restricted tool model; no plaintext fallback or false verification claim |

The S3 deletion-protection question was answered separately: the scoped uploader
has no delete or bucket-management permissions, verified by IAM simulation and
real conditional upload/readback. Object Lock compliance retention is not enabled
and no retention duration has been selected. Stronger immutable pre-response S3
storage would require enclave-authenticated upload/retention verification.
