"""Check authentication, contributor isolation and byte-preserving uploads.

These tests use a tiny mock collector, not people or real screen/microphone input.
"""
from http.client import HTTPConnection
from http.client import HTTPSConnection
import json
from pathlib import Path
import secrets
import socket
import sys
import ssl
import subprocess
import tempfile
import threading
import time
import unittest
from urllib.parse import urlencode
from gateway import Accounts, Gateway, configuration, load_settings

MOCK='''from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--port',type=int);a=p.parse_args()
root=Path(__file__).resolve().parent;user=json.loads((root/'campus_owner.json').read_text())['username']
state={'session_id':'sessions/'+user+'/test001','active':False,'processing':False,'actions':0,'username':user}
class H(BaseHTTPRequestHandler):
 def send(self,v):
  b=json.dumps(v).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
 def do_GET(self):self.send(state)
 def do_POST(self):
  b=self.rfile.read(int(self.headers.get('Content-Length','0')))
  if self.path.startswith('/api/upload'):
   (root/'uploaded.bin').write_bytes(b);self.send({'stored_bytes':len(b),'owner':user});return
  data=json.loads(b or b'{}')
  if self.path=='/api/start':state.update(active=True,annotator=data['annotator'])
  if self.path=='/api/action':state['actions']+=1
  if self.path=='/api/reset':state['active']=False
  self.send(state)
 def log_message(self,*a):pass
ThreadingHTTPServer(('127.0.0.1',a.port),H).serve_forever()
'''


class GatewayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='task5-campus-tests-')
        root=Path(cls.temp.name);template=root/'template';(template/'web').mkdir(parents=True)
        (template/'collector.py').write_text(MOCK)
        (template/'presentation_cases.py').write_text('')
        (template/'sample_case.json').write_text('{}')
        # Find a small contiguous free range without using production worker ports.
        with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
        cls.cfg=dict(bind='127.0.0.1',port=0,public_origin='',allowed_networks=['127.0.0.1/32'],
                     data_root=str(root/'data'),template_root=str(template),backend_python=sys.executable,
                     worker_port_start=port,max_workers=2,max_upload_bytes=1024*1024,minimum_free_bytes=0)
        cls.server=Gateway(cls.cfg,dev=True);cls.port=cls.server.server_address[1]
        cls.origin=f'http://127.0.0.1:{cls.port}';cls.cfg['public_origin']=cls.origin
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.password=secrets.token_urlsafe(20)
        for user in ['alice','bob','charlie']:cls.server.accounts.add(user,cls.password)
        cls.tokens={}
        for user in ['alice','bob','charlie']:
            status,headers,_=cls.request('/auth/login','POST',urlencode({'username':user,'password':cls.password}).encode(),ctype='application/x-www-form-urlencoded')
            assert status==303;cls.tokens[user]=headers['Set-Cookie'].split(';')[0]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.server.pool.close();cls.temp.cleanup()

    @classmethod
    def request(cls,path,method='GET',body=None,user=None,origin=None,ctype='application/json',extra=None):
        con=HTTPConnection('127.0.0.1',cls.port,timeout=10)
        headers={'Host':f'127.0.0.1:{cls.port}','Content-Type':ctype}
        if method=='POST':headers['Origin']=cls.origin if origin is None else origin
        if user:headers['Cookie']=cls.tokens[user]
        headers.update(extra or {})
        try:
            con.request(method,path,body=body,headers=headers);response=con.getresponse()
            return response.status,dict(response.getheaders()),response.read()
        finally:con.close()

    @classmethod
    def ready(cls,user):
        for _ in range(50):
            status,_,raw=cls.request('/api/state',user=user)
            if status==200:return json.loads(raw)
            time.sleep(.05)
        raise AssertionError('Worker not ready')

    def test_01_auth_and_origin(self):
        self.assertEqual(self.request('/api/state')[0],401)
        self.assertEqual(self.request('/auth/login','POST',b'username=alice&password=wrong',origin='https://evil.example')[0],403)
        self.assertEqual(self.request('/api/state',user='alice',extra={'Host':'evil.example'})[0],400)
        _,headers,_=self.request('/auth/login','POST',urlencode({'username':'alice','password':self.password}).encode())
        self.assertIn('HttpOnly',headers['Set-Cookie']);self.assertIn('SameSite=Strict',headers['Set-Cookie'])

    def test_02_independent_concurrent_workers(self):
        first=self.ready('alice');second=self.ready('bob')
        self.assertNotEqual(first['session_id'],second['session_id'])
        _,_,raw=self.request('/api/start','POST',b'{"annotator":"bob"}',user='alice')
        self.assertEqual(json.loads(raw)['annotator'],'alice')
        self.request('/api/action','POST',b'{}',user='alice')
        self.assertEqual(self.ready('alice')['actions'],1);self.assertEqual(self.ready('bob')['actions'],0)
        self.assertEqual(self.request('/api/state',user='charlie')[0],503)

    def test_03_upload_and_access_isolation(self):
        self.assertEqual(self.request('/api/media?session=sessions/bob/test001&file=navigation.mp4',user='alice')[0],403)
        self.assertEqual(self.request('/api/load','POST',b'{"session_id":"sessions/bob/test001"}',user='alice')[0],403)
        self.assertEqual(self.request('/api/upload?session=sessions/bob/test001','POST',b'private',user='alice')[0],403)
        payload=secrets.token_bytes(128*1024)
        status,_,raw=self.request('/api/upload?kind=voice&session=sessions/alice/test001','POST',payload,user='alice',ctype='audio/mp4')
        self.assertEqual(status,200);self.assertEqual(json.loads(raw)['owner'],'alice')
        root=Path(self.cfg['data_root'])/'contributors'
        self.assertEqual((root/'alice/uploaded.bin').read_bytes(),payload)
        self.assertFalse((root/'bob/uploaded.bin').exists())

    def test_04_logout_preserves_active_sample(self):
        self.assertEqual(self.request('/auth/logout','POST',b'{}',user='alice')[0],409)
        self.assertTrue(self.ready('alice')['active'])
        self.request('/api/reset','POST',b'{}',user='alice')
        status,headers,_=self.request('/auth/logout','POST',b'{}',user='alice')
        self.assertEqual(status,200);self.assertIn('Max-Age=0',headers['Set-Cookie'])
        self.assertEqual(self.request('/api/state',user='alice')[0],401)

    def test_05_network_allowlist_ignores_forged_forwarded_ip(self):
        original=self.server.networks
        import ipaddress
        self.server.networks=[ipaddress.ip_network('192.0.2.0/24')]
        try:self.assertEqual(self.request('/',extra={'X-Forwarded-For':'192.0.2.1'})[0],403)
        finally:self.server.networks=original

    def test_06_production_denies_incomplete_config(self):
        p=Path(self.temp.name)/'invalid.json';p.write_text(json.dumps(self.cfg))
        with self.assertRaises(ValueError):configuration(p,dev=False)

    def test_06b_paths_follow_config_folder(self):
        root=Path(self.temp.name)/'portable';root.mkdir()
        path=root/'config.json'
        path.write_text(json.dumps({'data_root':'data','tls_certificate':'certificates/server/collector.crt','tls_private_key':'certificates/server/collector.key','template_root':'template'}))
        cfg=load_settings(path)
        self.assertEqual(cfg['data_root'],str(root/'data'))
        self.assertEqual(cfg['tls_certificate'],str(root/'certificates/server/collector.crt'))
        self.assertEqual(cfg['tls_private_key'],str(root/'certificates/server/collector.key'))
        self.assertEqual(cfg['template_root'],str(root/'template'))

    def test_07_tls_and_secure_login_cookie(self):
        root=Path(self.temp.name)/'tls';root.mkdir()
        cert=root/'test.crt';key=root/'test.key'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes',
            '-keyout',str(key),'-out',str(cert),'-days','1','-subj','/CN=localhost',
            '-addext','subjectAltName=IP:127.0.0.1,DNS:localhost'],
            check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        cfg={**self.cfg,'port':0,'data_root':str(root/'data'),
             'tls_certificate':str(cert),'tls_private_key':str(key)}
        server=Gateway(cfg,dev=False);port=server.server_address[1]
        cfg['public_origin']=f'https://127.0.0.1:{port}'
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(cert,key);server.enable_tls(context)
        server.accounts.add('tlsuser',self.password)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        client=HTTPSConnection('127.0.0.1',port,context=ssl.create_default_context(cafile=str(cert)),timeout=5)
        # Idle browser preconnections and incomplete TLS must not block login.
        idle=socket.create_connection(('127.0.0.1',port),timeout=2)
        partial=socket.create_connection(('127.0.0.1',port),timeout=2)
        partial.sendall(b'\x16\x03\x01')
        try:
            body=urlencode({'username':'tlsuser','password':self.password})
            client.request('POST','/auth/login',body,headers={'Origin':cfg['public_origin'],'Content-Type':'application/x-www-form-urlencoded'})
            response=client.getresponse();response.read()
            self.assertEqual(response.status,303)
            self.assertIn('Secure',response.getheader('Set-Cookie'))
            self.assertIn('HttpOnly',response.getheader('Set-Cookie'))
        finally:
            idle.close();partial.close();client.close();server.shutdown();server.server_close();server.pool.close()

    def test_08_only_owner_created_accounts_can_sign_in(self):
        page=self.request('/')[2]
        self.assertIn(b'/auth/login',page)
        self.assertNotIn(b'/register',page)
        self.assertNotIn(b'invitation',page)
        with self.server.accounts.connect() as db:before=db.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        for user in [None,'bob']:
            self.assertEqual(self.request('/register',user=user)[0],404)
            self.assertEqual(self.request('/auth/register','POST',b'username=unapproved&password=not-a-real-password',user=user)[0],404)
        with self.server.accounts.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM users').fetchone()[0],before)
        self.server.accounts.add('owner_created',self.password)
        status,headers,_=self.request('/auth/login','POST',urlencode({'username':'owner_created','password':self.password}).encode())
        self.assertEqual(status,303)
        token=headers['Set-Cookie'].split(';')[0]
        status,_,raw=self.request('/auth/me',extra={'Cookie':token})
        self.assertEqual(status,200);self.assertEqual(json.loads(raw)['username'],'owner_created')
        self.assertNotIn('owner_created',self.server.pool.workers)
        self.assertFalse((Path(self.cfg['data_root'])/'contributors/owner_created').exists())

    def test_09_login_attempts_are_limited(self):
        form=urlencode({'username':'unknown_person','password':'wrong-password'}).encode()
        for _ in range(10):self.assertEqual(self.request('/auth/login','POST',form)[0],401)
        self.assertEqual(self.request('/auth/login','POST',form)[0],429)
        self.assertFalse(self.server.accounts.authenticate('unknown_person',self.password))


class OwnerAccountTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='task5-owner-account-tests-')
        self.accounts=Accounts(self.temp.name);self.password=secrets.token_urlsafe(20)

    def tearDown(self):self.temp.cleanup()

    def test_validation_and_duplicate_creation_preserve_existing_account(self):
        with self.assertRaises(ValueError):self.accounts.add('../bad',self.password)
        with self.assertRaises(ValueError):self.accounts.add('short','short')
        self.accounts.add('returning',self.password)
        with self.assertRaises(ValueError):self.accounts.add('returning',secrets.token_urlsafe(20))
        self.assertTrue(self.accounts.authenticate('returning',self.password))

    def test_password_reset_preserves_recordings_and_revokes_old_tokens(self):
        self.accounts.add('returning',self.password)
        recording=Path(self.temp.name)/'contributors/returning/sessions/returning/example/manifest.json'
        recording.parent.mkdir(parents=True);recording.write_text('{"existing_recording":true}')
        token=self.accounts.login('returning',3600);new_password=secrets.token_urlsafe(20)
        self.accounts.reset_password('returning',new_password)
        self.assertIsNone(self.accounts.user(token))
        self.assertFalse(self.accounts.authenticate('returning',self.password))
        self.assertTrue(self.accounts.authenticate('returning',new_password))
        self.assertEqual(recording.read_text(),'{"existing_recording":true}')

    def test_legacy_invites_disabled_without_account_or_session_loss(self):
        self.accounts.add('existing',self.password);token=self.accounts.login('existing',3600)
        with self.accounts.connect() as db:
            db.execute('CREATE TABLE invites(code_hash TEXT PRIMARY KEY,enabled INTEGER NOT NULL)')
            db.execute('INSERT INTO invites VALUES(?,1)',('obsolete-code-hash',))
        migrated=Accounts(self.temp.name)
        self.assertTrue(migrated.authenticate('existing',self.password))
        self.assertEqual(migrated.user(token),'existing')
        with migrated.connect() as db:self.assertEqual(db.execute('SELECT enabled FROM invites').fetchone()[0],0)


if __name__=='__main__':unittest.main(verbosity=2)
