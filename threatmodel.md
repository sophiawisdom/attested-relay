# Attested relay v2 threat model

Status: consolidated review baseline, 2026-09-09. This document describes the
intended security properties, the deployed design, and its known gaps. It is
not a claim that all properties have been proved or that the service is ready.

Measured production source: `a10323dede4413fbf295916b8ad12e3dbad7514e`.
See [production measurements](https://attested-relay-releases-370686332139-us-west-2.s3.us-west-2.amazonaws.com/releases/a10323dede4413fbf295916b8ad12e3dbad7514e/manifest.json),
[requirement audit](reviews/current/REQUIREMENTS-AUDIT.md), and
[Astra review](reviews/current/astra-security-review.md).

## 1. Security objective

An independently verifying client should be able to send an HTTPS GET through
the relay without giving the EC2 account owner, parent operating system, or
relay front end the request URL, request plaintext, response plaintext, or
enclave secrets. The intended upstream necessarily receives its request and
knows its response.

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
  AWS API. Authenticating a server does not make its content trustworthy.
- RandomX and the serial wrapping construction impose the assumed work. No
  proven VDF property, hardware-independent lower bound, or seven-day theorem
  is assumed to have been demonstrated.

Application code, parsers, cryptographic-library integration, native RandomX,
the kernel/bootstrap, dependencies, and the build chain are review targets.
Pinning and reproducible measurements do not prove that this software lacks
bugs or that a compromised compiler cannot produce malicious code.

## 3. Assets

- Request URLs, query parameters, response bodies, and captured audit plaintext.
- Enclave TLS and service-signing private keys.
- Active/future epoch keys and unreleased puzzle seeds or intermediate results
  that could bypass the intended serial work.
- The client's binding between the accepted code, actual TLS peer, hardware
  policy, and response.
- Surviving encrypted records, puzzles, attestation evidence, and trusted
  receipts needed for later recovery and provenance.

## 4. Adversaries and capabilities

Adversaries may collude; we do not require the following actors to be independent
for confidentiality or authentication:

| Actor | Capabilities considered |
|---|---|
| EC2 owner/root and parent host | Control parent processes, vsock/network proxies, credential replies and storage acknowledgements; observe traffic; replace, reorder, replay, truncate or withhold bytes; launch other images; kill/restart enclaves; delete host-held artifacts. |
| Cloudflare/relay front end and network | Control outer HTTPS termination, URL handling, caching and routing; inspect outer ciphertext and metadata; replay, alter or suppress transport operations. |
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
that every upstream interaction survives in the archive. A GET-only interface
does not guarantee that every target treats GET as free of side effects.

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

- Parent/front-end observers can see IP addresses, timing, sizes and connection
  behavior. The parent can see outbound SNI when ECH is unavailable or falls
  back; the resolver sees DNS questions. This is not an anonymity system or a
  guarantee that destination hostnames remain hidden.
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

- Production `a10323d` is running and warming. Real short-work Nitro requests,
  independent offline recovery, and reproducible PCRs passed. Full-duration
  production generation, rollover and key recovery remain unverified.
- Two independent GitHub-hosted ARM builds reproduced the production Docker
  image and PCR0/1/2. A separate hosted job recomputed the EIF measurements and
  signed the results. [Evidence and verification](build/ci/README.md) require
  accepting an exact reviewed CI revision, trusting GitHub's execution/provenance,
  and subsequently verifying a fresh AWS Nitro/TLS binding. This adds independent
  source-to-measurement evidence; it does not prove source safety or live readiness.
- Measured generation projects about 25.14 hours, exceeding the 24-hour serving
  epoch and causing fail-closed gaps if that estimate holds. It is a calibration
  estimate, not an observed complete production run.
- AWS and Hetzner artifact copies and the nine-worker solver fleet are operating.
  A third provider and the public Cloudflare transport still require deployment
  and live validation. The user has reported renewing Cloudflare login; that
  authorization/session has not yet been revalidated after the report.
- The S3 uploader lacks delete permissions, but Object Lock is not enabled.
  Enclave-authenticated S3 storage/retention verification is not implemented.
  The user has not selected a retention duration. Do not describe current
  uploads as undeletable or independently storage-confirmed before response.
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
