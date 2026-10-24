# Private study administration

Open the collector's HTTPS address followed by `/admin`. Sign in with an administrator account. Contributors cannot open this page or download its catalog.

## Create an account and assign instructions

1. Click **New account**. Enter a username. Leave Password blank to generate one, or enter a password of at least 12 characters.
2. Click **Create account**. Copy the credentials shown once and share them privately with that person. Closing the dialog clears the password from the page.
3. Select the person in **People**. Filter by collection, search, or choose **At least 40 m**. Tick the instructions and click **Save assignment**. Saving replaces that person's selection.
4. Ask the person to reload their collector page. They will see only their assigned instructions. A new account with no tasks cannot start a collector yet.

The optional “Assign the tasks currently selected” checkbox copies the editor's selection to a new account. It starts unchecked. Never share the admin page, catalog exports, or another person's credentials in a participant pack.

## Manage access

**Reset password** generates a new password and expires the old login. **Disable account** blocks sign-in. Both preserve saved recordings. Administrators have the complete available catalog automatically; their roles cannot be changed through the website.

Assignments and access changes are rejected while that person has an active recording, upload, or processing job. Wait until it finishes. If another admin changes the same assignment, refresh and review their changes before saving again.

The page shows saved sample counts and a recent changes log. It does not grant SSH, filesystem, or operating-system administrator access. Network approval and certificate trust still apply independently of website accounts.

## Source folders and research scope

The private **Which folder contains which instructions?** table lists every collection's source folder and file. Download the CSV or Markdown export for the complete instruction-by-instruction table.

- The forty-case collection uses its main Level 3 requests, labeled cases 01–20 and 21–40. These labels do not imply a new difficulty split.
- The existing ten presentation cases and three household cases are separate collections. Some requests are related scenarios; 53 catalog entries are not a claim of 53 independent houses.
- Length is the sum of the saved reference path's 3D segments. The **At least 40 m** filter uses that measurement, not shortest-path distance or a recorded participant run.
- Requests, memory images and routes come from the configured sources. Optional off-limits/multi-goal variants in the forty-case file are not additional imported instructions. Object pickup, placement, cleaning and other state changes remain conversational context.
- A task missing a required request photo remains visible to admins, with a warning in its details, but cannot be assigned to contributors. Review imported tasks before using them in a study; import and renderer checks do not establish semantic correctness.

Recordings continue to use the configured `data_root`; changing assignments does not move or remove them. Roles, assignments and the audit log are additive tables in the existing account database. Passwords use the existing salted password hashing and are never written to the audit log.

## Server setup and recovery

Deploy `gateway.py`, `admin_tools.py`, `admin_web/`, the campus client and the updated collector template together. Keep the production configuration, account database, certificates, source datasets and participant recordings private. Back up the account database and replaced source files before deployment. Restart only when no recording, upload or processing is active.

Enable optional collections in the private template selection file:

```json
{
  "authored_source_root": "/absolute/path/to/the/three-case-folder",
  "house40_source_root": "/absolute/path/to/house_first",
  "house40_rxr_file": "/absolute/path/to/val_unseen_guide.json.gz"
}
```

Keep the existing selection settings and assignments when adding these fields. The forty-case source folder must contain its case JSON, week-log JSON and rendered memory images under `verify/2azQ1b91cZZ/`.

Bootstrap an existing enabled account as an administrator from the server application folder:

```sh
python3 -B gateway.py --config config.production.json --grant-admin USERNAME
```

Use `--revoke-admin USERNAME` to return an administrator to contributor access. The CLI prevents removing the final enabled administrator. Keep role provisioning restricted to the study owner.

For validation, run `python3 -B -m unittest discover -s campus_collector -p 'test_*.py'` from Task_5 and `python3 -B campus_collector/verify_admin_browser.py` for the isolated synthetic Chrome check. `verify_catalog_renderer.py` runs on the simulation server, keeps images there, and creates no participant recordings.
