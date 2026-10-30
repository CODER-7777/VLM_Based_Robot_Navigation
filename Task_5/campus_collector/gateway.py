"""Campus-only HTTPS entry point with authenticated, isolated collector workers.

Production refuses to start without TLS, an explicit client-network allowlist,
and an exact public origin. --dev binds loopback for administrator testing only.
"""
from __future__ import annotations
import argparse
from collections import defaultdict, deque
from dataclasses import dataclass
import getpass
import hashlib
import hmac
from html import escape
from http import cookies
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import sqlite3
import ssl
import subprocess
import sys
import threading
import time
from urllib.parse import parse_qs, urlencode, urlsplit
from admin_tools import Administration, AdminStore, AdminError

ROOT=Path(__file__).resolve().parent
USERNAME=re.compile(r'^[A-Za-z0-9_-]{1,48}$')
GET_PATHS={'/','/app.js','/style.css','/api/case','/api/environments','/api/state',
           '/api/frame','/api/sessions','/api/jobs','/api/videos','/api/media','/api/download','/api/guidance'}
POST_PATHS={'/api/start','/api/action','/api/annotate','/api/delete','/api/load','/api/select','/api/reset','/api/upload'}


class Accounts:
    def __init__(self, root):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.path=self.root/'accounts.sqlite3'
        with self.connect() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS users(
                username TEXT PRIMARY KEY,salt BLOB NOT NULL,digest BLOB NOT NULL,enabled INTEGER NOT NULL DEFAULT 1);
                CREATE TABLE IF NOT EXISTS logins(
                token_hash TEXT PRIMARY KEY,username TEXT NOT NULL,expires REAL NOT NULL);''')
            # Disable legacy invitation records without touching accounts or recordings.
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='invites'").fetchone():
                db.execute('UPDATE invites SET enabled=0')
        self.path.chmod(0o600)

    def connect(self):
        return sqlite3.connect(self.path,timeout=20)

    @staticmethod
    def digest(password,salt):
        return hashlib.scrypt(password.encode(),salt=salt,n=32768,r=8,p=1,maxmem=128*1024*1024)

    @staticmethod
    def validate(username,password):
        if not isinstance(username,str) or not USERNAME.fullmatch(username):raise ValueError('Use 1–48 letters, digits, underscores or hyphens.')
        if not isinstance(password,str) or not 12<=len(password)<=256:raise ValueError('Use a password of 12–256 characters.')

    def add(self,username,password):
        self.validate(username,password)
        salt=secrets.token_bytes(16);digest=self.digest(password,salt)
        with self.connect() as db:
            try:db.execute('INSERT INTO users(username,salt,digest) VALUES(?,?,?)',(username,salt,digest))
            except sqlite3.IntegrityError:raise ValueError('Contributor ID already exists. Use --reset-password to change its password.') from None

    def authenticate(self,username,password):
        with self.connect() as db:row=db.execute('SELECT salt,digest,enabled FROM users WHERE username=?',(username,)).fetchone()
        salt=row[0] if row else b'fixed-dummy-salt!'
        candidate=self.digest(password,salt)
        return bool(row and row[2] and hmac.compare_digest(candidate,row[1]))

    def login(self,username,ttl):
        token=secrets.token_urlsafe(32)
        with self.connect() as db:
            db.execute('DELETE FROM logins WHERE expires < ?',(time.time(),))
            db.execute('INSERT INTO logins VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),username,time.time()+ttl))
        return token

    def user(self,token):
        with self.connect() as db:
            row=db.execute('SELECT l.username FROM logins l JOIN users u ON u.username=l.username WHERE token_hash=? AND expires>? AND enabled=1',
                           (hashlib.sha256(token.encode()).hexdigest(),time.time())).fetchone()
        return row[0] if row else None

    def revoke(self,token):
        with self.connect() as db:db.execute('DELETE FROM logins WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),))

    def disable(self,username):
        with self.connect() as db:
            db.execute('UPDATE users SET enabled=0 WHERE username=?',(username,))
            db.execute('DELETE FROM logins WHERE username=?',(username,))

    def reset_password(self,username,password):
        self.validate(username,password)
        salt=secrets.token_bytes(16);digest=self.digest(password,salt)
        with self.connect() as db:
            result=db.execute('UPDATE users SET salt=?,digest=? WHERE username=?',(salt,digest,username))
            if not result.rowcount:raise ValueError('Contributor ID does not exist.')
            db.execute('DELETE FROM logins WHERE username=?',(username,))


@dataclass
class Worker:
    username: str
    port: int
    process: subprocess.Popen
    last_seen: float
    inflight: int = 0


class WorkerPool:
    def __init__(self,cfg):
        self.cfg=cfg;self.lock=threading.RLock();self.workers={};self.administration=None
        self.root=Path(cfg['data_root'])/'contributors';self.root.mkdir(parents=True,exist_ok=True,mode=0o700)

    def state(self,w):
        con=HTTPConnection('127.0.0.1',w.port,timeout=2)
        try:
            con.request('GET','/api/state');response=con.getresponse()
            return json.loads(response.read()) if response.status==200 else None
        except (OSError,ValueError):return None
        finally:con.close()

    def get(self,username):
        with self.lock:
            for name,w in list(self.workers.items()):
                if w.process.poll() is not None:self.workers.pop(name)
                elif not w.inflight and time.monotonic()-w.last_seen>self.cfg.get('idle_seconds',600):
                    state=self.state(w)
                    if state and not state.get('active') and not state.get('processing'):
                        w.process.terminate();w.process.wait(timeout=10);self.workers.pop(name)
            if username in self.workers:
                w=self.workers[username];w.last_seen=time.monotonic();return w
            if len(self.workers)>=self.cfg['max_workers']:return None
            folder=self.root/username;folder.mkdir(exist_ok=True,mode=0o700)
            # Copy application files only; never another contributor's recordings.
            template=Path(self.cfg['template_root'])
            for name in ['collector.py','presentation_cases.py','sample_case.json']:
                shutil.copy2(template/name,folder/name)
            selection = template/'collection_selection.json'
            if selection.is_file():
                value=json.loads(selection.read_text())
                if self.administration:value=self.administration.worker_selection(username,value)
                (folder/selection.name).write_text(json.dumps(value,indent=2)+'\n')
            shutil.copytree(template/'web',folder/'web',dirs_exist_ok=True)
            (folder/'campus_owner.json').write_text(json.dumps({'username':username})+'\n')
            occupied={w.port for w in self.workers.values()}
            port=None
            for candidate in range(self.cfg['worker_port_start'],self.cfg['worker_port_start']+self.cfg['max_workers']):
                if candidate in occupied:continue
                with socket.socket() as s:
                    try:s.bind(('127.0.0.1',candidate))
                    except OSError:continue
                port=candidate;break
            if port is None:raise RuntimeError('Worker ports are occupied; administrator review required.')
            env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='0',OMP_NUM_THREADS='2',PYTHONDONTWRITEBYTECODE='1')
            with (folder/'worker.log').open('ab') as log:
                proc=subprocess.Popen([self.cfg['backend_python'],'-u','-B',str(folder/'collector.py'),'--port',str(port)],
                    cwd=folder,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log)
            w=Worker(username,port,proc,time.monotonic());self.workers[username]=w;return w

    def release(self,username):
        with self.lock:
            w=self.workers.get(username)
            if not w:return True
            if w.inflight:return False
            state=self.state(w)
            if not state or state.get('active') or state.get('processing'):return False
            w.process.terminate();w.process.wait(timeout=10);self.workers.pop(username);return True

    def close(self):
        for w in list(self.workers.values()):
            if w.process.poll() is None:w.process.terminate()
        for w in list(self.workers.values()):
            try:w.process.wait(timeout=15)
            except subprocess.TimeoutExpired:w.process.kill()


class Gateway(ThreadingHTTPServer):
    daemon_threads=True
    request_queue_size=128

    def enable_tls(self, context):
        # Never negotiate TLS in the accept loop: a browser preconnection can
        # otherwise block every participant before Handler.setup runs.
        self.socket=context.wrap_socket(self.socket,server_side=True,do_handshake_on_connect=False)

    def process_request_thread(self, request, client_address):
        if isinstance(request, ssl.SSLSocket):
            try:
                request.settimeout(10)
                request.do_handshake()
            except (OSError, ssl.SSLError):
                self.shutdown_request(request)
                return
        super().process_request_thread(request,client_address)

    def __init__(self,cfg,dev=False):
        self.cfg=cfg;self.dev=dev;self.accounts=Accounts(cfg['data_root']);self.pool=WorkerPool(cfg)
        self.admin=Administration(cfg,self.accounts,self.pool);self.pool.administration=self.admin
        self.networks=[ipaddress.ip_network(n,strict=False) for n in cfg['allowed_networks']]
        self.attempts=defaultdict(deque);self.auth_lock=threading.Lock();self.auth_slots=threading.BoundedSemaphore(4)
        super().__init__((cfg['bind'],cfg['port']),Handler)


LOGIN='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>IITK research collection · Sign in</title><link rel="stylesheet" href="/campus.css"><body class="campus-login">
<main><p class="eyebrow">RESEARCH DATA COLLECTION</p><h1>Record a navigation demonstration.</h1>
<p>Connect to the approved IITK network and sign in with the contributor ID and password supplied by the study owner.</p>
<p class="auth-error" role="alert">ERROR</p>
<form action="/auth/login" method="post"><label>Contributor ID<input name="username" autocomplete="username" required maxlength="48"></label>
<label>Password<input name="password" type="password" autocomplete="current-password" required maxlength="256"></label><button>Sign in</button></form>
<p class="auth-help">Forgot your password? Contact the study owner. Use a separate study password; your IITK CC and SSH passwords are not needed.</p>
<p class="notice">You choose when to share your microphone and screen. Your navigation, voice clips, video and corrected transcripts are saved on the research server under your contributor ID. Review the study instructions before recording.</p></main></body></html>'''


def auth_page(template,error=''):
    return template.replace('ERROR',escape(error))


WAIT='''<!doctype html><html lang="en"><meta charset="utf-8"><meta http-equiv="refresh" content="4"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/campus.css"><title>Preparing your collector</title><body class="campus-login"><main><p class="eyebrow">RESEARCH COLLECTION</p><h1>MESSAGE</h1><p>This page checks again automatically. Each active contributor has an independent simulator and recording folder.</p></main></body></html>'''


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup();self.connection.settimeout(60)

    protocol_version='HTTP/1.1'
    def log_message(self,fmt,*args):
        # Do not log cookies, passwords, request bodies or upload URLs.
        print(time.strftime('%Y-%m-%d %H:%M:%S'),self.client_address[0],self.command,urlsplit(self.path).path,flush=True)

    def finish_headers(self,mime,length,extra=None):
        self.send_header('Content-Type',mime);self.send_header('Content-Length',str(length))
        self.send_header('Cache-Control','no-store');self.send_header('Connection','close')
        self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','same-origin')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Permissions-Policy','microphone=(self), display-capture=(self), fullscreen=(self), camera=()')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'")
        if not self.server.dev:self.send_header('Strict-Transport-Security','max-age=31536000')
        for k,v in (extra or {}).items():self.send_header(k,v)
        self.end_headers();self.close_connection=True

    def reply(self,status,value,mime='application/json',extra=None):
        body=value if isinstance(value,bytes) else (value.encode() if isinstance(value,str) else json.dumps(value).encode())
        self.send_response(status);self.finish_headers(mime,len(body),extra)
        try:self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError):pass

    def error(self,status,message):return self.reply(status,{'error':message})

    def permitted(self):
        peer=ipaddress.ip_address(self.client_address[0])
        if not any(peer in n for n in self.server.networks):
            self.error(403,'This collector is available only from the approved IITK network.');return False
        expected=urlsplit(self.server.cfg['public_origin']).netloc
        if self.headers.get('Host')!=expected:
            self.error(400,'Use the approved collection website address.');return False
        return True

    def token(self):
        try:
            jar=cookies.SimpleCookie(self.headers.get('Cookie',''))
            return jar.get('task5_session').value if jar.get('task5_session') else ''
        except cookies.CookieError:return ''

    def user(self):return self.server.accounts.user(self.token())

    def cookie(self,value,expire=False):
        return 'task5_session='+value+'; Path=/; HttpOnly; SameSite=Strict; Max-Age='+('0' if expire else str(self.server.cfg.get('login_seconds',28800)))+('' if self.server.dev else '; Secure')

    def content_length(self,limit):
        lengths=self.headers.get_all('Content-Length',[])
        if self.headers.get('Transfer-Encoding') or len(lengths)>1:raise ValueError('Ambiguous request framing is not accepted.')
        n=int(lengths[0]) if lengths else 0
        if n<0:raise ValueError('Invalid body size.')
        if n>limit:raise OverflowError('Request exceeds the configured upload limit.')
        return n

    def do_GET(self):
        if not self.permitted():return
        path=urlsplit(self.path).path
        if path=='/campus.css':return self.reply(200,(ROOT/'campus.css').read_bytes(),'text/css')
        user=self.user()
        if path=='/auth/me':return self.reply(200 if user else 401,{'username':user,'role':self.server.admin.store.role(user)})
        if path.startswith('/admin') or path.startswith('/api/admin/'):
            return self.admin_get(path,user)
        if path=='/register':return self.error(404,'Accounts are supplied by the study owner.')
        if path=='/login':
            if user:return self.reply(303,b'',extra={'Location':'/admin' if self.server.admin.store.role(user)=='admin' else '/'})
            return self.reply(200,auth_page(LOGIN),'text/html; charset=utf-8')
        if not user:
            if path=='/':return self.reply(200,auth_page(LOGIN),'text/html; charset=utf-8')
            return self.error(401,'Sign in to the collection website.')
        if path=='/campus-recovery.js':return self.reply(200,(ROOT/'campus-recovery.js').read_bytes(),'text/javascript')
        if path=='/campus-client.js':return self.reply(200,(ROOT/'campus-client.js').read_bytes(),'text/javascript')
        if path not in GET_PATHS:return self.error(404,'Not found')
        params=parse_qs(urlsplit(self.path).query)
        if params.get('session') and not self.own_session(user,params['session'][0]):return self.error(403,'Recording is not owned by this contributor.')
        target=self.path
        if path=='/api/sessions':target=path+'?'+urlencode({'annotator':user})
        return self.proxy(user,target)

    @staticmethod
    def own_session(user,session):
        return bool(re.fullmatch(r'sessions/'+re.escape(user)+r'/[A-Za-z0-9_.-]+',session))

    def do_POST(self):
        if not self.permitted():return
        if self.headers.get('Origin')!=self.server.cfg['public_origin']:
            return self.error(403,'Same-origin browser requests are required.')
        path=urlsplit(self.path).path
        if path=='/auth/register':return self.error(404,'Accounts are supplied by the study owner.')
        try:
            n=self.content_length(self.server.cfg.get('max_upload_bytes',300*1024*1024) if path=='/api/upload' else 65536)
            if path=='/auth/login':
                if n>4096:return self.error(413,'Account request too large.')
                return self.login(n)
            user=self.user()
            if not user:return self.error(401,'Sign in before collecting data.')
            if path.startswith('/api/admin/'):
                if self.server.admin.store.role(user)!='admin':return self.error(403,'Administrator access is required.')
                if n>65536:return self.error(413,'Administrator request too large.')
                data=json.loads(self.rfile.read(n) or b'{}')
                return self.reply(200,self.server.admin.mutate(user,path.removeprefix('/api/admin/'),data))
            if path=='/auth/logout':
                if not self.server.pool.release(user):return self.error(409,'STOP & save and wait for all uploads/MP4 processing before signing out.')
                self.server.accounts.revoke(self.token());return self.reply(200,{'signed_out':True},extra={'Set-Cookie':self.cookie('',True)})
            if path not in POST_PATHS:return self.error(404,'Not found')
            params=parse_qs(urlsplit(self.path).query)
            if params.get('session') and not self.own_session(user,params['session'][0]):return self.error(403,'Recording belongs to another contributor.')
            if path=='/api/upload':
                if shutil.disk_usage(self.server.cfg['data_root']).free<self.server.cfg.get('minimum_free_bytes',2*1024**3):
                    return self.error(507,'Server storage is low. Keep the browser source recording and contact the study administrator.')
                return self.proxy(user,self.path,stream_length=n)
            payload=json.loads(self.rfile.read(n) or b'{}')
            if not isinstance(payload,dict):raise ValueError('Expected a JSON object.')
            if path=='/api/start':payload['annotator']=user
            for k in ['session_id','confirm_session']:
                if k in payload and not self.own_session(user,payload[k]):return self.error(403,'Recording belongs to another contributor.')
            return self.proxy(user,self.path,body=json.dumps(payload).encode())
        except OverflowError as e:self.error(413,str(e))
        except AdminError as e:self.error(e.status,str(e))
        except (ValueError,KeyError) as e:self.error(400,str(e))

    def admin_get(self,path,user):
        if not user:
            if path in ['/admin','/admin/']:
                return self.reply(303,b'',extra={'Location':'/login'})
            return self.error(401,'Sign in to use study administration.')
        if self.server.admin.store.role(user)!='admin':return self.error(403,'Administrator access is required.')
        assets={'/admin':('index.html','text/html; charset=utf-8'),'/admin/':('index.html','text/html; charset=utf-8'),
                '/admin/app.js':('app.js','text/javascript'),'/admin/style.css':('style.css','text/css')}
        if path in assets:
            name,mime=assets[path]
            return self.reply(200,(ROOT/'admin_web'/name).read_bytes(),mime)
        try:
            if path=='/api/admin/state':return self.reply(200,self.server.admin.overview(user))
            if path in ['/api/admin/catalog.csv','/api/admin/catalog.md']:
                markdown=path.endswith('.md');name='private_instruction_catalog.'+('md' if markdown else 'csv')
                return self.reply(200,self.server.admin.export(markdown),
                                  'text/markdown; charset=utf-8' if markdown else 'text/csv; charset=utf-8',
                                  {'Content-Disposition':'attachment; filename="'+name+'"'})
        except (OSError,ValueError,KeyError):return self.error(503,'The instruction catalog needs administrator review; check the server source configuration.')
        return self.error(404,'Administrator route not found.')

    def auth_attempt(self,username):
        ip=self.client_address[0];now=time.monotonic();key=('pair',ip,username)
        with self.server.auth_lock:
            for old,q in list(self.server.attempts.items()):
                while q and now-q[0]>600:q.popleft()
                if not q:self.server.attempts.pop(old,None)
            if len(self.server.attempts)>4096:
                self.error(429,'Account traffic limit reached; try again later.');return None
            pair=self.server.attempts[key];shared=self.server.attempts[('ip',ip)]
            if len(pair)>=10 or len(shared)>=100:
                self.reply(429,auth_page(LOGIN,'Too many attempts. Please try again later.'),'text/html; charset=utf-8');return None
            pair.append(now);shared.append(now)
        return key

    def login(self,n):
        fields=parse_qs(self.rfile.read(n).decode())
        username=fields.get('username',[''])[0];password=fields.get('password',[''])[0]
        key=self.auth_attempt(username[:48])
        if key is None:return
        if len(password)>256 or not USERNAME.fullmatch(username):
            return self.reply(401,auth_page(LOGIN,'Invalid contributor ID or password.'),'text/html; charset=utf-8')
        if not self.server.auth_slots.acquire(blocking=False):return self.reply(429,auth_page(LOGIN,'Sign-in is busy. Please retry shortly.'),'text/html; charset=utf-8')
        try:valid=self.server.accounts.authenticate(username,password)
        finally:self.server.auth_slots.release()
        if not valid:
            return self.reply(401,auth_page(LOGIN,'Invalid contributor ID or password.'),'text/html; charset=utf-8')
        with self.server.auth_lock:self.server.attempts.pop(key,None)
        token=self.server.accounts.login(username,self.server.cfg.get('login_seconds',28800))
        return self.reply(303,b'',extra={'Set-Cookie':self.cookie(token),'Location':'/admin' if self.server.admin.store.role(username)=='admin' else '/'})

    def proxy(self,user,target,body=None,stream_length=None):
        assignment=self.server.admin.store.assignment(user)
        if self.server.admin.store.role(user)!='admin' and assignment is not None and not assignment['keys']:
            return self.error(403,'No instructions are assigned yet. Ask a study administrator to assign your tasks.')
        # Take a worker lease before any admin may release/reconfigure it.
        with self.server.pool.lock:
            try:w=self.server.pool.get(user)
            except (ValueError,OSError):return self.error(503,'Your instruction assignment needs administrator review.')
            if w is not None:w.inflight+=1
        path=urlsplit(target).path
        if w is None:
            return self.reply(503,WAIT.replace('MESSAGE','All collection slots are currently in use.'),'text/html; charset=utf-8',{'Retry-After':'4'}) if path=='/' else self.error(503,'All collection slots are busy. Please wait and retry.')
        # Readiness must not allocate another renderer or reset existing state.
        if self.server.pool.state(w) is None:
            with self.server.pool.lock:w.inflight-=1
            return self.reply(503,WAIT.replace('MESSAGE','Preparing your independent simulator…'),'text/html; charset=utf-8',{'Retry-After':'4'}) if path=='/' else self.error(503,'Your simulator is starting; retry shortly.')
        con=HTTPConnection('127.0.0.1',w.port,timeout=600)
        headers_sent=False
        try:
            headers={'Host':self.headers['Host'],'Connection':'close'}
            if self.command=='POST':headers['Origin']=self.server.cfg['public_origin']
            if self.headers.get('Content-Type'):headers['Content-Type']=self.headers['Content-Type']
            if stream_length is not None:
                headers['Content-Length']=str(stream_length)
                con.putrequest(self.command,target,skip_host=True)
                for k,v in headers.items():con.putheader(k,v)
                con.endheaders();remaining=stream_length
                while remaining:
                    block=self.rfile.read(min(65536,remaining))
                    if not block:raise ConnectionError('Upload interrupted; keep the browser source recording.')
                    con.send(block);remaining-=len(block)
            else:con.request(self.command,target,body=body,headers=headers)
            response=con.getresponse();mime=response.getheader('Content-Type','application/octet-stream')
            extra={}
            if response.getheader('Content-Disposition'):extra['Content-Disposition']=response.getheader('Content-Disposition')
            if path=='/' and response.status==200:
                page=response.read().replace(b'<script src="/app.js"></script>',b'<script src="/campus-recovery.js"></script><script src="/app.js"></script>').replace(b'</body>',b'<script src="/campus-client.js"></script></body>')
                return self.reply(200,page,mime)
            length=response.getheader('Content-Length')
            if length is None:return self.reply(response.status,response.read(),mime,extra)
            self.send_response(response.status);self.finish_headers(mime,int(length),extra);headers_sent=True
            while True:
                block=response.read(65536)
                if not block:break
                self.wfile.write(block)
        except (OSError,ValueError) as e:
            # A client disconnect leaves backend files and completed uploads intact.
            if not headers_sent:
                self.error(502,'Collector connection interrupted. Keep the source recording and retry.')
            self.close_connection=True
        finally:
            con.close()
            with self.server.pool.lock:w.inflight-=1


def load_settings(path):
    path=Path(path).resolve()
    cfg=json.loads(path.read_text())
    for field in ['data_root','template_root','tls_certificate','tls_private_key']:
        if cfg.get(field):
            value=Path(cfg[field]).expanduser()
            cfg[field]=str(value if value.is_absolute() else (path.parent/value).resolve())
    return cfg


def configuration(path,dev=False):
    cfg=load_settings(path)
    cfg.setdefault('template_root',str(ROOT/'template'));cfg.setdefault('worker_port_start',9100)
    cfg.setdefault('max_workers',2);cfg.setdefault('backend_python','/home/guest-isl/rishabh/bench/envs/navila/bin/python')
    if not 1<=cfg['max_workers']<=8:raise ValueError('Set max_workers between 1 and 8 after measuring GPU capacity.')
    if dev:
        cfg['bind']='127.0.0.1';cfg['allowed_networks']=['127.0.0.1/32']
        cfg['public_origin']='http://127.0.0.1:'+str(cfg['port'])
    else:
        origin=urlsplit(cfg.get('public_origin',''))
        if origin.scheme!='https' or not origin.hostname or origin.path or origin.query or origin.fragment:raise ValueError('Configure the exact trusted HTTPS public_origin.')
        if not cfg.get('tls_certificate') or not cfg.get('tls_private_key'):raise ValueError('Trusted HTTPS certificate and private-key file paths are required.')
        if not cfg.get('allowed_networks'):raise ValueError('IITK IT must confirm allowed_networks; an empty allowlist cannot be published.')
        networks=[ipaddress.ip_network(n,strict=False) for n in cfg['allowed_networks']]
        if any(n.prefixlen==0 for n in networks):raise ValueError('An unrestricted network allowlist is not permitted.')
        if cfg['bind'] in ['0.0.0.0','::']:raise ValueError('Bind the approved campus interface explicitly.')
    return cfg


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',required=True);parser.add_argument('--dev',action='store_true')
    operations=parser.add_mutually_exclusive_group()
    operations.add_argument('--add-user');operations.add_argument('--disable-user');operations.add_argument('--reset-password')
    operations.add_argument('--grant-admin');operations.add_argument('--revoke-admin')
    parser.add_argument('--password-stdin',action='store_true')
    args=parser.parse_args();raw=load_settings(args.config)
    if args.add_user or args.disable_user or args.reset_password or args.grant_admin or args.revoke_admin:
        accounts=Accounts(raw['data_root'])
        if args.grant_admin or args.revoke_admin:
            name=args.grant_admin or args.revoke_admin
            AdminStore(accounts).set_role(name,'admin' if args.grant_admin else 'contributor')
            print('Study role updated:',name);return
        if args.disable_user:accounts.disable(args.disable_user);print('Contributor disabled:',args.disable_user);return
        password=sys.stdin.readline().rstrip('\n') if args.password_stdin else getpass.getpass('New contributor password (at least 12 characters): ')
        if not args.password_stdin and password!=getpass.getpass('Confirm new password: '):raise SystemExit('Passwords do not match.')
        if args.reset_password:
            accounts.reset_password(args.reset_password,password);print('Password reset; previous logins revoked. Recordings preserved.');return
        accounts.add(args.add_user,password);print('Contributor created:',args.add_user);return
    cfg=configuration(args.config,args.dev);server=Gateway(cfg,args.dev)
    if not args.dev:
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(cfg['tls_certificate'],cfg['tls_private_key']);server.enable_tls(context)
    print(('LOCAL ADMIN TEST ONLY: ' if args.dev else 'Campus HTTPS collector: ')+cfg['public_origin'],flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close();server.pool.close()


if __name__=='__main__':main()
