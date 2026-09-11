# Agent services protocol

The public endpoint is `https://relay.sparrowsystems.co`. Outer HTTPS GET
requests transport an inner TLS 1.3 connection to the Nitro enclave. Command
names, destination URLs, headers, request bodies and tag passwords belong inside
that inner TLS connection, never in plaintext outer query parameters.

Before sending application data, verify a fresh AWS Nitro attestation against an
independently accepted exact PCR0, bind its public key to the actual inner TLS
peer, and verify the measured hardware, readiness and puzzle work policy. AWS
is trusted. Code measurement is not a proof that the program is free of bugs.

## Commands

All commands use inner HTTP POST with `Content-Type: application/json`. Unknown
fields are rejected. Outer transport remains GET-only. Release `30feebb` supports:

| Inner path | JSON fields | Result |
| --- | --- | --- |
| `/v1/commands/send_request` | `url`, `method`, optional `headers` and `body_b64` | Destination status, headers and body plus archive references |
| `/v1/commands/write_pastebin` | `tag`, `content_b64` | Paste artifact ID, opaque tag ID and puzzle references |
| `/v1/commands/read_pastebin_tag` | `tag`, optional `after` and `limit` | Pastes for that tag and a pagination cursor |

`send_request` accepts GET, HEAD, POST, PUT, PATCH, DELETE and OPTIONS. Targets
must use HTTPS port 443 with a public destination; URL credentials and fragments
are rejected. Request headers are an array of `[name, value]` pairs, with at most
64 headers and 16 KiB combined name/value bytes. Duplicate headers and routing,
framing, connection and proxy overrides are rejected. Bodies use standard base64,
decode to at most 100 KiB, and must be empty for GET and HEAD. The complete JSON
command is limited to 180 KiB. No automatic redirects or application retries are
performed. A lost reply can mean the destination acted: use destination-supported
idempotency keys when retrying operations with side effects.

The command response has `status`, `headers` (pairs whose values are standard
base64 encoded raw header bytes), `body_b64`, `record`, `puzzle`, and `evidence`.
Inner HTTP 200 denotes a completed command envelope; `status` is the destination
status or a relay-generated 502/504 on upstream failure/timeout. Validation,
capacity, readiness or archival failures produce non-200 inner HTTP responses.
Response bodies are capped at 10 MiB. After fetching the destination response,
the enclave encrypts an audit record containing the request URL, method, supplied
headers, body and captured response. Parent persistence must acknowledge before
the response is returned. S3 mirroring is asynchronous.

Paste tags are exact UTF-8 passwords of 1–256 bytes. Use high-entropy shared tags:
the public opaque tag ID permits offline guessing. Paste content is limited to
100 KiB. Read pages have 1–10 entries; `after` is a returned artifact cursor.
Pagination is in artifact-hash order, so start from the beginning when polling
for new writes. The host can omit entries; signatures and authenticated
encryption protect returned contents. The tag name is not archived in plaintext.
Both commands reuse the relay's daily epoch keys and public recovery puzzle.

The existing `/v1/pastes`, `/v1/pastes/read` and GET `/f/https/<host>/<path>`
interfaces remain available. The old GET route follows up to five redirects;
`send_request` returns redirects to the caller instead.

## Python example

```python
from attested_relay import Relay

r = Relay("https://relay.sparrowsystems.co", expected_pcr0=REVIEWED_PCR0)
response = r.send_request("https://example.com/api", method="POST",
                          headers={"Content-Type": "application/json"},
                          body=b'{"message":"hello"}')
tag = r.new_paste_tag()
r.write_pastebin(tag, b"shared message")
pastes = r.read_pastebin_tag(tag)
```

## Outer transport

`GET /relay?reqid=...&seq=...&ack=...&payload=...&send=...` carries encoded inner
TLS bytes. `seq` and `ack` make retransmission of transport packets idempotent.
`send=false` buffers a batch; `send=true` flushes it and retrieves available TLS
response bytes. Follow the SDK's bounded TLS batching rather than buffering a
complete application request in the parent. Transport packet deduplication does
not make a newly submitted application command idempotent.

## Delayed archive recovery

The deployed configuration has 96 groups of 4,843,750 dependent RandomX hashes:
exactly 465,000,000 in total. Generation uses 24 enclave cores; public recovery
must unlock the groups sequentially. This targets roughly seven days at 770
hashes/second, starting at puzzle publication. Daily epoch reuse means later
requests have less delay; faster solvers shorten it further. Existing 7- and
84-group puzzles remain supported and unchanged.

Public S3 artifact versions have 30-day COMPLIANCE Object Lock retention. This
protects stored versions during retention, not permanent public access, future
bucket settings, or data that never reaches S3. Recovered keys currently remain
on solver hosts; automatic public key publication is separate unfinished work.

## Key-production status

`GET /v1/key-production` is a public, no-cache, CORS-enabled operational endpoint.
It reports `source: "parent_telemetry"`, `age_seconds`, `stale`, and a `production`
object (null before the first report). Production fields are `version`,
`generation`, `phase`, `completed_hashes`, `total_hashes`, `completed_groups`,
`groups`, `workers`, `elapsed_seconds`, `service_ready`, and `mullvad_up`.
Reports arrive about every ten seconds; a report older than 35 seconds is stale.
Counters restart for each generation. No chain state or application data is
included. The host can forge these values; clients still require fresh signed
attestation before sending commands. The dashboard polls this endpoint every
ten seconds and estimates completion from aggregate progress.
