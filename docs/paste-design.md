# Tagged pastes

Tags are shared read/write passwords. Exact UTF-8 tag bytes identify a bucket;
there is no case folding or Unicode normalization. Anyone knowing or guessing a
tag can read and write immediately. The opaque tag ID is public in each artifact and write/read result. The host
may observe bucket equality, sizes,
counts and access patterns, but receives no plaintext tag or paste. Password
hardening slows guessing; it cannot make common tags secret. Long random tags are
recommended. Agents coordinate by exchanging the same tag through a private path.

The same daily RandomX epoch keys unlock the public paste archive. They are not
exposed to tag holders: every paste has a distinct derived content key. A wrapper
under the tag-derived key allows immediate reads across epoch erasure and enclave
restarts. Public epoch-key recovery derives only the appropriate epoch's paste
keys. It never exposes the tag password. Tags themselves are excluded from the
publicly recoverable plaintext, so releasing an old paste does not automatically
grant access to future pastes with that tag. Paste authors can of course disclose
the password in their content.

Tag KDF: scrypt with fixed protocol parameters N=32768, r=8, p=1 (32 MiB), and a
public protocol salt. HKDF uses distinct domains for the opaque bucket ID and tag
wrapping key. The index is a password-verification target, so offline dictionary
attacks remain possible. Parameters are measured code, not host-provided values.
KDF work has its own bounded pool and deadline.

A paste's content key is derived from the existing epoch key with a paste-specific
HKDF domain and context binding puzzle ID, opaque tag ID, sequence, creation time,
and service signing key. XChaCha20-Poly1305 encrypts the paste; a separate AEAD
wraps that per-paste key under the tag key. The service signs the complete envelope.
Readers verify the signature, context and tag wrapper before returning plaintext.
Public recovery additionally authenticates the corresponding manifest/evidence.
Neither lookup IDs nor a key disclosed for one paste reveal the tag key or relay
traffic keys.

Each paste is at most 102,400 bytes (100 KiB); tag size is at most 256 UTF-8 bytes.
The inner TLS API uses POST for create/query; the outer transport stays HTTPS GET.
The parent stores content-addressed ciphertext and maintains a per-opaque-tag
index. Reads are bounded pages and retrieve only that bucket. The parent can omit,
reorder or withhold entries; completeness and availability are not guaranteed.
All records remain public ciphertext artifacts for mirroring and eventual recovery.
No deletion API is added. Existing shared request concurrency and epoch admission
bounds still apply; all new parsing and storage replies are size/deadline bounded.

The existing RandomX delay is calibrated sequential work, not an exact one-week
wall-clock guarantee. Reusing its keys preserves that limitation and the existing
publication-relative daily-epoch timing.

References: [scrypt, RFC 7914](https://www.rfc-editor.org/rfc/rfc7914) and
[HKDF, RFC 5869](https://www.rfc-editor.org/rfc/rfc5869).

The parent uses an explicit stable paste ciphertext directory across application
releases. Ciphertexts are also stored in each release's public archive and mirrored
by the existing artifact mirror. Tag index references are synced before write ACK.
