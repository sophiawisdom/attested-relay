# Mullvad production deployment and evidence

Production source: `92bd47508d7ad48442c98148f6b4e09c6169ab5e`.
Non-debug Graviton5 launch: 2026-09-10 02:39:40 UTC, parent
`i-0de9795ee9d3ce090`, enclave `i-0de9795ee9d3ce090-enc1a0892f694bd5b0`.
The image includes the native AES-probe race, memory-erasure and page-permission
fixes. Previous releases and artifacts are preserved.

## What passed

- 28 enclave Rust tests, including required-VPN fail-closed routing, stale/dead
  handshake rejection, and idempotent one-device key rotation.
- 68 Python client/end-to-end tests passed, one skipped.
- A real development-mode Mullvad request returned `mullvad_exit_ip=true`.
  Instrumented parent gateways saw no direct CONNECT for the request or its DNS.
  Dropping the UDP tunnel produced HTTP 503 without direct fallback; restoring it
  recovered Mullvad forwarding on the same device.
- The actual non-debug Nitro diagnostic passed fresh AWS chain/COSE, nonce, PCR0,
  hardware verification and actual TLS-peer SPKI binding. An HTTPS GET of
  `https://am.i.mullvad.net/json` exited through Mullvad. Its authenticated public
  puzzle was solved offline, and audit decryption recovered the exact response.
  The diagnostic source `4254f789f2b4b70ea77eff6e52dedcc04f2160d2` differs only by
  setting eight iterations; it proves no seven-day delay.
- Production's signed policy reports 43,768,124 iterations, seven segments,
  verified Graviton5 hardware, `egress=mullvad-wireguard`, `mullvad_up=true`, and
  `state=warming`. Ordinary SDK verification rejects warming and forwarding is 503.
- One dedicated device, `deluxe gerbil`, ID
  `0a1054cd-3032-4bc0-9f79-d0888cf3bd9e`, is reused across boots and retries.
  The two unrelated pre-existing devices retained their IDs, names and public
  keys. The account has three devices in total; this relay uses one.
- The nine-worker solver's PCR0 pin was updated. Solver, mirror and origin tunnel
  services were active; AWS/Hetzner artifact storage and previous state were kept.

## Independent reproduction

[GitHub run 34430163444](https://github.com/sophiawisdom/attested-relay/actions/runs/34430163444)
passed both fresh hosted ARM builds and the separate measurement/signing job.
Both Docker image IDs and PCR0/1/2 equal the deployed build. Whole EIF bytes differ
in unmeasured metadata. The signed report and an actual downloaded EIF verified
locally against exact CI revision `a0fad3334b501c610c20dbe27137edaa607c90b3`.
See `github/` and [verification instructions](../../build/ci/README.md).

[Public release](https://github.com/sophiawisdom/attested-relay/releases/tag/ci-92bd475-34430163444)
contains both EIFs, the report, signature bundle and scanned frozen source.
The source archive has 557 files, no ancestor Git history, account number or
credential-pattern findings. Its SHA256 is recorded in `source-archive.json`.

Production PCR0:

```text
fd164375c25cef773742877caa93d56ec4e170022dc100a16216002fdb80fea8baeb3407ad401bd6bd655d9fdec5c438
```

## Limits and remaining readiness

The fresh production observation authenticates its signed timestamp and session;
readers must obtain their own fresh Nitro/TLS verification. Full-duration warm-up,
rollover and production key recovery remain pending. The prior calibration estimates
about 25 hours of generation, so 24-hour rollover can have fail-closed gaps; the
new image has not completed a full-duration calibration. The restart began a new
warm-up. Public Cloudflare transport and stronger storage retention remain separate
unfinished deployment work.

The conservative 180-second handshake-age gate renews idle tunnels, observed during
the production warm-up. This can briefly report unavailable while reconnecting;
it neither creates a device nor enables direct upstream fallback. Bootstrap AWS
and Mullvad API traffic may go direct. Request/DNS traffic requires WireGuard;
Mullvad and DNS resolvers still see destination metadata. No anonymity or exact
seven-day lower-bound claim is made.

Raw private test state, account files and offline key/checkpoint files are kept
outside this evidence directory. The diagnostic request contains only public data.
