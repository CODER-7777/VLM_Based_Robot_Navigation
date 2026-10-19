"""Serve only the portable review dashboard on local loopback."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8894)
    args=parser.parse_args()
    root=Path(__file__).resolve().parent/'dist'
    handler=partial(SimpleHTTPRequestHandler,directory=str(root))
    server=ThreadingHTTPServer(('127.0.0.1',args.port),handler)
    print(f'RxR Route & Object Studio: http://127.0.0.1:{args.port}',flush=True)
    server.serve_forever()
