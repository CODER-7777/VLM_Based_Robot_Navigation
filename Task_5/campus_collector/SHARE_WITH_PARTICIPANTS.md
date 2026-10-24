# What to share

Share the participant launcher ZIP for each person's operating system:

| Operating system | Participant package | Admin-only package |
| --- | --- | --- |
| Windows | IITK_Study_Launcher_Windows.zip | IITK_Admin_Launcher_Windows.zip |
| Linux | IITK_Study_Launcher_Linux.zip | IITK_Admin_Launcher_Linux.zip |
| macOS | IITK_Study_Launcher_macOS.zip | IITK_Admin_Launcher_macOS.zip |

The same participant ZIP serves everyone on that platform. Share each account's login privately. Assignments remain on the server; they are not listed in the package. Keep admin packages, catalog exports and server archives private.

Participants follow README.txt and REASONING_TEMPLATE.txt. They record screen and microphone together, explain their decisions while navigating, then save their corrected transcript. WhatsApp messages and poster-generation prompts are not included in the launcher ZIPs.

Build the local packages with an official Go compiler and the owner-supplied public study CA:

```sh
python3 -B build_study_launcher.py --go /absolute/path/to/go
```

See [launcher build notes](study_launcher/README.md) for prerequisites and platform limitations. Binaries, certificates, account data, live configuration and recordings are excluded from Git. The separate certificate-package builder remains available for legacy direct-browser installations.
