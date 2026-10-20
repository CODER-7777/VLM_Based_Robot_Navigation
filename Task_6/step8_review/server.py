#!/usr/bin/env python3
"""Step 8 review UI and optional transient Habitat backend, using Python's standard library."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import mimetypes
import os
from pathlib import Path
import re
import secrets
from urllib.parse import parse_qs, urlparse

from model import Catalog, DIMENSIONS, RATINGS, SCENE, TYPES, review_props

HERE=Path(__file__).resolve().parent

class App:
    def __init__(self,source,runtime,navigation=False,glb=None):
        self.catalog=Catalog(source);self.runtime=Path(runtime);self.runtime.mkdir(parents=True,exist_ok=True)
        key_path=self.runtime/'author_key'
        if not key_path.exists():
            key_path.write_text(secrets.token_urlsafe(32));key_path.chmod(0o600)
        self.key=key_path.read_text().strip();self.nav=None
        self.navigation=navigation;self.glb=glb;self.nav_error=None
        self.store=self.runtime/'judgments.json'
        self.records=json.loads(self.store.read_text()) if self.store.exists() else dict(reviews={},blind={},naturalness={},props={})

    def save(self):
        tmp=self.store.with_suffix('.tmp');tmp.write_text(json.dumps(self.records,indent=2,ensure_ascii=False));tmp.replace(self.store)

    def ensure_nav(self):
        if not self.navigation:raise ValueError('Navigation is unavailable in offline mode. Connect to the simulator service.')
        if self.nav is None:
            from simulator import Navigation,GLB
            self.nav=Navigation(self.catalog,self.glb or GLB)
        return self.nav

    def summary(self):
        return dict(case_count=len(self.catalog.cases),need_count=sum(bool(c['levels']['2']) for c in self.catalog.cases),
                    general_count=20,typed_count=20,naturalness_count=len(self.catalog.naturalness),
                    review_count=len(self.records['reviews']),accepted=sum(r['decision']=='pass' for r in self.records['reviews'].values()),
                    minor=sum(r['decision']=='minor' for r in self.records['reviews'].values()),
                    prop_count=len(self.catalog.props()),confirmed_props=sum(p.get('rating')=='pass' for p in self.records['props'].values()),
                    recording=False,navigation_available=self.navigation,source_fingerprint=self.catalog.fingerprint)

def handler(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass

        def author(self):
            try:
                cookie=SimpleCookie(self.headers.get('Cookie',''));return secrets.compare_digest(cookie['step8_author'].value,app.key)
            except KeyError:return False

        def send(self,value,status=200,kind='application/json; charset=utf-8',extra=None):
            body=json.dumps(value,ensure_ascii=False,allow_nan=False).encode() if kind.startswith('application/json') else value
            self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Referrer-Policy','no-referrer')
            for k,v in (extra or {}).items():self.send_header(k,v)
            self.end_headers();self.wfile.write(body)

        def require_author(self):
            if not self.author():raise PermissionError('Open the private reviewer link to use this page.')

        def do_GET(self):
            try:self.get()
            except PermissionError as e:self.send(dict(error=str(e)),403)
            except (KeyError,ValueError,FileNotFoundError,StopIteration) as e:self.send(dict(error=str(e)),404)
            except Exception as e:self.send(dict(error=f'{type(e).__name__}: {e}'),500)

        def get(self):
            url=urlparse(self.path);q=parse_qs(url.query);path=url.path
            if path=='/review' and q.get('key'):
                if not secrets.compare_digest(q['key'][0],app.key):raise PermissionError('Invalid reviewer link')
                return self.send(b'',303,'text/plain',{'Location':'/review','Set-Cookie':f'step8_author={app.key}; HttpOnly; SameSite=Strict; Path=/'})
            if path in ('/','/review','/blind','/naturalness','/props'):
                if path in ('/','/review','/props'):self.require_author()
                return self.send((HERE/'index.html').read_bytes(),kind='text/html; charset=utf-8')
            if path in ('/app.js','/style.css'):
                return self.send((HERE/path[1:]).read_bytes(),kind='text/javascript; charset=utf-8' if path.endswith('.js') else 'text/css; charset=utf-8')
            if path=='/api/health':return self.send(dict(service='task6-step8-review',recording=False,navigation=app.navigation))
            if path=='/api/nav/map':
                self.require_author();return self.send(app.ensure_nav().locator(q['token'][0]),kind='image/jpeg')
            if path=='/api/catalog':
                blind=q.get('mode',['blind'])[0]=='blind'
                if not blind:self.require_author()
                value=dict(cases=app.catalog.listing(blind),recording=False)
                if not blind:value.update(types=TYPES,dimensions=DIMENSIONS,summary=app.summary(),reviews=app.records['reviews'])
                return self.send(value)
            if path=='/api/case':
                blind=q.get('mode',['blind'])[0]=='blind'
                if not blind:self.require_author()
                return self.send(app.catalog.case(q['id'][0],blind))
            if path=='/api/props':
                self.require_author();nav=app.ensure_nav()
                return self.send(dict(props=nav.props,authored=app.catalog.props(),judgments=app.records['props']))
            if path.startswith('/api/prop-image/'):
                self.require_author();return self.send(app.ensure_nav().inspect_prop(path.rsplit('/',1)[1]),kind='image/jpeg')
            if path=='/api/export':
                self.require_author();return self.send(dict(scene=SCENE,fingerprint=app.catalog.fingerprint,**app.records),extra={'Content-Disposition':'attachment; filename="step8_judgments.json"'})
            if path=='/api/naturalness':
                return self.send(dict(requests=[dict(id=i+1,text=t) for i,t in enumerate(app.catalog.naturalness)]))
            if path.startswith('/assets/'):
                name=path.rsplit('/',1)[1]
                if not re.fullmatch(r'(memory_[A-Z][0-9]{2}|image_case(07|15|20))\.jpg|2azQ1b91cZZ_floor[01]\.png|sheet_(p|room)[0-9]+\.jpg',name):raise ValueError('Unknown review image')
                if name.startswith('sheet_'):self.require_author()
                if name.startswith(('memory_','image_')) and app.navigation:
                    body=app.ensure_nav().photo(name)
                else:
                    source=app.catalog.source if name.endswith('.png') else app.catalog.verify
                    body=(source/name).read_bytes()
                return self.send(body,kind=mimetypes.guess_type(name)[0] or 'application/octet-stream')
            raise ValueError('Unknown page')

        def do_POST(self):
            try:
                if self.headers.get('Sec-Fetch-Site')=='cross-site':raise PermissionError('Cross-site request refused')
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<=100000:raise ValueError('Invalid request size')
                data=json.loads(self.rfile.read(n));self.post(urlparse(self.path).path,data)
            except PermissionError as e:self.send(dict(error=str(e)),403)
            except (ValueError,KeyError,TypeError,StopIteration) as e:self.send(dict(error=str(e)),400)
            except Exception as e:self.send(dict(error=f'{type(e).__name__}: {e}'),500)

        def post(self,path,data):
            if path=='/api/nav/start':
                blind=data.get('mode')=='blind'
                if not blind:self.require_author()
                nav=app.ensure_nav();token=nav.initialize(data['case_id'],blind)
                return self.send(dict(token=token,recording=False,scene='v16p + five review props'))
            if path=='/api/nav/act':
                action=data.get('action','none')
                if action not in ('none','w','s','a','d','up','down','reset'):raise ValueError('Unknown navigation action')
                nav=app.ensure_nav();body,status=nav.act(data['token'],action,bool(data.get('overlays')) and self.author())
                return self.send(body,kind='image/jpeg',extra={'X-Review-State':json.dumps(status,allow_nan=False)})
            reviewer=str(data.get('reviewer','')).strip()
            if not re.fullmatch(r'[A-Za-z0-9 _.-]{1,64}',reviewer):raise ValueError('Enter a reviewer name (letters, digits, spaces, . _ -).')
            stamp=datetime.now(timezone.utc).isoformat()
            if path=='/api/review':
                self.require_author();cid=data['case_id'];case=app.catalog.by_id[cid];variant=data.get('variant','level3')
                allowed=['level3']+(['level2'] if case['levels']['2'] else [])+[f'form{i}' for i in range(len(case['forms']))]
                if variant not in allowed:raise ValueError('Unknown request variant')
                ratings=data['ratings']
                if set(ratings)!=set(DIMENSIONS) or any(v not in RATINGS for v in ratings.values()):raise ValueError('Rate every check, including not applicable where appropriate.')
                required={'instruction','navigation','alternatives','visuals'} | ({'memory','grounding'} if variant!='level2' else set())
                if any(ratings[k]=='na' for k in required):raise ValueError('Instruction, navigation, alternatives, visuals, and relevant memory checks cannot be skipped.')
                severity=['pass','minor','major','fail','unsure'];decision=max((v for v in ratings.values() if v!='na'),key=severity.index,default='unsure')
                note=str(data.get('note','')).strip()
                if decision!='pass' and not note:raise ValueError('Describe the issue or uncertainty, even if it is minor.')
                if decision=='pass' and not data.get('walked'):raise ValueError('Complete the navigation check before passing this request.')
                if decision=='pass' and any(app.records['props'].get(p['item'],{}).get('rating')!='pass' for p in review_props(case,variant)):raise ValueError('Confirm the props needed for this request on the Props page before passing.')
                key=f'{reviewer}|{cid}|{variant}';record=dict(reviewer=reviewer,case_id=cid,variant=variant,ratings=ratings,decision=decision,
                    walked=bool(data.get('walked')),note=note,updated=stamp,fingerprint=app.catalog.fingerprint)
                app.records['reviews'][key]=record;app.save();return self.send(record)
            if path=='/api/blind':
                cid=data['case_id'];case=app.catalog.by_id[cid];variant=data.get('variant','level3')
                allowed=['level3']+(['level2'] if case['levels']['2'] else [])+[f'form{i}' for i in range(len(case['forms']))]
                if variant not in allowed:raise ValueError('Unknown request variant')
                answer=str(data.get('answer','')).strip()
                if not answer:raise ValueError('Write your destination or interpretation before submitting.')
                if data.get('confidence') not in ('clear','minor','major','unsolved'):raise ValueError('Choose clarity of interpretation')
                if data.get('confidence')!='clear' and not str(data.get('note','')).strip():raise ValueError('Describe the ambiguity, even if it is small.')
                record=dict(reviewer=reviewer,case_id=cid,variant=variant,answer=answer,note=str(data.get('note','')),confidence=data.get('confidence'),updated=stamp,fingerprint=app.catalog.fingerprint)
                app.records['blind'][f'{reviewer}|{cid}|{variant}']=record;app.save();return self.send(dict(saved=True))
            if path=='/api/prop-review':
                self.require_author();item=data['item']
                if item not in {p['item'] for p in app.catalog.props()}:raise ValueError('Unknown prop')
                if data['rating'] not in ('pass','minor','major','fail','unsure'):raise ValueError('Unknown judgment')
                record=dict(item=item,reviewer=reviewer,rating=data['rating'],note=str(data.get('note','')),updated=stamp)
                app.records['props'][item]=record;app.save();return self.send(record)
            if path=='/api/naturalness':
                idx=int(data['id'])
                if not 1<=idx<=len(app.catalog.naturalness) or data['rating'] not in ('yes','odd','no'):raise ValueError('Unknown naturalness judgment')
                if data['rating']!='yes' and not str(data.get('note','')).strip():raise ValueError('Explain what sounds odd or unclear, even if it is a small issue.')
                record=dict(reviewer=reviewer,id=idx,text=app.catalog.naturalness[idx-1],rating=data['rating'],note=str(data.get('note','')),updated=stamp)
                app.records['naturalness'][f'{reviewer}|{idx}']=record;app.save();return self.send(dict(saved=True))
            raise ValueError('Unknown action')
    return Handler

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',default=str(HERE/'source'));p.add_argument('--runtime',default=str(HERE/'.runtime'))
    p.add_argument('--port',type=int,default=8896);p.add_argument('--host',default='127.0.0.1');p.add_argument('--navigation',action='store_true');p.add_argument('--glb')
    args=p.parse_args();app=App(args.source,args.runtime,args.navigation,args.glb)
    print(f'Reviewer: http://127.0.0.1:{args.port}/review?key={app.key}',flush=True)
    print(f'Blind: http://127.0.0.1:{args.port}/blind',flush=True)
    print('Navigation is transient. Only submitted review judgments are saved.',flush=True)
    HTTPServer((args.host,args.port),handler(app)).serve_forever()

if __name__=='__main__':main()
