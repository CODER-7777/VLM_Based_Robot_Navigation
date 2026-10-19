#!/usr/bin/env python3
"""Copy finished human samples; convert media in the copy without editing v1."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
OLD = ROOT.parent / 'level3_manual_collector'


def main():
    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    report = {'source': str(OLD), 'started_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'samples': []}
    for manifest in sorted((OLD / 'sessions').glob('*/*/manifest.json')):
        data = json.loads(manifest.read_text())
        if data.get('recording_source') != 'human_manual':
            continue
        source = manifest.parent
        target = ROOT / source.relative_to(OLD)
        if target.exists():
            raise RuntimeError('Will not overwrite an imported sample: ' + str(target))
        shutil.copytree(source, target, ignore=shutil.ignore_patterns('*.webm', '*.ogg', '*.uploading'))
        conversions = {}
        for folder in ['screen', 'audio']:
            for original in sorted((source / folder).glob('*')):
                if not original.is_file() or original.suffix not in ['.webm', '.ogg']:
                    continue
                result = target / folder / (original.stem + '.mp4')
                if not result.exists():
                    cmd = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-n', '-i', str(original)]
                    if folder == 'screen':
                        cmd += ['-map', '0:v:0', '-map', '0:a:0?', '-c:v', 'libx264', '-preset', 'veryfast',
                                '-crf', '22', '-pix_fmt', 'yuv420p', '-r', '15', '-threads', '2']
                    else:
                        cmd += ['-map', '0:a:0', '-vn']
                    cmd += ['-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', str(result)]
                    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                conversions[str(original.relative_to(source))] = str(result.relative_to(target))
        # Point copied annotations at the copied MP4 files, preserving provenance.
        events = target / 'events.jsonl'
        if events.exists():
            rows = [json.loads(line) for line in events.read_text().splitlines() if line.strip()]
            for row in rows:
                if row.get('type') == 'media' and row.get('path') in conversions:
                    row['source_original_path'] = row['path']
                    row['path'] = conversions[row['path']]
                    row['mime_type'] = 'video/mp4' if row.get('kind') == 'screen' else 'audio/mp4'
                if 'text' in row:
                    for old, new in conversions.items():
                        row['text'] = row['text'].replace(old, new)
            events.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows))
        data['navigation_video_status'] = 'ready'
        data['imported_from_dashboard_v1'] = str(source)
        (target / 'manifest.json').write_text(json.dumps(data, indent=2) + '\n')
        (target / 'import_provenance.json').write_text(json.dumps({
            'original_session': str(source), 'source_manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest(),
            'media_conversions': conversions, 'old_files_unchanged': True,
        }, indent=2) + '\n')
        report['samples'].append(str(target.relative_to(ROOT)))
        (ROOT / 'import_verification.json').write_text(json.dumps(report, indent=2) + '\n')
        print('IMPORTED', source.name, flush=True)
    report['completed_at'] = dt.datetime.now(dt.timezone.utc).isoformat()
    report['all_imports_completed'] = True
    (ROOT / 'import_verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
