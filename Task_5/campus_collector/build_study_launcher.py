"""Build standalone local launchers; no installation or deployment on the server."""
import argparse
from datetime import datetime
import hashlib
import os
from pathlib import Path
import plistlib
import shutil
import struct
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent
EXPECTED_CA_HASH = '5d5d81ac9d7a884bf579c3cf9cc478e5b66a907b26a3356b88d4f66baf27b445'
MAC_APP = 'IITK Study Launcher.app/Contents/'
MAC_MINIMUM = '13.0'


def macos_bundle(binaries):
    """One app bundle chooses the correct native binary without Rosetta."""
    start = b'''#!/bin/sh
set -eu
study_macos_dir="$(CDPATH= cd -P "$(dirname "$0")" && pwd)"
exec /usr/bin/open -a Terminal "$study_macos_dir/../Resources/OpenDashboard.command"
'''
    command = b'''#!/bin/sh
set -eu
study_resources="$(CDPATH= cd -P "$(dirname "$0")" && pwd)"
case "$(/usr/bin/uname -m)" in
  arm64) study_binary=OpenDashboard-arm64 ;;
  x86_64) study_binary=OpenDashboard-amd64 ;;
  *) printf '%s\\n' 'This launcher supports Apple Silicon and Intel Macs only.'; exit 1 ;;
esac
printf '%s\\n' 'Keep this Terminal window open until recording uploads finish.'
exec "$study_resources/bin/$study_binary"
'''
    info = {'CFBundleName': 'IITK Study Launcher', 'CFBundleDisplayName': 'IITK Study Launcher',
            'CFBundleIdentifier': 'org.studylauncher.navigation', 'CFBundleExecutable': 'StartStudy',
            'CFBundlePackageType': 'APPL', 'CFBundleShortVersionString': '1.6', 'CFBundleVersion': '7',
            'CFBundleSupportedPlatforms': ['MacOSX'], 'LSMinimumSystemVersion': MAC_MINIMUM,
            'LSUIElement': True}
    return {MAC_APP + 'Info.plist': plistlib.dumps(info), MAC_APP + 'PkgInfo': b'APPL????',
            MAC_APP + 'MacOS/StartStudy': start,
            MAC_APP + 'Resources/OpenDashboard.command': command,
            **{MAC_APP + 'Resources/bin/OpenDashboard-' + arch: binary.read_bytes()
               for arch, binary in binaries.items()}}


def verify_macos_files(files):
    info = plistlib.loads(files[MAC_APP + 'Info.plist'])
    assert info['CFBundleExecutable'] == 'StartStudy' and info['LSMinimumSystemVersion'] == MAC_MINIMUM
    for arch, cpu in [('arm64', 0x0100000c), ('amd64', 0x01000007)]:
        value = files[MAC_APP + 'Resources/bin/OpenDashboard-' + arch]
        magic, actual_cpu, _, filetype, commands, _, _, _ = struct.unpack_from('<8I', value)
        assert magic == 0xfeedfacf and actual_cpu == cpu and filetype == 2, 'Wrong macOS binary architecture'
        offset, minimum = 32, None
        for _ in range(commands):
            kind, size = struct.unpack_from('<2I', value, offset)
            assert size >= 8 and offset + size <= len(value)
            if kind == 0x32:  # LC_BUILD_VERSION
                platform, minimum = struct.unpack_from('<2I', value, offset + 8)
                assert platform == 1, 'Expected a macOS Mach-O binary'
            offset += size
        assert minimum is not None and minimum == 13 << 16, 'Unexpected macOS deployment target'
    for name in ['MacOS/StartStudy', 'Resources/OpenDashboard.command']:
        subprocess.run(['sh', '-n'], input=files[MAC_APP + name], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--go', type=Path)
    parser.add_argument('--target', choices=['windows', 'linux', 'macos', 'all'], default='all')
    args = parser.parse_args()
    go = args.go or shutil.which('go') or ROOT / 'packages/launcher_build_tools/go/bin/go'
    if not Path(go).is_file():
        raise SystemExit('Obtain the official Go compiler locally, then pass --go PATH. Do not install it on the study server.')
    go = str(Path(go).resolve())
    source = ROOT / 'study_launcher'
    ca = ROOT / 'certificates/share/rootCA.crt'
    value = ca.read_bytes()
    if hashlib.sha256(value).hexdigest() != EXPECTED_CA_HASH or b'PRIVATE KEY' in value:
        raise SystemExit('Unexpected public study CA; no packages were produced.')
    shutil.copyfile(ca, source / 'rootCA.crt')
    builds = ROOT / 'packages/study_launcher'
    builds.mkdir(parents=True, exist_ok=True, mode=0o700)
    env = dict(os.environ, GOTOOLCHAIN='local', GOTELEMETRY='off', GOENV='off', CGO_ENABLED='0', GOPATH=str(builds / 'go-path'),
               GOCACHE=str(builds / 'go-cache'), GOMODCACHE=str(builds / 'go-mod-cache'))
    subprocess.run([go, 'test', '-count=1', './...'], cwd=source, env=env, check=True)
    targets = ['windows', 'linux', 'macos'] if args.target == 'all' else [args.target]
    for target in targets:
        filename = 'OpenDashboard.exe' if target == 'windows' else 'OpenDashboard'
        binaries = {}
        for arch in (['arm64', 'amd64'] if target == 'macos' else ['amd64']):
            binary = (builds / target / arch / filename if target == 'macos'
                      else builds / target / filename)
            binary.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            subprocess.run([go, 'build', '-trimpath', '-buildvcs=false', '-ldflags=-s -w -buildid=', '-o', str(binary), '.'],
                           cwd=source, env=dict(env, GOOS='darwin' if target == 'macos' else target, GOARCH=arch), check=True)
            binaries[arch] = binary
        label = 'macOS' if target == 'macos' else target.title()
        destination = ROOT.parent / ('IITK_Study_Launcher_' + label + '.zip')
        files = macos_bundle(binaries) if target == 'macos' else {filename: binaries['amd64'].read_bytes()}
        if target == 'macos':
            verify_macos_files(files)
        files.update({'README.txt': (ROOT / 'STUDY_LAUNCHER_GUIDE.md').read_bytes(),
                      'REASONING_TEMPLATE.txt': (ROOT / 'REASONING_TEMPLATE.md').read_bytes()})
        executables = ({MAC_APP + 'MacOS/StartStudy', MAC_APP + 'Resources/OpenDashboard.command',
                        MAC_APP + 'Resources/bin/OpenDashboard-arm64', MAC_APP + 'Resources/bin/OpenDashboard-amd64'}
                       if target == 'macos' else {filename})
        built_at = datetime.now().timetuple()[:6]
        with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, payload in files.items():
                item = zipfile.ZipInfo(name, date_time=built_at)
                item.compress_type = zipfile.ZIP_DEFLATED
                item.create_system = 3
                item.external_attr = (0o100755 if name in executables else 0o100644) << 16
                archive.writestr(item, payload)
        destination.chmod(0o600)
        with zipfile.ZipFile(destination) as archive:
            assert archive.testzip() is None and set(archive.namelist()) == set(files)
            if target == 'macos':
                verify_macos_files({name: archive.read(name) for name in archive.namelist()})
                assert all((archive.getinfo(name).external_attr >> 16) & 0o111 for name in executables)
        print(destination)
        print('SHA-256:', hashlib.sha256(destination.read_bytes()).hexdigest())
        admin_destination = ROOT.parent / ('IITK_Admin_Launcher_' + label + '.zip')
        admin_files = dict(files)
        admin_files['README.txt'] = (ROOT / 'ADMIN_LAUNCHER_QUICK_START.md').read_bytes()
        admin_files['RECORDING_STEPS.txt'] = files['README.txt']
        with zipfile.ZipFile(admin_destination, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, payload in admin_files.items():
                item = zipfile.ZipInfo(name, date_time=built_at)
                item.compress_type = zipfile.ZIP_DEFLATED
                item.create_system = 3
                item.external_attr = (0o100755 if name in executables else 0o100644) << 16
                archive.writestr(item, payload)
        admin_destination.chmod(0o600)
        with zipfile.ZipFile(admin_destination) as archive:
            assert archive.testzip() is None and set(archive.namelist()) == set(admin_files)
        print(admin_destination)
        print('SHA-256:', hashlib.sha256(admin_destination.read_bytes()).hexdigest())
    print('Cross-built Windows/macOS outputs require target-device acceptance testing. The macOS app is not Developer-ID signed or notarized.')


if __name__ == '__main__':
    main()
