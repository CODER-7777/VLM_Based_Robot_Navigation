"""Create private HTTPS material inside this Task_5 collector directory.

The CA key is password-encrypted and never goes into the server/share package.
No trust store, network setting, or running service is changed by this script.
"""
import argparse
import ipaddress
import os
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server-ip',default='172.26.186.222')
    parser.add_argument('--ca-password-file',type=Path,help='Optional existing private password file for automation; otherwise OpenSSL prompts interactively.')
    args=parser.parse_args()
    address=str(ipaddress.IPv4Address(args.server_ip))
    openssl=shutil.which('openssl')
    if not openssl:raise SystemExit('Install OpenSSL 3 before running this script.')
    version=subprocess.check_output([openssl,'version'],text=True)
    if not version.startswith('OpenSSL 3.'):raise SystemExit('This helper requires OpenSSL 3.')
    if args.ca_password_file:
        args.ca_password_file=args.ca_password_file.resolve(strict=True)
        if args.ca_password_file.stat().st_mode&0o077:raise SystemExit('Password file must be owner-only (chmod 600).')
        if len(args.ca_password_file.read_bytes().strip())<12:raise SystemExit('Use a CA password of at least 12 characters.')
    base=ROOT/'certificates'
    if base.exists():raise SystemExit('certificates/ already exists. Existing keys are preserved; do not regenerate them for a website update.')
    os.umask(0o077)
    authority=base/'authority';server=base/'server';share=base/'share'
    for folder in [authority,server,share]:folder.mkdir(parents=True,mode=0o700)
    key=authority/'rootCA.key';cert=share/'rootCA.crt'
    common=[openssl,'req','-x509','-sha256']
    root_command=common+['-newkey','rsa:3072','-days','1825','-keyout',str(key),'-out',str(cert),
        '-subj','/CN=Task5 Collector Private Root CA',
        '-addext','basicConstraints=critical,CA:TRUE,pathlen:0',
        '-addext','keyUsage=critical,keyCertSign,cRLSign']
    leaf_command=common+['-newkey','rsa:2048','-noenc','-days','365',
        '-CA',str(cert),'-CAkey',str(key),'-keyout',str(server/'collector.key'),'-out',str(server/'collector.crt'),
        '-subj','/CN='+address,'-addext','subjectAltName=IP:'+address,
        '-addext','basicConstraints=critical,CA:FALSE',
        '-addext','keyUsage=critical,digitalSignature,keyEncipherment',
        '-addext','extendedKeyUsage=serverAuth']
    if args.ca_password_file:
        root_command+=['-passout','file:'+str(args.ca_password_file)]
        leaf_command+=['-passin','file:'+str(args.ca_password_file)]
    print('Create a strong password for the private CA key; enter it again when signing the server certificate.',flush=True)
    try:
        subprocess.run(root_command,check=True)
        subprocess.run(leaf_command,check=True)
        subprocess.run([openssl,'verify','-CAfile',str(cert),'-purpose','sslserver','-verify_ip',address,str(server/'collector.crt')],check=True)
    except subprocess.CalledProcessError:
        raise SystemExit('Certificate preparation stopped. Partial files remain in certificates/ for review; no service was changed.')
    (share/'READ_ME.txt').write_text('Task_5 collector trust certificate\n\nVerify rootCA.crt with the study owner before installing it as a trusted authority.\nIt enables browser trust; IITK-only access is enforced separately on the server.\nNever distribute any .key file. See Task_5/CAMPUS_COLLECTION_START_HERE.md.\n')
    subprocess.run([openssl,'x509','-in',str(cert),'-noout','-fingerprint','-sha256'],check=True)
    print('Created:',base)
    print('Contributor file: certificates/share/rootCA.crt')
    print('Server files: certificates/server/collector.crt and collector.key')
    print('Private issuing key: certificates/authority/rootCA.key (keep on this laptop)')
    print('No trust store was modified and no website was started.')


if __name__=='__main__':main()
