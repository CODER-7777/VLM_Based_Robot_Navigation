# Review of the proposed SSID filtering and recording-upload configuration

This is a source/configuration review, not an independent security audit. No SSID restrictions, subnet expansion, Nginx installation or OS firewall changes were applied for this review.

## Network access

IP allowlists are useful. The existing HTTPS gateway checks the TCP peer address and ignores client-supplied forwarding headers. A reverse proxy or host firewall can enforce an approved allocation too. Binding controls which server interface listens; it does not identify a participant's Wi-Fi SSID.

The assertion that every IITK SSID always maps to a distinct, disjoint campus-wide client subnet has not been established. One laptop's two DHCP leases do not establish that mapping. Obtain an authoritative VLAN/source-range mapping from CC, including NAT/routing behavior, before claiming to distinguish `iitk` from `iitk-sec` or `iitk-sec(Highspeed-5GHz)`. If different SSIDs reach the application through the same source addresses, enforce the separation at the wireless controller/firewall instead. An ordinary web request does not report a trustworthy SSID.

Do not copy example ranges such as `172.20.0.0/16` into production. Do not broaden to all private networks. Current approved addresses must remain unchanged until the owner authorizes a verified change.

The example Nginx configuration listens on plain HTTP port 80. It does not solve trusted HTTPS, and non-loopback HTTP cannot support the collector's recording APIs. Introducing a proxy also requires preserving the correct Host/Origin and an explicitly trusted backend source arrangement; simply forwarding to the current gateway can trigger its source-IP denial.

## Certificate trust

`mkcert` creates a local CA. Other participants must trust that CA separately, so switching to it does not remove participant setup. It is intended for development, not a substitute for publicly trusted production certificates. Our custom launcher instead scopes the existing study CA to its own HTTPS client, leaving browser/OS root stores unchanged. Its browser UI runs on a loopback secure context; it does not create a publicly trusted hostname or make the campus server HTTP-accessible.

## Existing upload controls and remaining work

Source review confirms these existing controls:

- Authentication and contributor-owned session checks before uploads.
- Declared-size limits, ambiguous/chunked request rejection and a free-disk check at the gateway.
- Server-generated UUID staging names and numbered output paths, rather than uploaded filenames.
- Fixed voice/screen media types, per-contributor storage and authenticated download routes.
- FFmpeg invoked with an argument list instead of a shell; recordings are not executed as programs.

Additional defenses are still appropriate: validate permitted media containers/streams before queuing conversion; restrict FFmpeg input protocols and resource usage; add conversion timeouts/isolation; bound concurrent queued jobs and per-account storage; reserve space for in-flight uploads. Magic-byte checks alone do not validate a whole media file or eliminate parser vulnerabilities. The existing processing path does not yet implement all these defenses.

Prefer per-account/concurrency controls to a coarse per-IP upload cooldown, because several legitimate participants may share an address. Preserve the browser's source clip and recovery flow when rejecting a recording. The launcher's two-upload cap is a client safeguard, not server-side protection against custom clients.

Renaming a script to `.mp4` does not itself execute it, but untrusted media must still be processed with appropriate limits. No configuration can promise elimination of all cyber threats.

References: [IITK Network FAQ](https://www.iitk.ac.in/cc/faq/network-faq), [Nginx address access control](https://nginx.org/en/docs/http/ngx_http_access_module.html), [mkcert's own documentation](https://github.com/FiloSottile/mkcert#installing-the-ca-on-other-systems).
