"""Serve the existing repaired scene editor with its comparison panel collapsed.
The simulator and its route/object state stay in the existing upstream process.
"""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
import json
UPSTREAM='http://127.0.0.1:8776'
class Handler(BaseHTTPRequestHandler):
 def relay(self):
  if self.command=='GET' and self.path.split('?',1)[0]=='/comparisons':
   panels=[('Latest selected toaster: real photo | previous model | AtTheSpeedOf model','toaster.jpg'),('Earlier sink-counter comparisons — toaster superseded above','compare1.jpg'),('Corner counter — blue jug/vase, caddy, frogs, knife block and paper towel','compare2.jpg'),('Range counter','compare3.jpg'),('Latest toaster — additional viewing angles','toaster-novel.jpg')]
   html='<!doctype html><html><head><meta charset="utf-8"><title>All kitchen repair comparisons</title><style>body{background:#153c2c;color:#fff;font:16px sans-serif;margin:24px}a{color:#bbf7d0}img{display:block;max-width:100%;height:auto}section{margin:30px 0}</style></head><body><a href="/">Back to full scene editor</a> · <a href="/product-viewer">Rotate selected toaster with PBR lighting</a><h1>Kitchen repair comparisons</h1><p>Real photograph | previous scene | repaired scene. The latest toaster is first; the other saved object comparisons remain available below.</p><p><a href="http://localhost:8778/corner-comparisons">Latest Gaussian corner before / after and close-up views</a></p>'
   html+=''.join('<section><h2>'+title+'</h2><img src="/repair-preview/'+filename+'" alt="'+title+'"></section>' for title,filename in panels)+'</body></html>'
   payload=html.encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(payload)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(payload);return
  body=self.rfile.read(int(self.headers.get('Content-Length','0'))) if self.command=='POST' else None
  req=Request(UPSTREAM+self.path,data=body,method=self.command,headers={'Content-Type':self.headers.get('Content-Type','application/json')})
  try:
   with urlopen(req,timeout=45) as r:payload=r.read();status=r.status;ctype=r.headers.get('Content-Type','application/octet-stream')
   if self.command=='GET' and self.path.split('?',1)[0]=='/':
    html=payload.decode('utf-8');header='<h2>Habitat first-person route author</h2>';a=html.index(header)+len(header);b=html.index('<div id="source"',a);old=html[a:b]
    compact='''<p style="margin:6px 0 10px;color:#bbf7d0">Complete repaired scene · selected AtTheSpeedOf toaster installed.</p><p><a href="/comparisons" style="color:#bbf7d0;font-weight:bold">View all repaired-object comparisons — toaster, vase/jug, caddy, frogs and counter objects</a> · <a href="/product-viewer" style="color:#bbf7d0">Rotate the metallic PBR toaster</a></p><p><a href="http://localhost:8778/" style="color:#bbf7d0" target="_blank">Updated Gaussian RGB-D toaster corner</a> · <a href="http://localhost:8778/corner-comparisons" style="color:#bbf7d0" target="_blank">Gaussian before / after</a> — farther regions remain experimental; requires local port 8778 forwarding.</p><details style="margin-bottom:10px"><summary style="cursor:pointer">Repair comparisons and model notes</summary>'''+old+'</details>\n  '
    html=html[:a]+compact+html[b:];html=html.replace('<title>Habitat POV Route Author</title>','<title>Repaired kitchen — full scene editor</title>');payload=html.encode('utf-8')
   elif self.command=='GET' and self.path.split('?',1)[0]=='/scene-info':
    data=json.loads(payload);data['ui_mode']='full_editor';payload=json.dumps(data).encode()
  except HTTPError as e:status=e.code;payload=e.read();ctype=e.headers.get('Content-Type','text/plain')
  except (URLError,TimeoutError) as e:status=502;payload=('Scene editor temporarily unavailable: '+str(e)).encode();ctype='text/plain'
  self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(payload)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(payload)
 def do_GET(self):self.relay()
 def do_POST(self):self.relay()
ThreadingHTTPServer(('127.0.0.1',8774),Handler).serve_forever()
