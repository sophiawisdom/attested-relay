# Commands, progress and 24-core production — 2026-09-11

Production source: `30feebbeea8588fb1d1aa7b5ef40c9903bec0df5`.
CI verification revision: `468d8e359fafb098ac5f8503de9a9d96fb559a98`.
[Successful reproduction](https://github.com/sophiawisdom/attested-relay/actions/runs/34584883837).

## Deployed configuration

The existing EC2 parent was stopped, resized to c9g.8xlarge (32 physical ARM
cores, 64 GiB), and restarted with its disk preserved. Production reserves
CPUs 1–24 and 8 GiB. Parent services have CPUs 0 and 25–31; the old puzzle solver
continues on CPU 31 at nice 19. One existing Mullvad device is reused.

The new puzzle has 96 groups × 4,843,750 iterations = **465,000,000 hashes**.
Generation runs 24 workers at nice 19. Only generation is parallel: public
recovery must unlock each group before starting the next. Old published work is
unchanged. Production launched around 09:40 UTC and is still warming.

PCR0:
```
23d68ee2a199e9044c9a317fbbff82e480a95641bf589f44feb886243390def2dd5996a1cb78b5da2ba13af447ad419d
```

[Launch](production-launch.json), [fresh Nitro verification](production-verification.json),
[progress observation](progress-observation.json). The fresh verification bound
non-debug measurement, nonce and TLS peer, authenticated c9g.8xlarge and work
policy, and confirmed Mullvad up. The ordinary SDK rejects warming; forwarding
returned 503. Stored attestations are historical evidence, not a live challenge.

## Commands and tested behavior

The inner command API supports `send_request` with a method argument,
`write_pastebin` and `read_pastebin_tag`. Outer transport remains HTTPS GET.
Request bodies and pastes are limited to 100 KiB. See [protocol](../../protocol.md).

- [Python tests](python-tests.log): 72 passed, one external test skipped.
- [Rust tests](rust-tests.log): native 6 passed/one ignored; enclave 29 passed.
- Short-work **non-debug Nitro** on the same 24-core allocation passed a
  102,400-byte POST through Mullvad with a dummy Authorization header, paste
  write/read, pagination, tag isolation, and recovery without knowing the tag.
  The diagnostic source `2cf4a17` differs from production only in setting eight
  iterations per group. Its 768-hash solve validates mechanics, not elapsed delay.
- Independent native wheel recovery on macOS ARM, Linux ARM and Linux x86
  recovered the same POST audit plaintext: SHA256
  `329033b7ae3001df7a25bd08b4ea5780c4172e40efb1265a70b2056a03422ae2`.
  ARM recovery ran with networking disabled. Request method, supplied headers,
  100 KiB body and response were recovered.
- Public Cloudflare GET transport passed a separate 75,776-byte POST and paste
  round trip. The two public artifacts passed anonymous hash checks and S3
  version retention checks. The bucket default remains **30-day COMPLIANCE**.

Evidence: [Nitro diagnostic](diagnostic-verification.json),
[public commands](public-command-proof.json), [S3 checks](s3-proof.json),
[Mac wheel](mac-wheel-proof.json), [ARM wheel](arm-wheel-proof.json),
[x86 wheel](x86-wheel-proof.json).

## Reproduction and packages

Two independent GitHub-hosted ARM builds reproduced the Docker image and
PCR0/1/2. Full EIF bytes differ in unmeasured metadata. The signed report and an
actual downloaded EIF passed local verification with the exact CI/workflow pin
and hosted-runner restriction. See [signed report](reproduction.json),
[signature bundle](attestation-bundle.json), [EIF verification](eif-verification.json),
and [verification instructions](../../build/ci/README.md).

The complete frozen source and signed evidence are anonymously downloadable;
[source publication proof](progress-source-publication.json) and
[evidence publication proof](evidence-publication.json) record URLs and hashes.
Version **0.2.0a4** of both PyPI distributions is published. All four wheels were
downloaded anonymously and compared to the tested local wheels:
[package hashes and URLs](pypi-proof.json).

## Progress dashboard and solving

[Live dashboard](https://relay-key-production.sophia-wisdom1999.chatgpt.site)
(owner access) polls the public
[`/v1/key-production`](https://relay.sparrowsystems.co/v1/key-production) feed
about every ten seconds. It shows generation phase, hash/group counters, worker
count, throughput, ETA, readiness and Mullvad status. It marks stale data and
labels host telemetry as unauthenticated. No chain state or request data is
reported. [Deployment receipt](dashboard-deployment.json).

The new Hetzner `attested-relay-solvers-commands` follower is active and polls for
new puzzles every 30 seconds, with up to eight workers at nice 19. It has a
separate state directory from the old follower; old recovery continues. The new
full-work puzzle has not been published, so its solve cannot start yet.

A separate [production acceptance checker](../../deploy/check-command-production.py)
is actively waiting for fresh verified readiness. It will send disposable
100 KiB POST/paste commands once, verify public S3 copies and the signed puzzle,
and require a live solver process with a written checkpoint (or a recovered key
matching its commitment). It never restarts generation or solvers and does not
retry application commands. [Observed checker state](acceptance-checker.json).

At 09:51 UTC, generation had completed 4.32M hashes. The latest 170-second
interval measured about 7,059 aggregate hashes/second, projecting about 18 hours
remaining if sustained. This is an early generation observation, not a solo
solver benchmark. [Follow-up progress observation](progress-followup.json).

## Remaining verification

Full-work generation completion, activation, daily rollover, and full-work
recovery of this new release are not yet observed. Diagnostic success does not
prove those outcomes or a hardware-independent seven-day minimum. Recovered keys
currently stay on solver hosts; automatic public key/plaintext publication is
unfinished. S3 mirroring is asynchronous and host-acknowledged; the enclave does
not verify S3 retention before returning a response. A third-provider replica
and independent per-record historical receipts remain outside this rollout.
