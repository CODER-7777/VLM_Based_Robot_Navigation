> For the current launcher packages, use [the short launcher guide](STUDY_LAUNCHER_GUIDE.md). The certificate setup below applies to legacy direct-browser access.

# IITK navigation study — participant guide

**Website:** https://172.26.186.222:8443

**Use:** a laptop/desktop, Chrome or Edge, and a working microphone.

**Account:** the study owner sends your username/password privately. The same guide applies to every account; record the tasks shown after your login.

## 1. Connect to IITK

1. Connect to IITK Wi-Fi or campus LAN.
2. Complete the normal IITK network/firewall sign-in if required.
3. Stay on that connection throughout recording and upload.

**If the website says “available only from the approved IITK network”:** reconnect to the approved IITK connection and refresh the page. If it still appears, send the owner the error and your current IPv4 address. The initially blocked participant addresses have been enabled. Reinstalling the certificate will not fix a network-access error.

Network approval is separate from certificate trust and your website password. Access is restricted to approved addresses; a changed IP may need an owner update. Do not change your Wi-Fi security/certificate settings for this website.

## 2. Install the website certificate once

Extract `IITK_Dashboard_Participant_Pack.zip` with **Extract All**. Open the extracted folder, not the ZIP preview. It contains this README, `rootCA.crt`, the reasoning template and, when provided, a quick-start image.

Only install the certificate received directly from the study owner. Verify its SHA-256 file checksum before installing:

```text
5d5d81ac9d7a884bf579c3cf9cc478e5b66a907b26a3356b88d4f66baf27b445
```

Uppercase/lowercase letters in the checksum are equivalent. Follow only your operating system's steps below. This certificate is for the research website, not the IITK Wi-Fi login.

### Windows 10/11

1. Open the extracted folder in File Explorer.
2. Click its address bar, type `powershell`, then press Enter.
3. Run this command and compare its **Hash** with the checksum above:

```powershell
Get-FileHash .\rootCA.crt -Algorithm SHA256
```

4. If it matches, run:

```powershell
certutil.exe -user -addstore Root ".\rootCA.crt"
```

5. “Command completed successfully” or “already in store” means the import succeeded. No certificate password is required.
6. Close **all** Chrome/Edge windows, reopen the browser, and open the exact website URL above. Finish any unrelated browser work before closing it.

**For the screenshot showing “already in store”: installation is complete.** Do not repeat installation for the “approved IITK network” error.

### Ubuntu

Open Terminal in the extracted folder, compare the checksum, then install:

```bash
sha256sum rootCA.crt
sudo install -m 0644 rootCA.crt /usr/local/share/ca-certificates/task5-collector-root.crt
sudo update-ca-certificates
```

Restart the browser completely. If Chrome still does not trust the site, open `chrome://settings/certificates` and import `rootCA.crt` under its local/custom certificate authorities for trusting websites. Browser labels vary. On a managed device, ask its administrator if installation is blocked.

### macOS

1. In Terminal from the extracted folder, run `shasum -a 256 rootCA.crt` and compare the checksum.
2. Open **Keychain Access** and import `rootCA.crt` into your login keychain.
3. Open **Task5 Collector Private Root CA → Trust → When using this certificate → Always Trust**. Authenticate if prompted.
4. Restart the browser completely.

If a browser privacy/certificate warning remains, contact the owner before recording. Do not use “Proceed anyway” as the setup procedure.


## 3. Sign in and choose your assigned task

1. Open **https://172.26.186.222:8443**.
2. Enter the study username/password sent privately to you. No registration, invitation code, SSH or server account is needed.
3. Wait for a visible house view. There are two simultaneous simulation slots; if both are busy, keep the waiting page open.
4. Select one task in the **Episode** menu. Record **each assigned task in a separate sample**. The account determines which tasks are available; do not try to select another person's assignment.

Your assignments are shown only after you sign in. Follow the tasks visible in your own account. This shared guide does not list participants, their tasks or route lengths.

Navigate naturally; do not add loops. Physical pickup/carrying is assumed in these static scenes, not simulated.

## 4. Record one task — follow this order

### A. Review and create

1. Read **YOUR TASK** and **Current state**. Leave the assigned text unchanged.
2. Review the memory statements/photos. Click a photo to enlarge it; close it with ×.
3. Tick **Relevant memory** for the memory or memories you actually use.
4. Click **Create new sample**. Stay at the start while preparing screen/microphone capture.

**Memory selections are saved.** Initial ticks are stored when the sample is created. If you later change the ticks, click **Save reasoning text** to record the updated selection as a saved annotation.

### B. Start screen and microphone

5. Click **Record screen + microphone**.
6. In Chrome/Edge's chooser, select the dashboard tab or window and click **Share**. Share only this dashboard, without unrelated private content.
7. Allow microphone access and choose the correct microphone if asked.
8. After the browser prompts close, click **Enter full screen & start recording** in the website.
9. Confirm the website says screen capture is on before moving. Say your overall task explanation aloud so it is included in the microphone recording.

The share chooser can exit fullscreen. The separate **Enter full screen & start recording** click restores it. If fullscreen is denied, retry or use the displayed **Start without full screen** option. This screen-recording option already includes the microphone; a second simultaneous voice recording is unnecessary.

### C. Navigate and speak

Click the house view before using the keyboard. On-screen movement buttons also work.

| Control | Action |
| --- | --- |
| **W / Forward** | Forward 25 cm |
| **A / Left** | Turn left 15° |
| **D / Right** | Turn right 15° |
| **Space / STOP & save** | End the sample — not pause |

There is no reverse key: turn around with A/D if needed. Movement keys do not navigate while you type in a text box. If blocked by furniture, choose another direction.

**Speak aloud in simple English while navigating.** Explain what you see, which memory it matches, and why you choose each turn, forward movement, correction or stop. The screen-and-microphone recording captures this together.

Use these patterns with your actual observations:

> “I am turning left because [visible landmark] matches [the relevant memory].”
>
> “I am moving forward because [reason from my current view].”
>
> “This does not match the memory, so I am changing direction because [reason].”
>
> “These features match the destination, so I will stop.”

Explain decisions as they happen, rather than only giving an initial overall plan. Use only your assigned task, supplied memories and visible evidence.

The optional route aid is a hint. Try the memories first; mention any aid/help you used. Do not claim an object is visible or picked up when it is not.

### D. Stop, upload, write and verify

10. At your chosen destination, click **STOP & save** once.
11. Keep the page open while uploads and MP4 preparation finish. Do not refresh, close the tab or sign out during this stage.
12. Put what you said during navigation in **Corrected reasoning transcript** and click **Save reasoning text**. Check that it matches your task and run; correct it if your plan changed. This field is not automatically transcribed from the microphone.
13. Under the saved recording preview, select the **screen recording**, press Play, and check that both the dashboard and your voice are present. The navigation replay alone is silent.
14. Confirm there are no pending uploads/export errors. Your sample is saved on the server; downloading a copy is optional.

Include the reasons you spoke while navigating, including uncertainty or changes of direction. Save the corrected transcript after the run. See `REASONING_TEMPLATE.txt` for examples.

### E. Repeat and sign out

15. Choose the next assigned task only after the current sample and uploads finish.
16. Review/tick its memories, click **Create new sample**, then repeat the workflow above.
17. Review your saved samples. Once uploads/conversion finish, click **Save, then sign out**.

Use your own account and one dashboard tab. Do not delete samples unless the owner asks you to.

## 5. What is saved and where

The server saves your selected memory IDs, navigation frames/actions/poses, screen video with microphone audio, corrected reasoning/events and an audio-only copy extracted from each screen recording. The complete sample ZIP includes the separate `audio/screen_NNN.m4a`. No manual upload to another website or SSH transfer is required.

Your recordings are stored privately on the research server under your own account. No server-directory information or other participants' recordings are included in this guide.

## 6. Troubleshooting

| What you see | What to do |
| --- | --- |
| “Approved IITK network” error | Stay on IITK Wi-Fi/LAN, complete network sign-in, and contact the owner. This is the server's network allowlist, not a certificate/password error. |
| Browser privacy/certificate warning | Verify/install the supplied certificate and restart the browser. If unresolved, contact the owner. |
| “Already in store” during certificate import | Installation succeeded; continue to the website. |
| Invalid login | Recheck the privately supplied study credentials; contact the owner if needed. |
| Waiting for a simulation slot | Keep the page open; two contributors can run at once. |
| No movement | Create a sample, close dialogs, click the scene, then use W/A/D or buttons. |
| No fullscreen after sharing | Click **Enter full screen & start recording** after the browser chooser closes. |
| Silent preview | Select the screen recording, check microphone permissions/input device, then contact the owner if still silent. |
| Upload failed | Keep the page open and use **Recover uploads**. Retry or download the source clip for the owner before closing. |

Only if the owner requests network diagnostics: Windows → open PowerShell → run `ipconfig` → report the **IPv4 Address** and **Subnet Mask** under the active Wi-Fi/Ethernet adapter. Do not change them or send your Wi-Fi password. This is troubleshooting, not a normal requirement for every participant.
