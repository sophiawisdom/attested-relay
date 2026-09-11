# Attested relay v2 threat model

Status: deployment update, 2026-09-11. This document describes the
intended security properties, deployed design, and known gaps; it is not a
claim that all properties have been proved.

Measured production source: `30feebbeea8588fb1d1aa7b5ef40c9903bec0df5`.
It is running non-debug on 24 reserved Graviton5 cores of a 32-core c9g.8xlarge,
with Mullvad up and the first epoch warming. Its 96 serially wrapped groups
require exactly 465,000,000 hashes for recovery. Commands support upstream
methods and password-tagged pastes over the existing GET transport.
[Current rollout and test evidence](measurements/commands-20260911/README.md),
[protocol](protocol.md), [requirement audit](reviews/current/REQUIREMENTS-AUDIT.md),
and [earlier Astra review](reviews/current/astra-security-review.md).
Earlier reviews predate the new command and progress code.

## 1. Security objective

An independently verifying client should be able to send an HTTPS request through
the relay without giving the EC2 account owner, parent operating system, or
relay front end the request URL, request plaintext, response plaintext, or
enclave secrets. The intended upstream necessarily receives its request and
knows its response. Protection cannot extend to information that the client or
an intended plaintext recipient voluntarily gives to another party. In
particular, a destination colluding with the operator can disclose the complete
exchange immediately; AWS trust and RandomX strength do not prevent that.

Encrypted audit records are deliberately recoverable later through public
RandomX puzzles. Confidentiality is temporary and conditional on the assumed
cost of solving those puzzles. This is not permanent encrypted storage.

## 2. Trust assumptions

**AWS itself is trusted; the AWS account owner is not.** We rely on Nitro
isolation, the NSM's entropy and signed time, AWS's attestation PKI, the
hardware presented to the enclave, and the authenticated EC2 API's account of
the instance. A malicious AWS provider capable of falsifying those mechanisms
is outside the implemented protection.

Other assumptions:

- The client's execution environment and verification code are trustworthy,
  and its exact PCR0 pin comes from an independently trusted source. A PCR
  supplied by the server being verified is not a trust anchor.
- Standard cryptographic primitives remain secure, including TLS, signatures,
  hashes, HKDF, and the AEAD schemes used here.
- WebPKI correctly authenticates upstream HTTPS servers, DoH resolvers, and the
  AWS and Mullvad APIs. Authenticating a server does not make its content trustworthy.
- RandomX and the serial wrapping construction impose the assumed work. No
  proven VDF property, hardware-independent lower bound, or seven-day theorem
  is assumed to have been demonstrated.

Application code, parsers, cryptographic-library integration, native RandomX,
the kernel/bootstrap, dependencies, and the build chain are review targets.
Pinning and reproducible measurements do not prove that this software lacks
bugs or that a compromised compiler cannot produce malicious code.

## 3. Assets

- Request URLs, query parameters, methods, headers, bodies, response bodies,
  paste contents and tag passwords, and captured audit plaintext.
- Enclave TLS and service-signing private keys.
- Active/future epoch keys and unreleased puzzle seeds or intermediate results
  that could bypass the intended serial work.
- The client's binding between the accepted code, actual TLS peer, hardware
  policy, and response.
- Surviving encrypted records, puzzles, attestation evidence, and trusted
  receipts needed for later recovery and provenance.

## 4. Adversaries and capabilities

Adversaries may collude. The confidentiality objective covers information that
they cannot already obtain as intended plaintext recipients; it cannot prevent
recipient disclosure described in section 1. Malicious upstream inputs remain
in scope for exploitation of the enclave and disclosure of other users' data.

| Actor | Capabilities considered |
|---|---|
| EC2 owner/root and parent host | Control parent processes, vsock/network proxies, credential replies and storage acknowledgements; observe traffic; replace, reorder, replay, truncate or withhold bytes; launch other images; kill/restart enclaves; delete host-held artifacts. |
| Cloudflare/relay front end and network | Control outer HTTPS termination, URL handling, caching and routing; inspect outer ciphertext and metadata; replay, alter or suppress transport operations. |
| Mullvad VPN operator | Observe destination IPs, timing, sizes and unencrypted TLS metadata; drop, reorder or alter tunnel traffic. Upstream TLS remains authenticated inside the enclave. The account owner can revoke or replace the registered device key and deny service. |
| DNS resolver and upstream websites | Return hostile DNS/HTTP/TLS inputs and redirects, large or slow bodies, and misleading content; attempt SSRF and parser/resource attacks. Their authentic certificates do not grant trust in their responses. |
| Anonymous relay clients | Choose requests, establish concurrent sessions, disconnect at awkward points, and attempt denial of service or exploitation of enclave code. |
| Archive hosts and external solvers | Corrupt, omit, replay or replace artifacts and progress claims; withhold results; publish wrong keys; coordinate and share computed work; use faster hardware. |

A compromised client or its tool provider may already see that client's inputs
and outputs. The relay does not protect a user from software that handles their
plaintext before encryption or after decryption.

## 5. Trust boundaries and required invariants

### Client to enclave

Outer GET operations carry an inner TLS connection. Before transmitting an
upstream request, the client must verify the AWS-rooted COSE document, a fresh
nonce and timestamp, the exact nondebug PCR0, required hardware/work policy,
readiness, and the binding to the **actual TLS peer's SPKI on that connection**.
Relaying somebody else's valid attestation must not authenticate an attacker's
TLS endpoint. Historical evidence must not substitute for a fresh live check.

An upgrade requires explicit acceptance of a new measurement. There is no
automatic acceptance of whichever PCR the operator advertises as latest.
A literal fetch-only tool cannot independently execute this TLS/COSE protocol;
there is no verified plaintext fallback.

### Enclave to host, AWS and upstreams

Host-provided identities and credentials are untrusted inputs. Hardware
acceptance combines local CPU identity, fresh NSM PCR4 parent binding, and an
enclave-authenticated EC2 API response for the matching instance.

Upstream TLS verification happens inside the enclave. Resolved destinations
and redirects must remain within the public HTTPS/port-443 policy. Parent
responses, DNS/HTTP bodies, connection counts and operation lifetimes require
bounds before untrusted input can cause unbounded resource use.

Production upstream connections and their DNS-over-HTTPS lookups require an
in-enclave Mullvad WireGuard tunnel. Its private key comes from NSM and is never
accepted from or exported to the parent. One measured device ID is reused; each
boot rotates its public key, and retries never create or delete devices. A missing,
dead or stale tunnel blocks upstream traffic, including an accidental Direct mode.
Public bootstrap lookups, Mullvad registration and AWS hardware verification may
connect directly. Signed policy includes tunnel readiness and the egress mode.

### Entropy, epochs and disclosure

Production must successfully obtain NSM randomness and reseed the kernel before
TLS initialization. Signing keys, epoch keys and private puzzle material use
direct, fallible NSM randomness; failures must not silently select a weaker path.

Future puzzles remain private. A key cannot serve traffic before its puzzle's
publication acknowledgement. Delayed acknowledgements cannot extend the lifetime
of an already disclosed puzzle. Expired epochs reject new work even when their
successor is late. Admitted requests retain bounded completion leases.

App-owned key buffers are zeroized on release where implemented. This is not
proof of erasing every compiler, allocator, library, kernel or hardware copy.
An independent native probe confirmed that register bytes retained after the VM
destructor can reconstruct a final segment output with one BLAKE2b operation.
No externally reachable memory-read primitive was found; obtaining the final
segment's residual state would nevertheless allow early epoch-key unwrapping.
See the [native review](reviews/current/astra-20260909-round2/native-entropy-and-memory.md).
Attestation also does not establish general resistance to microarchitectural
side channels. Concrete attacks available to an in-scope adversary must be
investigated, not dismissed merely because the code is measured.

### Response capture and storage

Before returning the upstream response, the enclave encrypts the audit record
and waits for the parent's persistence acknowledgement. This establishes the
ordering in the enclave; **a malicious parent's acknowledgement is not proof
of durable storage or replication**.

A host can also kill the enclave after an upstream has observed a request but
before capture finishes. Consequently, this is not an unconditional guarantee
that every upstream interaction survives in the archive. Both method commands and legacy GET requests can cause destination-side effects.

### Archived evidence and recovered records

Puzzle signatures are bound to the Nitro-attested service key. Archive checks
must bind the puzzle, signer, attestation, content-addressed files and required
PCR/hardware policy, while distinguishing historical identity from liveness.
Wrong recovered keys and modified ciphertext must fail their commitment/AEAD
checks.

**Individual record envelopes are not service-signed.** Once the epoch key is
public, anyone holding it can create another valid AEAD record. Proving an
original historical relay interaction therefore also requires a previously
trusted ciphertext digest/receipt or independent publication record. A fresh
digest supplied by a malicious archive does not solve this problem. Neither
AEAD nor a signed puzzle proves archive completeness.

## 6. Deliberate leakage and limits

- Parent/front-end observers can see client/VPN-peer IP addresses, timing, sizes
  and connection behavior. WireGuard hides client-selected destination IPs and
  upstream TLS handshakes from the parent, but Mullvad sees destination IPs and
  outbound SNI when ECH is unavailable or falls back. The DoH resolver sees DNS
  questions. Colluding observers and traffic analysis remain in scope as leakage;
  this is not an anonymity guarantee or a promise to hide all hostnames.
- Metadata can reveal content, not merely activity. Public record ciphertext
  exposes the exact serialized plaintext length plus the AEAD tag, allowing
  known candidates of different lengths to be distinguished without solving.
  Following a redirect can also expose response-derived information embedded
  in its destination hostname through DNS/SNI. No claim of hiding all facts
  about request or response contents is made.
- Puzzles, manifests, attestations and encrypted artifacts are public by design.
  Decrypted audit data is intended to become public after solving.
- Approximate delay starts at puzzle publication, not at each request. With a
  24-hour epoch, its last records have roughly one day less remaining delay
  than its first records. Faster hardware, improvements or shared progress can
  shorten recovery time.
- A malicious parent can always stop its enclave or refuse service. Admission
  limits mitigate resource abuse; they do not guarantee anonymous-service
  availability. Memory-bound defects still count as implementation defects.
- Recovery needs surviving ciphertext **and** the corresponding puzzle and
  evidence. No cryptography recovers files after every copy is destroyed.

## 7. Known gaps and deployment status

- Production `30feebb` includes the native hardening changes documented in
  [RandomX patch notes](vendor/randomx/PATCHED.md): a per-call AES probe, explicit
  native VM/JIT/temporary-state erasure, and fail-closed page-permission checks.
  [Regression evidence](reviews/current/native-fixes-20260910.md) covers ARM
  sanitizer checks and Linux deallocation/failure-injection tests. The previously
  reproduced shared AES-probe race is fixed in this deployed source. These checks
  do not prove erasure of every compiler, register or kernel copy.
- Production `30feebb` is running non-debug on Graviton5 with an authenticated
  signed policy reporting Mullvad up and epoch warming. An eight-iteration Nitro
  build differing only in work count passed fresh attestation, a real Mullvad-exit
  request and exact offline audit-record recovery. Real VPN loss/recovery and
  absence of direct fallback were exercised separately in development mode.
  Full-duration production generation, rollover and key recovery remain unverified.
- Two independent GitHub-hosted ARM builds reproduced the deployed `30feebb` Docker
  image and PCR0/1/2. A separate hosted job recomputed the EIF measurements and
  signed the results. [Evidence and verification](build/ci/README.md) require
  accepting an exact reviewed CI revision, trusting GitHub's execution/provenance,
  and subsequently verifying a fresh AWS Nitro/TLS binding. This adds independent
  source-to-measurement evidence; it does not prove source safety or live readiness.
  [Run 34584883837](https://github.com/sophiawisdom/attested-relay/actions/runs/34584883837)
  passed; its signed report and an actual EIF verified locally against CI revision
  `468d8e359fafb098ac5f8503de9a9d96fb559a98`. Full EIF bytes differ in unmeasured
  metadata; Docker image identity and PCR0/1/2 match.
- Generation schedules 96 groups over 24 workers at nice 19. Full-duration
  throughput remains unmeasured; if generation misses the 24-hour serving epoch,
  requests expire closed until the successor is ready.
- AWS and Hetzner artifact copies are operating. The old puzzle continues solving;
  a separate eight-worker follower waits for new production puzzles. A third
  provider remains pending. Cloudflare's Worker transports ciphertext through its
  VPC binding; the published 0.2.0a4 SDK includes the transport fixes.
- The archive's `artifacts/` prefix is publicly readable and discoverable over
  HTTPS. The current diagnostic POST and paste artifacts passed anonymous
  full-byte hash checks and retained-version checks. Full-work production has
  not yet published its first puzzle. [Current evidence](measurements/commands-20260911/README.md).
- The solver fleet saves recovered keys locally. Automatic public publication of
  recovered keys/decrypted records is not deployed; public users can independently
  solve downloaded puzzles. Automatic discovery/failover from S3 is also not wired
  into the fleet's current origin-based follower.
- The S3 archive uses 30-day Object Lock compliance retention by default, and
  existing public artifact versions are protected for 30 days from backfill.
  The uploader also lacks delete permissions. Protection applies to retained
  versions until their retention dates; administrators can still change future
  defaults or public access, and new versions/delete markers can hide retained
  versions from ordinary reads. Enclave-authenticated S3 storage/retention
  verification is not implemented: uploads are not independently
  storage-confirmed before response. See [Object Lock evidence](measurements/s3-object-lock-20260910/README.md).
- Per-record origin signatures or an equivalent durable independent receipt
  mechanism are not implemented. Post-release provenance has the limit above.

## 8. Instructions for subsequent security reviews

Use this model to identify violations, not to explain away bugs. Report the
attacker capability, reachable entry point, violated property, concrete trigger,
and evidence or reproducer. Distinguish current defects, unverified assumptions,
accepted disclosure, and proposed stronger guarantees. Review the actual pinned
source and relevant deployment state; do not infer runtime security from a PCR,
a green test suite, or another model's conclusion alone.

Disagreements with these assumptions—especially trust in AWS, approximate delay,
record provenance, and storage durability—must be raised explicitly before
claiming that the implementation satisfies a stronger threat model.


## Tagged pastes

Tags act as shared read/write passwords.
Anyone guessing a tag can use the same public API as other agents. Scrypt slows
online/offline guessing; low-entropy tag names do not satisfy unconditional name
or content secrecy. Long random tags provide the intended password security.
Opaque tag IDs are intentionally public, exposing grouping, counts and access
patterns. The host can omit, reorder or withhold results; no completeness claim
is made. All paste plaintext and tag passwords travel inside attested inner TLS.

Per-paste content keys are derived with a separate HKDF domain from the same
existing epoch keys; tag holders receive only individually wrapped paste keys,
not epoch keys or relay-traffic keys. Tag wrappers allow access after old epoch
keys are erased. Public epoch recovery unlocks only that epoch's paste contents;
it does not reveal tag passwords or automatically unlock later epochs. Authors
may disclose passwords in their own content. Signatures and AEAD bind paste
metadata, tag ID, puzzle identity and signer; public recovery authenticates the
signer through the corresponding independently attested manifest.

The 100 KiB paste limit, 256-byte tag limit, two KDF workers, ten-entry page limit,
shared request admission and a 30-second operation deadline bound resources.
The existing assumptions about computational delay, storage acknowledgements,
replicas, metadata leakage and imperfect memory erasure still apply.
[Detailed protocol and API design](docs/paste-design.md).

The short-work Nitro paste test, public Cloudflare 100 KiB round trip and
independent epoch-key recovery passed. Full-duration production behavior remains
unverified. [Paste rollout evidence](measurements/paste-20260910/README.md).

## Public generation telemetry

`GET /v1/key-production` exposes only aggregate generation counters: phase,
generation number, completed/total hashes and groups, worker count, elapsed
time, service readiness and Mullvad status. It includes no seeds, intermediate
chain values, epoch keys, tags or application request data. The host can forge
or withhold this telemetry; it must never authorize a client request or replace
fresh Nitro/TLS verification. The dashboard labels this distinction explicitly.

The command API has bounded bodies and headers and forbids routing/framing
header overrides. It performs no application retry or redirect following for
`send_request`; a missing reply does not prove that a destination operation had
no effect. The legacy GET route retains its bounded redirect behavior.
