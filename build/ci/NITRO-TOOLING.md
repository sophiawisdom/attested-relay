# Pinned AWS Nitro tooling

`install-nitro.sh` obtains Nitro CLI 1.5.0 and its ARM64 bootstrap blobs directly
from Amazon Linux's public HTTPS RPM repository. It checks the complete RPM
SHA-256 hashes and each extracted file against `nitro-tooling.lock.json`.
The resulting CLI and bootstrap bytes match the installed files used to build
production commit `a10323dede4413fbf295916b8ad12e3dbad7514e`.

This uses AWS-distributed binary tooling under the explicit assumption that AWS
is trusted. It does not establish reproducibility of AWS's own CLI, kernel,
bootstrap process, NSM driver, or LinuxKit from their source code. No binary
copied from the service operator's machine is used as a build input.

The installer also downloads the bootstrap files from AWS's public GitHub
commit `2950b3699d81ad304df2458915688a552734833d` (the `v1.5.0` tag), verifies
their separately pinned hashes, and records the comparison. The kernel Image,
kernel configuration, and command line match the RPM distribution. **The init,
LinuxKit, and NSM driver files differ between these two AWS distributions.**
The installer deliberately uses the exact RPM versions for production PCR
reproduction. A shared version label is not evidence of identical bytes.

On an Ubuntu 24.04 ARM64 runner, install `libarchive-tools` for `bsdtar`, then:

```sh
bash build/ci/install-nitro.sh "$RUNNER_TEMP/nitro-tooling"
source "$RUNNER_TEMP/nitro-tooling/environment.sh"
nitro-cli --version
```

The target must not exist. The installer preserves downloaded packages and all
evidence, including failed attempts. It runs no RPM scriptlets and installs no
system services or kernel module. It redirects Nitro's blobs, artifacts and
logs into the fresh target and exposes its CLI through `PATH`. The CLI uses the
runner's system OpenSSL 3, glibc, libgcc and zlib; the recorded `ldd` output makes
that runtime dependency explicit. Building an EIF does not require launching an
enclave or giving this tooling access to `/dev/nitro_enclaves`.

`tooling-evidence.json` records the lock digest, public download URLs, package
and file hashes, comparisons between the two AWS distributions, and runtime
version/dependencies. `--verify-only` performs download/extraction/hash checks
on another platform without attempting to execute the ARM64 Linux binary; it
does not validate runtime compatibility or build an EIF.

Relevant AWS sources:

- [Nitro CLI v1.5.0 source](https://github.com/aws/aws-nitro-enclaves-cli/tree/2950b3699d81ad304df2458915688a552734833d)
- [Supported blob and artifact environment variables](https://github.com/aws/aws-nitro-enclaves-cli/blob/2950b3699d81ad304df2458915688a552734833d/src/lib.rs)
- [Supported log directory environment variable](https://github.com/aws/aws-nitro-enclaves-cli/blob/2950b3699d81ad304df2458915688a552734833d/src/common/logger.rs)
- [AWS build-enclave command](https://docs.aws.amazon.com/enclaves/latest/user/cmd-nitro-build-enclave.html)
