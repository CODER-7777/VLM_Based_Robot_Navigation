# Draft request for IITK IT / the lab network administrator

## Short message to forward

> Please provision `mvivek24.iitk.ac.in` for our research data-collection dashboard, or assign another approved IITK hostname. The application is already running on `172.26.186.222:8443`. We need HTTPS that normal browsers trust without participants downloading or installing a certificate. Please provide the DNS entry, a browser-trusted server certificate with renewal, and campus-only network access. Existing website username/password authentication and server-side recording storage must remain in place. The hostname does not currently resolve in either our laptop or campus-server lookup; it is a requested name, not an existing assigned address.

The `.iitk.ac.in` suffix or an IITK username alone does not provision a hostname. IT must allocate the name and configure its DNS. A private-CA certificate, even if issued for the new hostname, would still require participants to install its root certificate. We need a certificate chain already trusted by ordinary browsers.

After provisioning, participants should only need to connect to the approved campus network, open the shared HTTPS URL, sign in, and grant the normal microphone/screen-sharing permissions. No certificate ZIP or contributor SSH access should be required. This new flow is not live until the hostname and trusted certificate are actually installed and tested.

## Technical handoff

### Observed DuckDNS network block — 24 October 2026

On the current campus connection, both `duckdns.org` and `www.duckdns.org` resolve to `208.91.112.55` (and `2620:101:9000:53::55`). A read-only TLS check receives a self-signed certificate whose subject and issuer are `O=Fortinet, CN=Fortiguard SDNS Blocked Page`. This explains the browser's `NET::ERR_CERT_AUTHORITY_INVALID` warning for DuckDNS on this connection. No trust-store, DNS, firewall or study-server settings were changed for this diagnosis.

Please confirm whether DuckDNS is permitted for this research service. If so, arrange the appropriate network exception and verify the actual registered hostname from participant networks. Otherwise, please identify an approved DNS/hosting provider or institute-managed HTTPS hostname. Registering a name through a different network alone would not resolve a campus filtering restriction.

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

Please return the approved hostname/URL, confirmation that browser trust requires no client installation, allowed network ranges, listening-port/proxy arrangement, and certificate file paths if TLS is hosted on our server. The current application allowlist combines an earlier approved Wi-Fi range with explicitly approved individual client addresses; it is not a verified allowlist for the whole IITK campus. Please supply the actual approved campus ranges so participants do not need repeated individual IP approval as their Wi-Fi addresses change. Do not assume that every private address belongs to IITK.

Direct TLS on the existing port 8443 is sufficient if the certificate is browser-trusted and covers the assigned hostname. Standard HTTPS on port 443 is preferable if IT can provide it. When changing the URL, the application public origin must be changed to the exact assigned HTTPS URL as well. If a reverse proxy is chosen, coordinate its backend source address and Host/Origin with the gateway; simply adding a proxy without updating these checks will cause access denials.

An internal-only server can obtain a publicly trusted certificate through DNS validation when the DNS/domain administrator supports it; the application does not need to be exposed publicly for DNS-01. See [Let's Encrypt's official DNS-01 documentation](https://letsencrypt.org/docs/challenge-types/#dns-01-challenge).

Nothing in this request asks for public Internet publication or contributor shell access. This is a draft only; it has not been sent.
