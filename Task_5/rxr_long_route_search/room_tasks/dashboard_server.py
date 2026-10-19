"""Serve the local review and relay only its inspection API over an SSH tunnel."""
import argparse
import functools
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen

ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=8890)
ap.add_argument('--upstream',default='http://127.0.0.1:8892')
args=ap.parse_args();ROOT=Path(__file__).resolve().parent.parent


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control','no-store' if self.path.endswith(('.html','.js','.json','.css')) else 'no-cache')
        super().end_headers()

    def relay(self):
        route=self.path.split('?',1)[0].removeprefix('/room_tasks/api/')
        allowed={'health','select','state','step','jump','props','look','action'}
        if route not in allowed:return self.send_error(404)
        data=None
        if self.command=='POST':
            length=int(self.headers.get('Content-Length','0'))
            if length>32768:return self.send_error(413)
            data=self.rfile.read(length)
        try:
            with urlopen(Request(args.upstream+'/'+route,data=data,method=self.command,
                                 headers={'Content-Type':'application/json'}),timeout=190) as response:
                body=response.read();status=response.status
        except HTTPError as error:body=error.read();status=error.code
        except (URLError,TimeoutError,OSError):
            body=b'{"error":"The 3D inspection connection is unavailable. Images and trajectory maps remain available; reconnect the review SSH tunnel."}';status=503
        self.send_response(status);self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(body)));self.end_headers()
        try:self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError):pass

    def do_GET(self):
        if self.path.startswith('/room_tasks/api/'):return self.relay()
        if self.path=='/':self.path='/room_tasks/review.html'
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith('/room_tasks/api/'):return self.relay()
        return self.send_error(405)


if __name__=='__main__':
    handler=functools.partial(Handler,directory=str(ROOT))
    print(f'RxR dashboard http://127.0.0.1:{args.port}/room_tasks/review.html',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),handler).serve_forever()
