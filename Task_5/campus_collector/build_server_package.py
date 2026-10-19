"""Build an explicit server-only package; never export the private CA key or data."""
import argparse
import os
from pathlib import Path
import tarfile

ROOT=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include-tls',action='store_true',help='Include the server TLS key/certificate and public CA certificate. Keep this package private.')
    args=parser.parse_args()
    names=['gateway.py','run_tmux.py','start_campus_collector.sh','backfill_screen_audio.py','campus.css',
           'campus-client.js','campus-recovery.js','README.md','IT_REQUEST.md','PARTICIPANT_GUIDE.md','CLOUDFLARE_NOTES.md',
           'config.production.example.json','config.private-ca.example.json','config.dev.example.json',
           'template/collector.py','template/presentation_cases.py','template/sample_case.json','template/collection_selection.json',
           'template/web/index.html','template/web/app.js','template/web/style.css']
    if args.include_tls:names+=['certificates/server/collector.crt','certificates/server/collector.key','certificates/share/rootCA.crt']
    for name in names:
        path=ROOT/name
        if not path.is_file() or path.is_symlink():raise SystemExit('Missing or linked package input: '+name)
    os.umask(0o077)
    directory=ROOT/'packages';directory.mkdir(mode=0o700,exist_ok=True)
    destination=directory/('campus_server_private_tls.tar.gz' if args.include_tls else 'campus_server_code.tar.gz')
    # Opening through a new temporary file avoids inheriting permissive old modes.
    temporary=destination.with_suffix(destination.suffix+'.tmp')
    with temporary.open('xb') as stream:
        with tarfile.open(fileobj=stream,mode='w:gz') as archive:
            for name in names:archive.add(ROOT/name,arcname='campus_collector/'+name,recursive=False)
    temporary.replace(destination);destination.chmod(0o600)
    print(destination)
    print('Contains server key; transfer only to the study server. Do not send to contributors.' if args.include_tls else 'Code only. No keys, account database, recordings or live config included.')


if __name__=='__main__':main()
