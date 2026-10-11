"""Capture real browser PBR room frames; no navigation actions or model edits."""
from urllib.request import Request, urlopen
from urllib.parse import urlsplit
from pathlib import Path
import base64
import json
import os
import socket
import struct
import time

ROOT = Path(__file__).resolve().parent
DEBUG = 'http://127.0.0.1:9240'
PANORAMA = 'http://127.0.0.1:8769'


class DevTools:
    def __init__(self, tab=None):
        if tab is None:
            with urlopen(Request(DEBUG + '/json/new?about:blank', method='PUT')) as response:
                tab = json.load(response)
        self.tab = tab
        address = urlsplit(self.tab['webSocketDebuggerUrl'])
        self.socket = socket.create_connection((address.hostname, address.port))
        self.socket.settimeout(180)
        key = base64.b64encode(os.urandom(16)).decode()
        self.socket.sendall(('GET ' + address.path + ' HTTP/1.1\r\nHost: ' + address.netloc +
                             '\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: ' + key +
                             '\r\nSec-WebSocket-Version: 13\r\nOrigin: http://localhost:9240\r\n\r\n').encode())
        header = b''
        while not header.endswith(b'\r\n\r\n'):
            header += self.socket.recv(1)
        assert header.split(b' ')[1] == b'101', header
        self.sequence = 0
        self.errors = []

    def exact(self, n):
        data = bytearray()
        while len(data) < n:
            part = self.socket.recv(n - len(data))
            if not part:
                raise RuntimeError('Browser connection closed')
            data.extend(part)
        return bytes(data)

    def receive(self):
        header = self.exact(2)
        size = header[1] & 127
        if size == 126:
            size = struct.unpack('!H', self.exact(2))[0]
        elif size == 127:
            size = struct.unpack('!Q', self.exact(8))[0]
        mask = self.exact(4) if header[1] & 128 else None
        data = self.exact(size)
        if mask:
            data = bytes(v ^ mask[i % 4] for i, v in enumerate(data))
        if header[0] & 15 == 8:
            raise RuntimeError('Browser websocket closed')
        return json.loads(data)

    def call(self, method, params=None):
        self.sequence += 1
        data = json.dumps({'id': self.sequence, 'method': method, 'params': params or {}}).encode()
        mask = os.urandom(4)
        if len(data) < 126:
            header = bytes([0x81, 0x80 | len(data)])
        elif len(data) < 65536:
            header = bytes([0x81, 0x80 | 126]) + struct.pack('!H', len(data))
        else:
            header = bytes([0x81, 0x80 | 127]) + struct.pack('!Q', len(data))
        self.socket.sendall(header + mask + bytes(v ^ mask[i % 4] for i, v in enumerate(data)))
        while True:
            response = self.receive()
            if response.get('method') == 'Runtime.exceptionThrown':
                self.errors.append(response['params'])
            if response.get('id') == self.sequence:
                if 'error' in response:
                    raise RuntimeError(response['error'])
                return response.get('result', {})

    def js(self, expression):
        result = self.call('Runtime.evaluate', {'expression': expression, 'returnByValue': True, 'awaitPromise': True})
        if 'exceptionDetails' in result:
            raise RuntimeError(result['exceptionDetails'])
        return result.get('result', {}).get('value')


if __name__ == '__main__':
    with urlopen(PANORAMA + '/config.json', timeout=30) as response:
        config = json.load(response)
    with urlopen('http://127.0.0.1:8767/tour-info', timeout=30) as response:
        live_info = json.load(response)
    assert live_info['revision'] == config['revision'], 'Published room differs from panorama source'
    assert live_info['validation']['scene_sha256'] == config['source_sha256']
    browser = DevTools()
    browser.call('Page.enable')
    browser.call('Runtime.enable')
    browser.call('Emulation.setDeviceMetricsOverride', {'width': 1200, 'height': 900, 'deviceScaleFactor': 1, 'mobile': False})
    browser.call('Page.navigate', {'url': 'http://127.0.0.1:8767/home-tour'})
    started = time.monotonic()
    for attempt in range(600):
        time.sleep(1)
        state = browser.js('window.homeTour ? {ready:window.homeTour.ready,error:window.homeTour.error,status:document.getElementById("status")?.textContent} : {}')
        if attempt % 15 == 0:
            print('LOAD', attempt, state, flush=True)
        if state.get('error'):
            raise RuntimeError(state['error'])
        if state.get('ready'):
            break
    else:
        raise RuntimeError('Kitchen did not finish loading')
    assert browser.js('Boolean(window.homeTourRenderer && window.homeTourScene && window.homeTourCamera)')
    report = {'source': config['after_source'], 'source_mtime_ns': config['source_mtime_ns'],
              'source_sha256': config['source_sha256'], 'revision': config['revision'],
              'capture_time_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'renderer': 'Existing direct-PBR kitchen renderer; identical lighting and unchanged geometry',
              'toaster': browser.js('({parts:window.homeTour.toasterParts,originalPbr:window.homeTour.originalPbr})'),
              'views': []}
    for view in config['views']:
        for index, packet in enumerate(view['capture_packets']):
            canvas = browser.js('window.homeTour.capturePhoto(' + json.dumps(packet) + ')')
            image = base64.b64decode(canvas.split(',', 1)[1])
            with urlopen(Request(PANORAMA + '/capture/%s/%d' % (view['id'], index), data=image, headers={'Content-Type': 'image/png'}), timeout=60) as response:
                assert response.status == 200
            print('FACE', view['id'], index, len(image), flush=True)
        with urlopen(Request(PANORAMA + '/assemble/' + view['id'], data=b'{}', headers={'Content-Type': 'application/json'}), timeout=120) as response:
            assert response.status == 200
        report['views'].append({'id': view['id'], 'position_raw': view['position_raw'], 'packets': view['capture_packets']})
        print('PANORAMA_READY', view['id'], flush=True)
    report['browser_errors'] = browser.errors
    report['elapsed_s'] = round(time.monotonic() - started, 2)
    (ROOT / 'capture_report.json').write_text(json.dumps(report, indent=2))
    browser.call('Page.navigate', {'url': PANORAMA + '/'})
    print('CAPTURE_COMPLETE', report['elapsed_s'], flush=True)
