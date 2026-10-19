# Draft request for IITK IT / the lab network administrator

Please provision a stable campus-only HTTPS address for our human navigation demonstration collector, using a certificate already trusted by normal contributor browsers. We want contributors to open the link without certificate warnings or installing a custom root certificate.

The application server is **172.26.186.222**. Contributors should access one shared browser URL while connected to the approved IITK network; they must not need SSH, shell accounts, or the server password. Several authenticated contributors will record independently. Microphone audio, screen video, navigation frames and corrected transcripts are uploaded directly to this server.

The existing application is running at `https://172.26.186.222:8443` using our private CA. The study owner creates a separate application username/password for each contributor; self-registration is disabled. We need DNS/HTTPS/network provisioning, not a new application or contributor shell accounts. Cloudflare is not being used.

Application directory: `/home/guest-isl/rishabh/bench/experiments/Data_from_Dashboard/campus_collector/`.

Recording destination: `/home/guest-isl/rishabh/bench/experiments/level3_manual_collector_v2/data_collecting/data/`.

We need:

1. An approved IITK DNS hostname resolving to this campus interface.
2. Browser-trusted HTTPS for that hostname, preferably on port **443** through an existing IT-managed reverse proxy. Please confirm that ordinary browsers will trust the complete certificate chain without participants installing an IITK/private root CA. A certificate signed only by an internal CA may still need client trust installation, which we are trying to avoid. Alternatively, supply an appropriate server certificate/full chain and private-key **file paths on the server**; never send private-key contents in messages. Please clarify who handles certificate renewal. HTTPS must support browser microphone and screen-capture APIs.
3. The exact approved campus client IPv4/IPv6 ranges. Please specify whether institute VPN clients are included. The application must be unreachable from other networks; also enforce this at the campus/host firewall.
4. Campus-only reachability on the chosen HTTPS port (preferably **443**), forwarding to the existing application on **8443** if a reverse proxy is used. The application binds the approved campus interface explicitly. Ports **9100–9101** are private per-contributor workers and must remain loopback-only; do not expose existing local collector ports 8876/8878.
5. If a reverse proxy is used, it must enforce the campus allowlist itself and preserve the approved Host/Origin. The application does not trust arbitrary X-Forwarded-For headers. Allow uploads up to 300 MB and response/upload timeouts up to 600 seconds.

Please return the approved hostname/URL, whether browser trust requires any client installation, allowed network ranges, listening-port/proxy arrangement, and certificate file paths if TLS is hosted on our server. Our current application allowlist is `172.24.200.0/22`, verified as the owner's current Wi-Fi subnet; it does not cover every campus building. The observed server interface prefix is /21; that is also not a verified allowlist for the whole IITK campus.

Nothing in this request asks for public Internet publication or contributor shell access. This is a draft only; it has not been sent.
