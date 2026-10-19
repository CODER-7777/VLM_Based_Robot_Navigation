# Reproducing source checks and deployment

## Source-only checks

From `Task_5`, with Python 3.10+:

```sh
python3 -B tools/github_publication.py --check
python3 -B -m unittest discover -s campus_collector -p 'test_*.py'
```

These tests use temporary files and synthetic cases. They need no scene images, authored household files or GPU, but bind temporary loopback HTTP servers. The gateway uses the standard library; test passwords are generated for temporary accounts.

For the synthetic audio integration check, install `imageio-ffmpeg` in a suitable environment, then run:

```sh
python3 -B campus_collector/verify_screen_audio.py \
  --template campus_collector/template --report /tmp/task5-audio-check.json
```

This creates a synthetic tone/video and checks extraction, idempotence, media download and ZIP contents without touching human recordings. Browser checks additionally need Chrome/Chromium; inspect their script arguments. Real-worker checks require the simulation environment and create temporary QA accounts/artifacts; run them on a prepared test deployment.

## Route search

`rxr_long_route_search/search_rxr.py` downloads official validation guide annotations and connectivity JSON into an ignored `sources/` cache. Network access is required; generated outputs stay local:

```sh
python3 -B rxr_long_route_search/search_rxr.py
```

The recorded audit used connectivity revision `589d091b111333f9e9f9d6cfd021b2eb68435925`. The script resolves the upstream revision when first run and records hashes. For exact replication, use the recorded revision/cache; a fresh revision may change inputs. `docs/rxr_validation_summary.json` is a publication snapshot, not automatically updated by a new search.

Semantic review additionally requires authorized `.house` annotations; RGB rendering requires matching meshes and Habitat-Sim. Images/3D assets are not supplied by this checkout. Some research scripts contain original server paths and dated experiment paths; inspect constants before using another machine. Rebuild dashboard catalogs with matching local inputs.

## Website/server preparation

The shared service is `campus_collector/gateway.py`, a Python HTTPS gateway starting separate localhost Habitat workers. Workers need compatible Habitat-Sim, `numpy`, `numpy-quaternion`, Pillow and `imageio-ffmpeg`. Geometry/review tools also use packages such as `trimesh` and `matplotlib`. No universal pinned environment is claimed; the original deployment reuses its simulator environment.

Excluded deployment inputs include the source `presentation.html`, prepared `template/sample_case.json` with embedded imagery, live `template/collection_selection.json`, account database, TLS files, optional authored metadata/images, scene meshes and human recordings.

On a prepared simulation server:

1. Set the presentation/scene paths in `template/collector.py`. From `campus_collector`, run `python3 -B template/collector.py --prepare` to generate the prepared sample without launching Habitat. The current preparer expects laundry episode `QUCTc6BB5sX_8247` in the source presentation.
2. Copy `template/collection_selection.example.json` to `template/collection_selection.json`. Its two default episode IDs must exist in your presentation. Set `authored_source_root` and add `account_episode_keys` only when the extra cases are installed. The synthetic unit fixture demonstrates the authored metadata schema.
3. Copy a `config.*.example.json` to `config.production.json`; adapt bind/origin, interpreter, data root, TLS paths and approved network ranges. Production refuses an empty allowlist. Existing paths are site-specific examples.
4. Follow [the administrator guide](../CAMPUS_COLLECTION_START_HERE.md) for certificates, package transfer, owner-created accounts and startup. Generate new certificates for a new installation. Share [participant instructions](../campus_collector/PARTICIPANT_GUIDE.md), never server keys.

`build_server_package.py` requires the prepared inputs before building an archive. A package made with `--include-tls` contains a private server key and must stay private; packages are excluded from Git.

Server application files live under `Data_from_Dashboard/campus_collector/`; recordings remain under the configured `level3_manual_collector_v2/data_collecting/data/`. Updating GitHub does not deploy/restart the server. Preserve active sessions and deploy only after uploads/conversion complete.

## Local dashboards

[Dashboard startup instructions](../dashboard_startup/README.md) describe the tmux launchers. Research dashboards need generated catalogs/assets. Legacy collection/live render launchers need authorized SSH and existing remote installations; these are administrator tools, not participant links. This publication enables no Cloudflare tunnel.
