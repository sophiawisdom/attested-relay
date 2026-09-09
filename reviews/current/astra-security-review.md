# Independent Astra security review — 2026-09-09

Reviewed the working tree based on `04d67264ce55d140d42518390fe5b5a855eddf5a`,
including the uncommitted NSM entropy, canonical CBOR and high-level Puzzle API
changes. The running image remains the separately measured `474083e` build;
this review does not establish that the replacement source is deployed.

Scope: v2 enclave initialization, NSM randomness/time, epoch activation/erasure,
RandomX generation/wrapping, GET relay, outbound TLS and hardware verification,
live Python TLS/COSE validation, archive binding, and the new Puzzle wrapper.
Read REQUIREMENTS-AUDIT.md, NSM-RNG-AUDIT.md and the final shared design/transport
corrections. AWS/Nitro/PKI are trusted; parent and Cloudflare are adversarial.
No credentials or private deployment state were read. No network/cloud actions
or source changes were made. Tests used local synthetic certificate fixtures.

## Outcome

No new high/critical confidentiality or authentication bypass was established.
Two concrete availability defects violated the intended memory bounds. Both
were sent to the parent agent and corrected during this review. I independently
inspected the final source fixes: M1 now bounds tunnel/config lines before
allocation grows, and M2 limits DoH bytes before collection. The corrections are
local source changes; they have not been measured/deployed. Findings below
retain the original locations and triggers for review history.

## Findings

### M1: parent tunnel acknowledgement allocates without a byte limit — fixed in source

Location: `crates/enclave/src/transport.rs:91–104`, especially `read_line` at 98.

Every outbound TCP connection first reads the untrusted parent's textual tunnel
acknowledgement. A parent responding with a long ASCII stream without a newline
causes `read_line(&mut String)` to keep growing the buffer. The 30-second timeout
limits elapsed time, not allocation. This path runs before outbound TLS, and is
reachable during hardware initialization as well as normal DNS/upstream traffic.
The request concurrency cap does not bound bytes allocated by one such stream.

Impact: allocation exhaustion can terminate the enclave or cancel in-flight
capture work. It does not reveal a key or authenticate a fake upstream. The
parent can already terminate its enclave, so this is a bounded-resource defect,
not an additional availability guarantee against the account owner.

Recommended correction: a bounded line reader, for example a 64-byte maximum
for the tunnel acknowledgement, that requires a terminated accepted OK line and
retains bytes buffered after the newline for TLS. Reject an unterminated line
at the bound. Test a long no-newline stream, EOF without newline, and an OK line
coalesced with trailing TLS bytes using a bounded in-memory duplex stream.

The same primitive at `transport.rs:134` reads the legacy host-config line
without a pre-allocation cap; its 64-KiB check runs only after `read_line` returns.
That legacy path is not used by the reviewed v2 bootstrap, but a shared bounded
helper should also enforce its 64-KiB limit before allocation grows further.

### M2: authenticated DoH response body is unbounded — fixed in source

Location: `crates/enclave/src/dns.rs:194`, `resp.into_body().collect()`.

The enclave's first configured DoH provider is Cloudflare at 1.1.1.1. TLS proves
the provider's identity, not that its response is safely sized. Under the stated
malicious-Cloudflare model, that provider can return HTTP 200 with an arbitrarily
large chunked body. The implementation collects it completely before asking
the DNS parser to validate it. The query's timeout does not impose a byte cap.
A body exceeding 65,535 bytes is already a bounded trigger for this gap; no
memory-exhaustion test is needed to demonstrate the missing check.

Impact: a malicious/compromised resolver can exhaust enclave memory through DNS,
bypassing the relay's 10-MiB response limit. Ordinary relay clients cannot forge
the resolver's TLS certificate; controlling a queried domain is not by itself
shown to permit this attack. The scope expressly includes malicious Cloudflare.

Recommended correction: incrementally bound the decoded HTTP body to the DNS
wire-message maximum of 65,535 bytes before collection/parsing. A Content-Length
check alone is insufficient for chunked responses. Test the exact boundary,
one byte above it, and a chunked response that crosses it. Retain the total
query timeout as well.

## Verified boundaries and accepted limitations

- **New entropy path:** `v2_main.rs` opens the NSM attester and calls the fail-closed
  kernel reseed gate before installing the TLS provider or generating the TLS
  identity. The signing seed is obtained directly from NSM. `generate_with_rng`
  obtains all 16 entropy draws before RandomX work and has no fallback. The raw
  NSM response and borrowed/copy destinations are bounded and zeroizing;
  failed fills leave caller output zeroed. The fresh two-round kernel reseed
  requires real nondebug Nitro validation of the replacement image. Tests or
  successful hardware evidence from the old image cannot establish that fact.
- **Erasure:** future puzzles remain private until the old trusted deadline;
  activation is anchored before the first possible puzzle publication. Delayed
  storage acknowledgements cannot grant an already disclosed puzzle a new full
  lifetime. An independent monotonic watchdog releases the global expired-key
  reference, and admitted requests retain bounded capture/publication leases.
  Zeroizing wrappers do not prove removal of every compiler, allocator, native
  RandomX, cryptographic-library or kernel copy. No host-readable path to such
  residual copies was established under the trusted Nitro isolation model.
- **Live identity:** the Python client completes a real inner TLS handshake,
  checks a fresh 32-byte nonce, AWS-rooted COSE signature, nonzero pinned PCR0,
  current certificate validity and exact actual-peer SPKI before transmitting
  the requested upstream URL. Dev bypass requires explicit loopback options.
  Fresh verification creates a new session; ordinary requests reuse only the
  verified TLS connection. No plaintext fallback was found.
- **Hardware:** production initialization checks local V3 MIDRs, fresh local NSM
  PCR4, and a TLS-authenticated DescribeInstances response for the matching ID,
  exact c9g.4xlarge type, running state and enclave enablement. Host-supplied
  credential/instance strings do not by themselves establish hardware trust.
- **Record format:** canonical CBOR v3 includes software_version in authenticated
  ciphertext; epoch, sequence and signed-manifest ID are authenticated in AAD.
  Moving software_version inside the authenticated plaintext does not create
  an unauthenticated field. Historic JSON v2 remains a distinct old format.
- **Historical provenance after key release:** puzzle signatures remain bound to
  the Nitro-attested service key. Individual EncryptedRecord envelopes have no
  service signature (`crates/timelock/src/lib.rs:55–62,92–155`). Anyone holding
  the eventually public epoch key can encrypt an invented record under the real
  signed manifest and pass AEAD verification. A digest newly supplied by the
  malicious archive is not an independent trust anchor. Original-record
  provenance requires a previously trusted receipt/publication digest or a
  service signature over each record. This existing limitation is now stated
  in the Puzzle API README; do not describe AEAD decryption as proof of an
  authentic historical relay interaction. Archive completeness and release time
  are also not established by historical attestation alone.
- **Storage:** OK from the parent proves only that the parent acknowledged the
  bytes. It does not prove S3 retention or independent replication. The stronger
  enclave-authenticated immutable-storage guarantee is unimplemented and Object
  Lock is disabled. This is an explicit existing requirement gap, not a new
  bypass of an implemented storage-proof protocol.
- **Delay:** seven independent private seeds and serial authenticated unwraps
  enforce the intended dependency chain under the RandomX assumption. The
  measured parameter is not a seven-day lower bound against faster hardware.
  One-day epochs also mean the final records have roughly one day less delay
  than records at publication. Production-length solving and sustained rollover
  remain unobserved; the estimated 25.14-hour generation time implies fail-closed
  daily gaps when it exceeds the 24-hour epoch.
- **Puzzle API:** independent PCR0 and historical hardware/manifest verification
  are mandatory. Metadata is returned as copies. The parallel API review found
  and is correcting custom-output-directory and checkpoint/manifest hardlink
  issues; those findings are not duplicated as independent new defects here.

## Validation

Executed:

```text
PYTHONPATH=python/attested-relay/src /tmp/attested-relay-venv/bin/python -m pytest -q -p no:cacheprovider python/attested-relay/tests/test_verify.py python/attested-relay/tests/test_archive.py -k 'not fetch_historical_bundle_and_discover_via_real_host' --basetemp=/tmp/astra-security-pytest-20260909
46 passed, 1 deselected in 0.38s
```

This exercises synthetic-chain verification, nonce/PCR/TLS-key rejection,
invalid signed policy, historical certificate validity at signed time, unsigned
policy substitution, puzzle/bundle/content-address binding, native manifest
encoding, and small-order/noncanonical Ed25519 rejection. The deselected test
requires the local relay host integration fixture. No replacement-image Nitro
run or production-duration puzzle generation was performed in this review.
The memory-bound findings are source-established; no unbounded allocation or
live denial-of-service experiment was run.

## Correction review

Inspected the final transport diff: `bounded_parent_line` limits allocation
before extending the output, rejects a full unterminated line immediately,
retains buffered bytes after a newline, and `parent_ok` accepts only OK LF/CRLF.
The legacy config reader uses the same helper with a 64-KiB cap. Its tests cover
fragmented oversized streams that stay open, exact acknowledgement syntax,
coalesced TLS preservation and the exact config limit.

Inspected the final DNS diff: `Limited::new(body, 65535)` wraps the body before
`collect`. Tests cover multiple frames with no eventual EOF, the exact bound,
and one oversized frame. Both corrections address the findings without
changing the TLS authentication trust boundary. Implementing agents reported the following successful targeted executions:

```text
cargo test --locked -p tlproxy-enclave transport::tests -- --test-threads=1
4/4 v2 tests passed; 4/4 legacy tests passed.

cargo test -p tlproxy-enclave --bin attested-relay-enclave dns::tests --locked
2/2 DNS tests passed. Log: /tmp/relay-dns-bound-tests.log
```

The parent also reported 76 passing Python tests in 15.29 seconds after the
final API corrections. My independent execution remains the 46-test verifier/
archive run above. At report freeze, the parent was running broader workspace
Rust checks and rebuilt-binary end-to-end tests; those are not represented as
completed evidence here.
