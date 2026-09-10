# Tagged paste rollout — 2026-09-10

Production `19a53a50c3b340a192ef28955789ad083eb7bc69` runs non-debug on 14 Graviton5
cores, 8 GiB, 84 groups × 3,647,344 hashes. Generation uses nice 19. Two host cores
remain online. It restarted warm-up when replacing the previous image. Fresh
public Nitro evidence at 09:56:48 UTC verifies Mullvad up, paste protocol 1 and
102,400-byte maximum, while ordinary SDK verification rejects warming and relay
forwarding returns 503. Production warm-up, daily rollover and full-work recovery
have not yet completed.

## User-visible behavior

Tags are exact shared read/write passwords. `Relay.new_paste_tag()` creates a
random password; `write_paste(tag, content)` appends at most 100 KiB, and
`read_pastes(tag, after=..., limit=10)` reads pages. The tag password remains
inside authenticated inner TLS. Public artifacts contain an opaque tag ID for
grouping/counts. Contents use the existing daily epoch key with a separate
per-paste derivation; tag holders never receive the epoch key. Public recovery
needs the epoch key but no tag, and does not disclose the tag password.

Weak tags remain guessable offline using the public ID. The host can withhold
entries. Hash cursors are pagination, not a subscription: poll again from the
first page to discover new posts. See [design](../../docs/paste-design.md).

## Evidence

- [Production attestation](production/nitro-evidence.json) and [activation](production/activation.log).
- [Real Nitro diagnostic](diagnostic/nitro-evidence.json): Mullvad GET, archive recovery, 100 KiB pastes, pagination, wrong-tag isolation and tag-free epoch recovery passed. Diagnostic source `5dfd2e5` differs only in using eight iterations.
- [Public Cloudflare test](diagnostic/public-paste-proof.json): maximum-size write/read and anonymous artifact hash verification passed in 25.6 seconds.
- [Anonymous S3 readback](diagnostic/s3-readback.json): eight encrypted artifacts matched; mirror also keeps Hetzner copies. Stable parent paste directory survives release replacement.
- [GitHub run 34462293819](https://github.com/sophiawisdom/attested-relay/actions/runs/34462293819): two fresh ARM builds matched Docker image and PCR0/1/2; a separate job remeasured and signed both EIFs and the report. [Report](reproduction.json), [signature bundle](attestation-bundle.json), [local verification](ci-verification.log).
- Reviewed CI revision: `6a8dcd564c7a66cf554f7f86520aca528e0a06b6`. Later documentation commits do not replace this provenance pin.
- [Public enclave source](source-publication.json) and [SDK source](sdk-source-publication.json). The SDK-only follow-up `be4c866` streams 16 KiB plaintext TLS batches to avoid the enclave header timeout during large uploads. No enclave code or measurement changed for that fix.
- [PyPI 0.2.0a3](pypi-publication.json): client, macOS ARM64 solver and manylinux 2.34 ARM64/x86_64 solvers. All anonymous PyPI downloads matched tested wheel hashes.
- [Mac](mac-wheel-recovery.json), [Linux x86](linux-wheel-recovery.json) and [Linux ARM](arm-wheel-recovery.json) bundled binaries freshly solved the diagnostic puzzle and recovered a paste without its tag. Both Linux checks had networking disabled.
- Rust suite: 62 passed, one expensive full vector ignored; final crypto test passed. SDK/dev end-to-end: 71 passed, one external test skipped. Fresh Mac/Linux package suites: 78 passed each. SDK after transport fix: 66 passed. Tool tests: 24 passed plus six subtests; Worker: three passed. Logs are retained here.

## Operations and limits

Enclave: `production-paste-19a53a5`, ID `i-0de9795ee9d3ce090-enc1a08abed198619b`.
The parent keeps pastes in `/var/lib/attested-relay/pastes`; per-release archives
remain preserved. Cloudflare Worker version is `950e5905-cd1d-43f6-abd5-3fece56adec9`.
The fleet uses PyPI-equivalent 0.2.0a3 wheels, the new pin and nine workers;
previous venvs, source, artifacts, checkpoints and configurations are preserved.
One existing Mullvad device is reused.

On Graviton, `python3 /home/ec2-user/paste-20260910/control.py status` is read-only.
Its `sudo ... stop` and `sudo ... start` modes affect this named release only;
they preserve artifacts, but restarting begins a fresh warm-up. Those two control
modes were not exercised against the newly launched production process.

The calibrated RandomX delay is not a guaranteed seven-day wall clock. Daily
epoch timing, faster hardware, host availability and public archival durability
retain the limitations described in the threat model. Solver keys currently stay
local; automatic public key/plaintext publication remains unfinished. S3 is public
and the mirror role cannot delete, but Object Lock is absent and the AWS account
owner can remove objects. No third-provider replica is configured.
