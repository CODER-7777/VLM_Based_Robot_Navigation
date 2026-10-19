# IITK voice and video collection — participant instructions

Website: **https://172.26.186.222:8443**

The study owner gives you your individual username and password separately. Use your website account; no server account, SSH access, invitation code or registration is needed.

## 1. Connect and install the certificate once

Use a laptop or desktop with Chrome or Edge, a working microphone, and an approved IITK network. Complete the usual IITK firewall sign-in if your connection requires it. The collector currently allows `172.24.200.0/22` plus the owner's individual IITK address; other IITK clients may need the owner to add their verified address/range. Being on any IITK Wi-Fi does not automatically guarantee access.

Extract the participant ZIP. It contains only:

- `README.md` — this guide.
- `rootCA.crt` — the public certificate to trust this research website.

Before trusting the certificate, confirm its checksum with the study owner through your usual trusted contact. The expected SHA-256 checksum of the file is:

```text
5d5d81ac9d7a884bf579c3cf9cc478e5b66a907b26a3356b88d4f66baf27b445
```

Follow **only the steps for your own operating system**, on your own computer, from the extracted ZIP folder. Trusting this private CA allows certificates issued by the study owner; it does not replace your website login.

### Ubuntu

Open a terminal in the extracted folder:

```bash
sha256sum rootCA.crt
sudo install -m 0644 rootCA.crt /usr/local/share/ca-certificates/task5-collector-root.crt
sudo update-ca-certificates
```

Restart the browser completely. If Chrome still does not recognize the certificate, open `chrome://settings/certificates` and use the certificate manager's custom/local certificate-authority import to trust `rootCA.crt` for websites. Browser labels vary by version. Do not import it as a personal/client certificate. For a managed device, ask its administrator if certificate installation is blocked.

### Windows

Open PowerShell in the extracted folder:

```powershell
Get-FileHash .\rootCA.crt -Algorithm SHA256
certutil.exe -user -addstore Root ".\rootCA.crt"
```

Check the checksum and confirm the certificate import if prompted. This installs into your current user's trusted root store. Restart Chrome/Edge completely. If device policy blocks the import, ask the device administrator.

### macOS

Check the checksum in Terminal from the extracted folder:

```bash
shasum -a 256 rootCA.crt
```

Open **Keychain Access**, import `rootCA.crt` into your login keychain, and open **Task5 Collector Private Root CA**. Expand **Trust**, set **When using this certificate → Always Trust**, and authenticate if prompted. Restart the browser completely.

Open the exact website URL above. If a certificate warning remains, contact the study owner to fix trust before recording. Do not rely on clicking “Proceed”.

## 2. Sign in

Enter the username and password the owner sent you privately. Keep them private and reuse the same account for later visits. Do not enter your IITK CC password or server password.

Two people can use separate simulation slots simultaneously. If the slots are occupied, keep the waiting page open until one becomes available.

## 3. Record these two tasks only

Both are in scene/environment **`2azQ1b91cZZ`**. Use the episode menu to choose each task and follow its displayed memories and current state.

| Episode | Menu title | Task instruction | Original reference route |
| --- | --- | --- | --- |
| `2azQ1b91cZZ_4240` | Return parcel for the courier | “Our return parcel needs to go with the courier who's just arrived. It's on the little table by the front door.” | **41.49 m** |
| `2azQ1b91cZZ_7372` | Help Asha read after dinner | “Asha's having trouble making out the words during her after-dinner reading. Could you help?” | **45.54 m** |

These distances are the sum of 3D segments in the original reference trajectories. Your actual recorded walking distance can differ. Navigate naturally; do not add loops just to exceed 40 m. This study records navigation and reasoning; physical object pickup/delivery is not simulated.

## 4. Understand the website before recording

After signing in, the website opens your simulation. Wait for **Connected** and a visible first-person house view. If the simulation slots are occupied, keep the waiting page open. Each account controls an independent simulation.

- **Environment:** selects the house. For both assigned tasks, choose the environment labelled **Asha & Maya**, scene `2azQ1b91cZZ`.
- **Episode:** selects your task. Choose **Return parcel for the courier** first, then **Help Asha read after dinner** for your second sample. The episode numbers may be 07 and 09; those are original catalog numbers.
- **YOUR TASK / Current state:** tells you the request and situation. Leave this text unchanged for the assigned study.
- **Explore the house:** your current first-person camera view. Click this view before using movement keys.
- **Memories:** photos and the household statements available to you. Scroll sideways to see all photos; click a photo to enlarge it. Use the arrow buttons for other views, then close the enlarged view with ×. Mark **Relevant memory** for the memory or memories you actually use. There is no visual-description field.
- **Recording tools:** starts a sample, records screen/voice, and saves your corrected reasoning transcript.
- **Saved samples & downloads:** lets you review your own completed recordings and download them if needed. Saving to the server does not require downloading a copy.

## 5. Record one complete sample

### A. Select and read

1. Choose the first assigned episode. Wait until its task, memories and scene have loaded.
2. Read the request and current state. Review the memory photos and statements and select the relevant memory checkbox(es).
3. Click **Create new sample**. This begins the navigation log. Stay at the starting position while you set up screen/voice recording.

### B. Start screen and voice

4. Click **Record screen + microphone**. The site opens its focused layout and Chrome’s screen-sharing picker.
5. Choose the dashboard tab/window, click **Share**, and allow microphone access. Once those prompts close, click **Enter full screen & start recording** in the dashboard. Chrome may leave full screen while its picker is open; this second click restores full screen before the video begins. Share only the dashboard, without unrelated tabs or private messages. If full screen is denied, retry or press F11 and choose **Start without full screen**. **Cancel** releases the prepared screen/microphone streams without creating a clip.
6. Check that the recording status indicates screen capture is on. This option already records your microphone. You do not need a second simultaneous **Record reasoning** recording. The server also automatically extracts a separate audio-only clip, such as `audio/screen_000.m4a`, from each screen recording. Both the video and separate audio are included in the complete sample ZIP.
7. Speak a short opening: what the request requires, which memory is relevant, and how you intend to recognize the destination. Begin moving after the screen recording is running.

The site records your microphone; it does not automatically transcribe your speech into the text field.

### C. Navigate and explain decisions

| Key / on-screen button | Action |
| --- | --- |
| **W / Forward** | Move forward by 25 cm. |
| **A / Left** | Turn left by 15 degrees. |
| **D / Right** | Turn right by 15 degrees. |
| **Space / STOP & save** | End the whole sample and save. |

Click the scene to focus it if keys do not move the robot. You can also click the movement buttons. There is no backward movement; turn around with A or D if you need to retrace your path. Space ends the sample, so do not use it to pause. A collision may prevent forward movement; change direction instead of repeatedly pushing into the obstacle. Movement keys do not navigate while you are typing in a text field.

Speak at meaningful decisions rather than every keypress:

- **Start:** what you need and which memory helps.
- **Junction or doorway:** what you see, the direction you choose and why.
- **Correction:** what differed from your expectation and how you adjust.
- **Arrival:** which actual visible features confirm the destination.

Describe what you really observe. Do not read a supplied solution, claim an object is visible when it is not, or add loops to increase distance. **Optional route aid / Show next movement** is an oracle hint: try using the task and memories first; if you need the aid, mention it in your transcript. The system logs use of the aid.

In focused/full-screen mode, **Memories** shows/hides the memory panel and **Recording tools** opens its controls. **Back to setup** restores the normal layout without being a save command. Closing an enlarged photo also does not stop recording.

### D. Finish and save the text

8. When you judge that you have arrived, explain the visible evidence aloud, then click **STOP & save** once. This stops the screen/microphone recording and finishes the navigation sample.
9. Keep the page open while uploads and MP4 preparation finish. Do not refresh, sign out or close the browser during this stage.
10. Open **Recording tools** if needed. Type one **Corrected reasoning transcript** for this sample. It summarizes/corrects what you actually said and did; you do not have to save text after every movement. Click **Save reasoning text**. You may also save notes during a sample if useful.
11. Use the saved recording preview to check that the scene and your voice are present. If the preview selects the navigation replay, choose the **screen recording** in the Recording selector to check microphone audio. Navigation replay alone has no microphone audio.
12. Confirm there are no pending uploads or export errors before starting your next sample.

A useful transcript structure is:

> The task requires [need]. I used [memory] because [reason]. At [landmark I actually saw], I chose [action] because [evidence]. I corrected [mistake, if any]. I stopped because [visible confirmation].

Fill the placeholders using your own run. If you failed to find the destination or needed help, record that honestly. One complete demonstration per assigned task is the minimum requested here; retain an unsuccessful attempt and ask the study owner whether another attempt is needed. Do not delete a sample accidentally while reviewing it.

### E. Record the second episode and sign out

13. After the first sample is fully saved, select **Help Asha read after dinner** from the Episode menu.
14. Click **Create new sample** and repeat the same workflow. Each task must have its own sample.
15. Review both samples under **Saved samples & downloads**. Finish uploads and MP4 preparation, then click **Save, then sign out**.

Raj and Priyansh should each complete both assigned tasks using their own account. Do not share one account between two people, and use one dashboard tab per account to avoid changing the same simulation from multiple tabs.

## 6. Where your recordings go

The website uploads recordings directly to the research server under your account. No manual file transfer or server login is required. The server storage location is:

```text
/home/guest-isl/rishabh/bench/experiments/level3_manual_collector_v2/data_collecting/data/contributors/<username>/sessions/<username>/
```

The collection includes navigation frames/actions, microphone audio, screen video and saved reasoning text. Record only material you agree to contribute to this study.

## If something fails

- **Access denied / cannot connect:** confirm IITK connectivity and firewall sign-in; send the owner your current IPv4 address and error message. The owner may need to approve your campus subnet.
- **Invalid login:** contact the owner; there is no self-service account creation or password reset.
- **Microphone/screen denied:** allow access in the browser's site permissions and try again.
- **Upload interrupted:** keep the page open and use **Recover uploads**. Retry or download the source clip before closing the page, then contact the owner. Do not assume an unfinished upload is saved on the server.
- **Missing audio:** select the screen recording rather than the silent navigation replay, check your microphone/site permission, and contact the owner if the saved screen clip is silent.
- **No movement:** create a sample first, click the scene, and close any open dialog/text field. Use on-screen movement buttons if necessary.
- **Old episodes visible:** finish any existing recording, save all uploads, sign out and sign in again. New collection should show only the two tasks above.

Certificate installation references: [Ubuntu](https://ubuntu.com/server/docs/how-to/security/install-a-root-ca-certificate-in-the-trust-store/), [Chromium Linux](https://chromium.googlesource.com/chromium/src/+/HEAD/docs/linux/cert_management.md), [Windows certutil](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/certutil), [macOS Keychain Access](https://support.apple.com/guide/keychain-access/change-the-trust-settings-of-a-certificate-kyca11871/mac).
