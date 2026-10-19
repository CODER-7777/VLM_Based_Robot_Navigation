# Cloudflare Tunnel alternative

Cloudflare Tunnel can provide a browser-trusted HTTPS hostname while a server connector makes an outbound connection to Cloudflare. The server still stores uploaded recordings at the configured `data_root`, but requests and uploads pass through Cloudflare. This is an alternative to the direct-campus/private-CA setup; no tunnel has been started or published by this preparation.

For the requested IITK-only workflow, a tunnel alone is insufficient. Use a managed tunnel with a stable hostname and an Access policy that requires the approved IITK **public Internet egress IPv4/IPv6 ranges**. If email authentication is also desired, require the network condition in addition to the email identity, rather than allowing either condition independently. IITK email ownership alone does not prove current campus connectivity. The observed private Wi-Fi range `172.24.200.0/22` is not the public source range that Cloudflare sees.

The gateway currently implements direct-campus TLS and checks the TCP peer against private campus ranges. It deliberately ignores forwarding headers. A tunnel delivery mode therefore needs explicit application changes: bind the origin to loopback, set the public hostname/origin correctly, authenticate the trusted tunnel/Access boundary, and evaluate the appropriate client IP without trusting arbitrary forwarded headers. Do not expose the origin directly or disable its restrictions to make a quick tunnel work.

Before configuring a managed tunnel, obtain the Cloudflare account/hostname arrangement and approved campus public egress ranges. A hostname in your own Cloudflare-managed domain avoids changing the URL across restarts. Access and connector setup must be tested from both allowed-campus and outside connections. Keep connector credentials under the server's `Data_from_Dashboard` folder, excluded from source archives and contributor files.

Quick Tunnels generate temporary `trycloudflare.com` URLs and are intended for development/testing. Their hostname changes when recreated. Current documentation also describes email restrictions for Quick Tunnels, but email restrictions alone do not satisfy the IITK-network-only requirement.

Cloudflare also imposes per-request upload size limits (currently 100 MB on Free/Pro, 200 MB on Business, up to 5 GB on Enterprise). The existing collector accepts up to 300 MB per clip; longer clips could therefore require chunked upload support or another upload arrangement before using a tunnel. Verify the applicable plan and test realistic recording sizes first.

Official references:

- [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/)
- [Access policy IP conditions](https://developers.cloudflare.com/cloudflare-one/access-controls/policies/)
- [Quick Tunnel behavior](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)
- [Upload limits](https://developers.cloudflare.com/support/troubleshooting/http-status-codes/4xx-client-error/error-413/)
