# Files selected for GitHub

The explicit [publication manifest](../publication_files.json) selects research source, website HTML/CSS/JavaScript, server/account/upload code, certificate-generation and packaging scripts, example configuration, launchers, tests, attribution notes and small aggregate research results. Historical benchmark tables are retained.

The Task 5 `.gitignore` is generated from that list and excludes everything else by default. It does not delete/relocate local files. Add new source/documents to the manifest before including them in a later commit.

Local-only material includes:

- Human sessions, recordings, transcripts, raw uploads, account databases, logs and runtime state.
- Live configuration, per-account assignments, passwords, private keys, certificates and generated ZIP/TAR packages.
- Downloaded annotations, source presentations, prepared cases with embedded imagery, scene meshes, rendered household views and third-party models/textures.
- Generated `verify_*.py` scripts and verification dumps, duplicate/backup collectors, poster-generation prompts, personal screenshots, unrelated CSVs and the internal Wi-Fi document.

Historical experiment READMEs describe local outputs and may link to files absent from GitHub. The root README and `docs/` provide the standalone research account. Collectors require authorized external simulator/data inputs for rendering.

```sh
python3 -B tools/github_publication.py --check
python3 -B tools/github_publication.py --write-ignore

# Optional separate source-only folder for review/sharing.
python3 -B tools/github_publication.py --export /tmp/task5-source-review
```

The exporter refuses symlinks, missing files, generated verification scripts, unexpected file types, large files, embedded image payloads and recognizable credential/key material. It guards against accidental inclusion; it is not a complete secret scanner. Review staged changes before pushing. Ignore rules do not remove files already tracked in older commits; removing their index entries leaves local copies intact and does not rewrite existing Git history.
