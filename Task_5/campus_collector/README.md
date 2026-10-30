# Campus-only multi-contributor recording website

For a fresh GitHub checkout, first follow [source preparation](../docs/REPRODUCIBILITY.md). Prepared cases with embedded images, live configuration, per-account assignments, TLS files and recordings are intentionally excluded. Generate/copy those local inputs before building a deployment package.

For participant access, start with the [portable launcher guide](STUDY_LAUNCHER_GUIDE.md). For server certificate setup, follow the laptop's [Task_5/CAMPUS_COLLECTION_START_HERE.md](../CAMPUS_COLLECTION_START_HERE.md). Local setup files, certificates and deployment packages stay under Task_5. Deploy the server application to `/home/guest-isl/rishabh/bench/experiments/Data_from_Dashboard/campus_collector/`. The requested server recording root is `/home/guest-isl/rishabh/bench/experiments/level3_manual_collector_v2/data_collecting/data/`. Existing scene datasets and the Python environment are referenced in place.

This is a separate authenticated gateway and isolated-worker copy of the existing voice/video collector. The original collectors on ports 8876 and 8878 are preserved.

The intended experience is one shared **trusted HTTPS** URL. On an approved IITK network, a contributor signs in using the ID/password supplied privately by the study owner, chooses an episode and relevant memories, creates a sample, records screen and microphone, navigates and presses STOP & save. Participants speak their reasoning while navigating, explaining visible landmarks, memory matches and movement decisions in simple English. The simulator runs on the server; screen/microphone capture runs in the browser, and media conversion occurs on the server after upload. No contributor SSH or OS account is required. See the [task and recording procedure](../README.md#collection-task-and-participant-procedure).

## Current state

- Owner-created contributor accounts, authentication and separate Habitat processes/recording folders are implemented. Self-registration is disabled.
- Source template contains only application files and source episode inputs, not previous human recordings.
- Local integration checks cover authentication, two concurrent users, cross-user denial, uploads, safe sign-out and network restrictions.
- The campus listener uses `https://172.26.186.222:8443` with private-CA HTTPS. Direct browser access requires trusting the public study CA; the portable launcher instead scopes that CA to its own verified HTTPS client. The owner-approved deployment policy currently permits `172.16.0.0/12` and still requires website login. This is a deployment choice, not a verified complete IITK allocation or an SSID check. Both campus SSIDs can work when routing and source addresses meet the policy; VPN or campus relays may also satisfy it. Outside-network denial has not been independently tested. Confirm authoritative ranges with IT; see `IT_REQUEST.md` for institution-issued HTTPS.
- Private administration is available at `/admin`. Enabled administrators receive the complete 53-entry catalog (20 + 20 + 10 + 3); contributors receive their own assigned selection. The UI supports account creation, assignment, password reset, private catalog exports and a changes log. One imported task is missing its required request photo and is admin-preview only. See [the admin guide](ADMIN_GUIDE.md). Actual account assignments remain in private server storage and are not listed in shared documentation.

- Default capacity is **two simultaneous contributors**, using physical GPU 0. Additional users see a waiting page. Increase `max_workers` only after measuring memory and latency. An active sample is not evicted merely because it becomes idle.

## Architecture

```text
Contributor browser on approved IITK network
    -> HTTPS campus interface + network allowlist
    -> authenticated gateway (one common URL)
       -> contributor A's loopback Habitat process + files
       -> contributor B's loopback Habitat process + files
```

Each login is a contributor account in `accounts.sqlite3`, not a server account. Passwords use salted scrypt; random login tokens are stored hashed and expire after eight hours. Login has rate/concurrency limits. Administrators create contributor accounts and reset passwords through the private admin page. Administrator roles are provisioned through the server CLI; public registration endpoints are unavailable. Legacy invitation records are disabled without deleting accounts or recordings. Production cookies are Secure, HttpOnly and SameSite=Strict. Cross-origin POSTs and cross-contributor media/session references are denied. The gateway ignores forged forwarding headers. Only enumerated collector routes are relayed; source directories are not exposed as a static file tree.

The gateway streams uploaded bytes to the contributor's private backend. Each completed screen recording also produces an audio-only `audio/screen_NNN.m4a` with a source-mapping JSON sidecar; extraction prefers copying the encoded audio stream, leaving the video and standalone voice recordings unchanged. The audio appears in API listings, can be downloaded directly, and is included in the complete sample ZIP. `backfill_screen_audio.py` processes completed current samples with `--apply`; it does not process deleted samples. The backend stages media on server disk and creates H.264/AAC MP4 outputs. The browser keeps a source clip until the server accepts its upload, using IndexedDB when browser storage is available and a memory fallback otherwise. **Recover uploads** lets the contributor retry or download a failed source clip. Keep the browser open until uploads finish; memory-only backups do not survive closing the page. Retry requires the original sample. The launcher also checkpoints recording chunks and reasoning/memory drafts in browser IndexedDB. New/restarted workers restore unfinished navigation from an owner-scoped durable checkpoint; use the same browser profile for local media recovery. Interrupted recordings may lack their final unsaved seconds. Sign-out waits for sample completion, pending clips, in-flight transfers and MP4 processing, then releases that contributor's worker. Finished inactive workers can be reclaimed after ten minutes. Abandoned active samples need administrator review rather than automatic deletion.

Files are stored under:

`<data_root>` is `/home/guest-isl/rishabh/bench/experiments/level3_manual_collector_v2/data_collecting/data/` in both production examples. This is server storage, not a laptop destination. Existing sessions in the original collector's `sessions/` folder are not migrated by changing the shared collector's configuration.

```text
<data_root>/
  accounts.sqlite3
  contributors/<contributor_id>/
    sessions/<contributor_id>/<UTC sample timestamp>/
      inputs.json, frames/, trajectory.jsonl, events.jsonl
      audio/voice_*.mp4
      screen/screen_*.mp4
      navigation.mp4, manifest.json
    deleted_sessions/    # recoverable deletions in that contributor's worker
    .uploads/            # staged/recoverable incoming media
    worker.log
```

## Production setup (administrator, on the simulation server)

1. Put this application folder in a retained project directory. Retain the existing `navila` environment, source presentation and MP3D scene paths used by the template.
2. Copy `config.production.example.json` to `config.production.json` and fill the values supplied by IITK IT. `public_origin` is the exact HTTPS origin, including `:8443` when used, with no trailing slash. Keep `allowed_networks` explicit; do not substitute all private addresses or `0.0.0.0/0`.
3. Create a contributor account for each person:

   ```sh
   python3 -B gateway.py --config config.production.json --add-user contributor_01
   ```

   Each command prompts for a password of at least 12 characters and confirmation. Share each ID/password privately with its contributor. They sign in directly; there is no signup page or invitation code. Existing accounts continue to work. No password is passed in shell arguments or written in source/configuration; no contributor needs SSH. Share the public root certificate separately for this private-CA deployment.
4. Start the HTTPS gateway using the launcher:

   ```sh
   sh start_campus_collector.sh config.production.json
   ```

   The launcher uses tmux if installed, otherwise a systemd user service. The current simulation server uses `data-from-dashboard-collector.service`; inspect logs with `journalctl --user -u data-from-dashboard-collector.service -f`. Confirm startup and the assigned HTTPS URL from a contributor device before sharing it. This starts no renderer until an authenticated contributor opens the dashboard.
5. Verify both boundaries: an allowed campus device can sign in and save a sample, while an outside-network device is denied. Browser microphone/screen permissions must be approved by the contributor.

Disable an account and invalidate its browser login tokens with:

```sh
python3 -B gateway.py --config config.production.json --disable-user contributor_01
```

For forgotten passwords, the owner can verify the contributor through the study channel and use `--reset-password contributor_01`, which prompts for a replacement, invalidates old login tokens and preserves the account's recordings. Let recordings/uploads finish before a reset. Email delivery/verification and IITK SSO are not configured; the website's login is a separate study account.

See [PARTICIPANT_GUIDE.md](PARTICIPANT_GUIDE.md) for sharing instructions and [CLOUDFLARE_NOTES.md](CLOUDFLARE_NOTES.md) for the tunnel alternative.

## Development and verification

`--dev` is restricted to loopback HTTP for administrator testing; it is not the shareable campus deployment. It never binds a campus interface.

```sh
python3 -B -m unittest discover -s . -p test_gateway.py -v
python3 -B gateway.py --config config.dev.example.json --dev
```

Generated browser and real-worker verification tools and reports remain local. The published unit tests use temporary users, storage and synthetic routes; real rendering additionally requires the separately installed simulator and authorized assets.

HTTPS requirements: [MDN screen capture](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getDisplayMedia). IITK certificate support is described in [Computer Centre information](https://linux.cc.iitk.ac.in/lininfo/What_computer_center_provid.html); current provisioning and campus ranges must be confirmed by IT.
