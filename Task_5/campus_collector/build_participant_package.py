#!/usr/bin/env python3
"""Build the common participant ZIP from an explicit public-file list only."""
import argparse
import datetime as dt
import hashlib
from pathlib import Path
import re
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT.parent / 'IITK_Dashboard_Participant_Pack.zip')
    parser.add_argument('--without-image', action='store_true', help='Build without the optional generated poster.')
    args = parser.parse_args()
    certificate = ROOT / 'certificates/share/rootCA.crt'
    guide = ROOT / 'PARTICIPANT_GUIDE.md'
    reasoning = ROOT / 'REASONING_TEMPLATE.md'
    inputs = [guide, certificate, reasoning]
    poster = ROOT / 'participant_assets/QUICK_START.png'
    if not args.without_image:
        inputs.append(poster)
    for path in inputs:
        if not path.is_file() or path.is_symlink():
            raise SystemExit('Missing or linked participant input: ' + str(path))
    # Shared instructions must never contain the private assignment roster.
    for path in [guide, reasoning]:
        text = path.read_text()
        if re.search(r'(?im)^\s*(?:Current assignments\s*:|\|\s*Account\s*\|)', text):
            raise SystemExit('Remove the private assignment roster from shared instructions: ' + path.name)
        if re.search(r'/home/[^\s`]+', text):
            raise SystemExit('Remove private server directory paths from shared instructions: ' + path.name)
    digest = hashlib.sha256(certificate.read_bytes()).hexdigest()
    if digest not in guide.read_text():
        raise SystemExit('Update the guide with the actual public certificate checksum before packaging.')
    if b'PRIVATE KEY' in certificate.read_bytes():
        raise SystemExit('Participant certificate input must contain no private key.')
    files = {'README.md': guide.read_bytes(), 'README.txt': guide.read_bytes(),
             'rootCA.crt': certificate.read_bytes(),
             'REASONING_TEMPLATE.txt': reasoning.read_bytes()}
    if not args.without_image:
        files['QUICK_START.png'] = poster.read_bytes()
    destination = args.out.resolve()
    if destination.is_relative_to(ROOT / 'certificates'):
        raise SystemExit('Save participant packages outside the certificate directory.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        backups = ROOT / 'packages'
        backups.mkdir(parents=True, exist_ok=True)
        stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        shutil.copy2(destination, backups / ('participant_pack_before_' + stamp + '.zip'))
    temporary = destination.with_name('.' + destination.name + '.tmp')
    try:
        with temporary.open('xb') as stream:
            with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
                for name, payload in files.items():
                    info = zipfile.ZipInfo(name)
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    archive.writestr(info, payload)
        with zipfile.ZipFile(temporary) as archive:
            assert set(archive.namelist()) == set(files)
            assert archive.testzip() is None
            assert archive.read('rootCA.crt') == certificate.read_bytes()
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    print(destination)
    print('Contents:', ', '.join(files))
    print('Public certificate SHA-256:', digest)
    print('No passwords, private keys, server configuration or recordings included.')


if __name__ == '__main__':
    main()
