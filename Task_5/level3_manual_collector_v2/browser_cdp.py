"""Minimal standard-library Chrome DevTools client for browser validation."""
import base64
import hashlib
import json
import os
import socket
import struct
from urllib.parse import urlparse


class CDP:
    def __init__(self,url):
        p=urlparse(url);self.sock=socket.create_connection((p.hostname,p.port));self.sock.settimeout(45)
        key=base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f'GET {p.path} HTTP/1.1\r\nHost: {p.netloc}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n').encode())
        self.buffer=b''
        while b'\r\n\r\n' not in self.buffer:self.buffer+=self.sock.recv(4096)
        headers,self.buffer=self.buffer.split(b'\r\n\r\n',1)
        assert b' 101 ' in headers.split(b'\r\n',1)[0],headers
        expected=base64.b64encode(hashlib.sha1((key+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest())
        assert expected.lower() in headers.lower()
        self.counter=0

    def read(self,n):
        while len(self.buffer)<n:
            chunk=self.sock.recv(max(n,4096))
            if not chunk:raise RuntimeError('Browser socket closed')
            self.buffer+=chunk
        result,self.buffer=self.buffer[:n],self.buffer[n:]
        return result

    def send(self,data,opcode=1):
        mask=os.urandom(4);n=len(data);header=bytes([128|opcode])
        header+=bytes([128|n]) if n<126 else bytes([128|126])+struct.pack('!H',n) if n<65536 else bytes([128|127])+struct.pack('!Q',n)
        self.sock.sendall(header+mask+bytes(b^mask[i%4] for i,b in enumerate(data)))

    def message(self):
        chunks=[]
        while True:
            first,second=self.read(2);n=second&127
            if n==126:n=struct.unpack('!H',self.read(2))[0]
            elif n==127:n=struct.unpack('!Q',self.read(8))[0]
            mask=self.read(4) if second&128 else None;data=self.read(n)
            if mask:data=bytes(b^mask[i%4] for i,b in enumerate(data))
            op=first&15
            if op==9:self.send(data,10);continue
            if op==8:raise RuntimeError('Browser socket closed')
            if op in [0,1]:chunks.append(data)
            if first&128 and chunks:return json.loads(b''.join(chunks))

    def call(self,method,params=None):
        self.counter+=1;identifier=self.counter
        self.send(json.dumps({'id':identifier,'method':method,'params':params or {}}).encode())
        while True:
            data=self.message()
            if data.get('id')==identifier:
                if 'error' in data:raise RuntimeError(data['error'])
                return data.get('result',{})

    def evaluate(self,script):
        result=self.call('Runtime.evaluate',{'expression':script,'awaitPromise':True,'returnByValue':True})
        if 'exceptionDetails' in result:raise RuntimeError(result['exceptionDetails'])
        return result.get('result',{}).get('value')
