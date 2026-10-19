"""Extract separate audio for completed, non-deleted collection samples on the server."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--template', required=True, type=Path)
    parser.add_argument('--data-root', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    sys.path.insert(0, str(args.template.resolve()))
    spec = importlib.util.spec_from_file_location('audio_backfill_collector', args.template / 'collector.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    rows = []
    for account in sorted((args.data_root / 'contributors').iterdir()):
        if not account.is_dir(): continue
        for sample in sorted((account / 'sessions').glob('*/*')):
            if not (sample / 'manifest.json').is_file(): continue
            inputs = json.loads((sample / 'inputs.json').read_text())
            for screen in sorted((sample / 'screen').glob('screen_*.mp4')):
                relative = str(screen.relative_to(sample))
                row = {'account': account.name, 'sample': sample.name, 'episode': inputs.get('episode_key'),
                       'sample_path': str(sample), 'source_screen': relative}
                if args.apply:
                    try: row.update(module.extract_screen_audio(sample, relative), success=True)
                    except Exception as error: row.update(success=False, error=str(error))
                rows.append(row)
    report = {'applied': args.apply, 'clips': rows,
              'created': sum(row.get('success', False) and not row.get('already_exists', False) for row in rows),
              'errors': sum(row.get('success') is False for row in rows)}
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    if report['errors']: raise SystemExit(1)


if __name__ == '__main__': main()
