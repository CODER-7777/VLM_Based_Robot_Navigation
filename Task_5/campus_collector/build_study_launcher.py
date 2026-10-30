"""Build standalone local launchers; no installation or deployment on the server."""
import argparse
from datetime import datetime
import hashlib
import os
from pathlib import Path
import shutil
import struct
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent
EXPECTED_CA_HASH = '5d5d81ac9d7a884bf579c3cf9cc478e5b66a907b26a3356b88d4f66baf27b445'
MAC_MINIMUM = '13.0'
MAC_PACKAGE_VERSION = '1.9.0'
MAC_START_HELP = '''Mac: start here

1. Extract the ZIP using Finder. Keep all extracted files together.
2. First time only: open Terminal and type sh followed by a space.
   Drag OpenDashboard.command from this folder into Terminal.
   Press Enter. Type yes if the launcher asks for first-start approval.
3. Later: double-click OpenDashboard.command. Sign in in Chrome/Edge.
   Keep Terminal open until uploads finish.

Only use the ZIP received from the study owner. First start checks the
native executable against its bundled SHA-256. With your confirmation,
it removes download quarantine from that executable and this command
file only. It does not disable Gatekeeper or approve other applications.
Keep the launcher folder beside OpenDashboard.command. This package has
no .app bundle; use OpenDashboard.command.

If macOS reports "Operation not permitted" while approving:
Check System Settings > Privacy & Security > Files & Folders > Terminal
and allow Downloads Folder access, if listed.
Quit and reopen Terminal after changing a permission, then retry.

Still failing? Send the owner your macOS version and chip from About This
Mac, and the Terminal error only. Do not share passwords or browser links.
Requires macOS 13 or later; supports Intel and Apple Silicon.
'''


def macos_bundle(binaries):
    """Use plain files so a blocked enclosing .app cannot veto a tool launch."""
    command = b'''#!/bin/sh
set -eu
study_dir="$(CDPATH= cd -P "$(dirname "$0")" && pwd)"
study_resources="$study_dir/launcher"
case "$(/usr/bin/uname -m)" in
  arm64) study_binary=OpenDashboard-arm64; study_expected=__ARM64_HASH__ ;;
  x86_64) study_binary=OpenDashboard-amd64; study_expected=__AMD64_HASH__ ;;
  *) printf '%s\\n' 'This launcher supports Apple Silicon and Intel Macs only.'; exit 1 ;;
esac
study_path="$study_resources/bin/$study_binary"
case "${1:-}" in
  ''|--approve) ;;
  *) printf '%s\\n' 'Use no arguments, or --approve for the first start.'; exit 1 ;;
esac
if ! printf '%s  %s\\n' "$study_expected" "$study_path" | /usr/bin/shasum -a 256 -c -; then
  printf '%s\\n' 'Executable verification failed. Obtain a fresh ZIP from the study owner.'
  exit 1
fi
study_needs_approval=false
for study_file in "$study_path" "$study_dir/$(basename "$0")"; do
  if /usr/bin/xattr -p com.apple.quarantine "$study_file" >/dev/null 2>&1; then
    study_needs_approval=true
  fi
done
if [ "${1:-}" = --approve ] || [ "$study_needs_approval" = true ]; then
  printf '%s\\n' 'First-start approval for this study launcher only.'
  printf '%s\\n' 'This removes download quarantine from the verified executable and this command file.'
  printf '%s\\n' 'It does not disable Gatekeeper globally. Continue only if this ZIP came from the study owner.'
  printf '%s' 'Type yes to approve: '
  if ! IFS= read -r study_answer; then
    printf '\\n%s\\n' 'Open Terminal, type sh and a space, drag this command file into Terminal, then press Enter.'
    exit 1
  fi
  if [ "$study_answer" != yes ]; then
    printf '%s\\n' 'Cancelled. No quarantine attributes were changed.'
    exit 1
  fi
  for study_file in "$study_path" "$study_dir/$(basename "$0")"; do
    if /usr/bin/xattr -p com.apple.quarantine "$study_file" >/dev/null 2>&1; then
      if ! /usr/bin/xattr -d com.apple.quarantine "$study_file"; then
        printf '\\n%s\\n' 'macOS refused the requested first-start approval. The dashboard has not started.'
        printf '%s\\n' 'Check System Settings > Privacy & Security > Files & Folders > Terminal > Downloads Folder, if listed.'
        printf '%s\\n' 'Quit and reopen Terminal after changing a permission, then retry this command.'
        printf '%s\\n' 'If these options are missing or locked, send the owner your macOS version and the error.'
        exit 1
      fi
    fi
  done
fi
printf '%s\\n' 'Keep this Terminal window open until recording uploads finish.'
exec "$study_path"
'''
    for arch in ['arm64', 'amd64']:
        command = command.replace(('__' + arch.upper() + '_HASH__').encode(),
                                  hashlib.sha256(binaries[arch].read_bytes()).hexdigest().encode())
    return {'OpenDashboard.command': command,
            'MAC_START_HERE.txt': MAC_START_HELP.encode(),
            'VERSION.txt': (MAC_PACKAGE_VERSION + '\n').encode(),
            **{'launcher/bin/OpenDashboard-' + arch: binary.read_bytes()
               for arch, binary in binaries.items()}}


def verify_macos_files(files):
    assert not any(part.endswith('.app') for name in files for part in Path(name).parts), 'Mac tools must not be nested inside an app bundle'
    assert files['VERSION.txt'].decode().strip() == MAC_PACKAGE_VERSION
    for arch, cpu in [('arm64', 0x0100000c), ('amd64', 0x01000007)]:
        value = files['launcher/bin/OpenDashboard-' + arch]
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
    for name in ['OpenDashboard.command']:
        subprocess.run(['sh', '-n'], input=files[name], check=True)
        for arch in ['arm64', 'amd64']:
            expected = hashlib.sha256(files['launcher/bin/OpenDashboard-' + arch]).hexdigest().encode()
            assert expected in files[name], 'First-start executable checksum is stale'


def write_archive(destination, files, executables, built_at):
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        # Explicit directories preserve the launcher's extraction permissions.
        directories = {str(parent) + '/' for name in files
                       for parent in Path(name).parents if str(parent) != '.'}
        for name in sorted(directories) + list(files):
            directory = name.endswith('/')
            item = zipfile.ZipInfo(name, date_time=built_at)
            item.compress_type = zipfile.ZIP_DEFLATED
            item.create_system = 3
            mode = 0o40755 if directory else (0o100755 if name in executables else 0o100644)
            item.external_attr = mode << 16 | (0x10 if directory else 0)
            archive.writestr(item, b'' if directory else files[name])
    destination.chmod(0o600)
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        assert {item.filename for item in archive.infolist() if not item.is_dir()} == set(files)
        assert all((archive.getinfo(name).external_attr >> 16) & 0o111 for name in executables)


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
        files = (macos_bundle(binaries) if target == 'macos'
                 else {filename: binaries['amd64'].read_bytes()})
        if target == 'macos':
            verify_macos_files(files)
        files.update({'README.txt': (ROOT / 'STUDY_LAUNCHER_GUIDE.md').read_bytes(),
                      'REASONING_TEMPLATE.txt': (ROOT / 'REASONING_TEMPLATE.md').read_bytes()})
        if target == 'macos':
            recording_steps = files['README.txt'].replace(
                b'**IITK Study Launcher.app** (Mac)', b'**OpenDashboard.command** (Mac)')
            files['README.txt'] = MAC_START_HELP.encode() + b'\nRecording steps\n\n' + recording_steps
        executables = ({'launcher/bin/OpenDashboard-arm64', 'launcher/bin/OpenDashboard-amd64',
                        'OpenDashboard.command'}
                       if target == 'macos' else {filename})
        built_at = datetime.now().timetuple()[:6]
        write_archive(destination, files, executables, built_at)
        with zipfile.ZipFile(destination) as archive:
            if target == 'macos':
                verify_macos_files({name: archive.read(name) for name in archive.namelist()})
                assert all((archive.getinfo(name).external_attr >> 16) & 0o111 for name in executables)
        print(destination)
        print('SHA-256:', hashlib.sha256(destination.read_bytes()).hexdigest())
        admin_destination = ROOT.parent / ('IITK_Admin_Launcher_' + label + '.zip')
        admin_files = dict(files)
        admin_files['README.txt'] = (ROOT / 'ADMIN_LAUNCHER_QUICK_START.md').read_bytes()
        if target == 'macos':
            admin_files['README.txt'] = MAC_START_HELP.encode() + b'\nAdministration\n\n' + admin_files['README.txt']
        admin_files['RECORDING_STEPS.txt'] = files['README.txt']
        write_archive(admin_destination, admin_files, executables, built_at)
        print(admin_destination)
        print('SHA-256:', hashlib.sha256(admin_destination.read_bytes()).hexdigest())
    print('Cross-built Windows/macOS outputs require target-device acceptance testing. The macOS tools are not Developer-ID signed or notarized.')


if __name__ == '__main__':
    main()
