# Local study launcher

This client serves the existing collector through a loopback-only HTTP listener. Current Chrome/Edge treat loopback origins as potentially trustworthy, enabling recording APIs without installing the study root into the OS/browser. The upstream remains HTTPS with hostname/expiry/chain verification against only the checksum-pinned study CA. No trust checks are disabled.

This is an alternative client, not a new publicly trusted website certificate. It requires one local launcher download. It does not alter the production gateway, account roles, SSID rules, approved addresses or recording destinations. The server still sees the participant computer's campus source address.

## Design

- Bind to `127.0.0.1`; accept only the exact `iitk-study.localhost:PORT` Host.
- Launch through a random per-process bootstrap URL, then require an HttpOnly, host-only, SameSite=Strict local cookie. Do not log request paths, passwords, cookies or bodies.
- Reject external Origin/cross-site requests and methods other than GET/POST. Only after that check translate the local Origin to the configured HTTPS origin expected by the existing gateway.
- Keep upstream login cookies in an in-memory jar. Strip server cookies from browser responses, forwarding only the jar's cookies to the fixed server. No browser cookie attributes are weakened.
- Drop client-supplied forwarding/IP headers. The upstream network allowlist continues to check the real TCP peer address; no proxy-header bypass is added.
- Stream uploads/downloads through the standard Go reverse proxy. Enforce 300 MiB upload and 64 KiB ordinary request limits and two simultaneous uploads locally. Server-side limits still apply independently.
- Keep passwords and upstream login cookies in memory only. A private per-port local cache file holds the random bootstrap token for repeat launching. Browser IndexedDB stores recording chunks and account-scoped text/memory/assignment drafts; preserve the default origin, port and browser profile for recovery.
- Inject only a same-origin external client script into dashboard/login/admin HTML, retaining the upstream CSP and TLS checks. A local EventSource connection tracks live tabs; fallback heartbeats cover reconnects. Last-tab close has a ten-second grace period for navigation; stale heartbeats expire after three minutes. This stops only the local launcher, never the simulator or its files.
- An authenticated reopen reserves the current process against automatic shutdown. Concurrent starts and the port-release boundary retry for up to twelve seconds without changing the browser origin or killing an unverified process.
- Reopening explicitly clears the local login after in-flight proxy requests finish. Normal refresh/navigation retains login. Browser recordings checkpoint their WebM chunks using strict IndexedDB transactions; a recovered prefix may omit the final seconds and is labeled as interrupted. Screen/microphone permission must be requested again after a crash.
- The updated collector template checkpoints pose, distance, action count and ordered goal progress after acknowledged navigation. Once deployed, new/restarted server workers restore the same owner's unfinished sample; finished samples and other users' folders are not resumed. An existing running worker is not restarted merely because its client tab closes.

The local machine is part of the trust boundary. This does not protect against malware with access to that machine, a modified launcher download, or compromised authenticated server content. It does not replace server-side upload validation, media parser isolation, account quotas, or verified campus network allocations. Binding the loopback listener prevents access from other computers, not from other processes on the same computer.

## Build and test

From Task_5, run `python3 -B campus_collector/build_study_launcher.py --go /absolute/path/to/go` using a locally installed official Go compiler. Only standard-library Go modules are used. The build copies the already prepared **public** study CA to `rootCA.crt` for embedding, verifies its checksum, tests the proxy and produces Windows/Linux AMD64 ZIPs and a macOS app containing native ARM64 and AMD64 binaries. Use `--target macos` to build only the Mac package. No CA/server private key is embedded or needed by the build.

Prepared public CA files, build caches, binaries and ZIPs remain excluded from source publication. A fresh checkout needs the owner-supplied public study CA before `go test` or `go build` can compile the embed directive. If the study CA rotates, the owner must review/update the expected checksum and redistribute the launcher. A server leaf certificate renewed under the same CA and hostname does not need a launcher rebuild.

`main_test.go` checks bootstrap/Origin/Host restrictions, real TLS hostname/expiry/CA rejection, login-cookie isolation, redirect rejection and streaming an upload before the sender has finished.

Windows/macOS binaries are cross-compiled; passing Linux/browser tests is not a target-device acceptance test. Pilot each package on its intended platform before broad distribution. The Mac package requires macOS 13+ with the current Go 1.27 compiler, is not Developer-ID signed or notarized, and may require per-app approval. It starts the selected binary through Terminal so the connection window remains visible. On a managed device, obtain normal administrator approval if application execution is restricted.

References: [Secure contexts](https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Secure_Contexts), [Go TLS](https://pkg.go.dev/crypto/tls), [Go ReverseProxy](https://pkg.go.dev/net/http/httputil#ReverseProxy).
