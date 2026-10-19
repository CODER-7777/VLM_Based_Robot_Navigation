"""Browser regression for picker-exits-fullscreen using synthetic media only."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'level3_manual_collector_v2'))
from browser_cdp import CDP

FIXTURE = r'''
window.fixtureCalls=[];window.captureRequests=0;window.micRequests=0;
window.fixtureTracks=[];window.recordStarts=[];window.failMic=false;
api=async(path,data)=>{if(path.startsWith('/api/sessions?'))return [];throw Error('Unexpected API '+path)};
upload=async()=>{fixtureCalls.push('upload');return {status:'synthetic'}};
caseData={default_relevant_memory_ids:[]};
$('annotator').value='synthetic_fullscreen_test';
update({active:true,finished:false,session_id:'sessions/synthetic/fullscreen',actions:0,path_length_m:0,
 elapsed_seconds:0,processing:false,media_jobs:[],videos:[],audio:[]});
const canvas=document.createElement('canvas');canvas.width=512;canvas.height=512;
window.redraw=setInterval(()=>{const c=canvas.getContext('2d');c.fillStyle='#285e42';c.fillRect(0,0,512,512)},60);
navigator.mediaDevices.getDisplayMedia=async()=>{
 if(!navigator.userActivation.isActive)throw Error('Picker requires a trusted click');
 captureRequests++;
 if(document.fullscreenElement)await document.exitFullscreen();
 const stream=canvas.captureStream(15);fixtureTracks.push(...stream.getTracks());return stream;
};
navigator.mediaDevices.getUserMedia=async()=>{
 micRequests++;if(failMic)throw Error('Synthetic microphone permission denied');
 const context=new AudioContext(),oscillator=context.createOscillator(),destination=context.createMediaStreamDestination();
 oscillator.connect(destination);oscillator.start();window.audioContexts=(window.audioContexts||[]).concat(context);
 fixtureTracks.push(...destination.stream.getTracks());return destination.stream;
};
const nativeStart=MediaRecorder.prototype.start;
MediaRecorder.prototype.start=function(...args){recordStarts.push({fullscreen:!!document.fullscreenElement});return nativeStart.apply(this,args)};
window.fixtureReady=true;
'''


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?', 1)[0]
        if path == '/':
            data = (ROOT / 'template/web/index.html').read_bytes(); mime = 'text/html'
        elif path == '/app.js':
            source = (ROOT / 'template/web/app.js').read_text()
            data = (source.rsplit('(async()=>{', 1)[0] + FIXTURE).encode(); mime = 'text/javascript'
        elif path == '/style.css':
            data = (ROOT / 'template/web/style.css').read_bytes(); mime = 'text/css'
        else:
            self.send_error(404); return
        self.send_response(200); self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data)

    def log_message(self, *args):
        pass


def main():
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    profile = tempfile.TemporaryDirectory(prefix='task5-fullscreen-browser-')
    log = (Path(profile.name) / 'browser.log').open('wb')
    origin = 'http://127.0.0.1:' + str(server.server_address[1])
    browser = subprocess.Popen([shutil.which('google-chrome'), '--headless', '--no-sandbox', '--disable-gpu',
        '--disable-dev-shm-usage', '--remote-debugging-port=0', '--user-data-dir=' + profile.name,
        '--window-size=1680,1080', '--autoplay-policy=no-user-gesture-required', origin], stdout=log, stderr=log)
    client = None
    def until(expression):
        for _ in range(100):
            try:
                if client.evaluate(expression): return
            except RuntimeError: pass
            time.sleep(.1)
        raise AssertionError('Browser condition failed: ' + expression)
    def click(selector):
        point = client.evaluate('(()=>{const e=document.querySelector(' + json.dumps(selector) + ');e.scrollIntoView({block:"center"});const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()')
        for kind in ['mousePressed', 'mouseReleased']:
            client.call('Input.dispatchMouseEvent', {'type': kind, 'button': 'left', 'clickCount': 1, **point})
    try:
        for _ in range(100):
            try:
                port = (Path(profile.name) / 'DevToolsActivePort').read_text().splitlines()[0]
                tabs = json.load(urllib.request.urlopen('http://127.0.0.1:' + port + '/json', timeout=1))
                page = next(t for t in tabs if t.get('type') == 'page' and t.get('url', '').startswith(origin))
                client = CDP(page['webSocketDebuggerUrl']); break
            except Exception: time.sleep(.1)
        assert client
        until('window.fixtureReady===true')
        click('#fullscreen'); until('!!document.fullscreenElement')
        click('#focus-screen')
        until('!!preparedScreen && $("screen-start-dialog").open && !document.fullscreenElement')
        assert client.evaluate('!screen && captureRequests===1 && micRequests===1 && recordStarts.length===0')
        click('#screen-start'); until('!!screen && !!document.fullscreenElement')
        assert client.evaluate('recordStarts.length===1 && recordStarts[0].fullscreen && captureRequests===1 && micRequests===1')
        client.evaluate('screen.recorder.stop()'); until('!screen')
        assert client.evaluate('fixtureTracks.every(t=>t.readyState==="ended")')
        client.evaluate('document.exitFullscreen()'); until('!document.fullscreenElement')

        click('#focus-screen'); until('!!preparedScreen && $("screen-start-dialog").open')
        client.evaluate('window.nativeFullscreen=document.documentElement.requestFullscreen;document.documentElement.requestFullscreen=async()=>{throw Error("Synthetic fullscreen rejection")}')
        click('#screen-start'); until('!$("screen-start-windowed").hidden')
        assert client.evaluate('!screen && !!preparedScreen && recordStarts.length===1')
        click('#screen-start-windowed'); until('!!screen')
        assert client.evaluate('recordStarts.length===2 && !recordStarts[1].fullscreen')
        client.evaluate('screen.recorder.stop();document.documentElement.requestFullscreen=nativeFullscreen'); until('!screen')
        assert client.evaluate('fixtureTracks.every(t=>t.readyState==="ended")')

        click('#focus-screen'); until('!!preparedScreen')
        click('#cancel-screen-start'); until('!preparedScreen && !screenStarting')
        assert client.evaluate('recordStarts.length===2 && fixtureTracks.every(t=>t.readyState==="ended")')

        click('#focus-screen'); until('!!preparedScreen')
        client.call('Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'Escape', 'code': 'Escape', 'windowsVirtualKeyCode': 27})
        client.call('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'Escape', 'code': 'Escape', 'windowsVirtualKeyCode': 27})
        until('!preparedScreen && !screenStarting')
        assert client.evaluate('fixtureTracks.every(t=>t.readyState==="ended")')

        client.evaluate('failMic=true'); click('#focus-screen')
        until('!screenStarting && !preparedScreen && $("message").textContent.includes("microphone permission denied")')
        assert client.evaluate('!screen && fixtureTracks.every(t=>t.readyState==="ended")')
        report = {'passed': True, 'picker_exits_fullscreen_reproduced': True,
                  'fresh_click_restores_native_fullscreen_before_recording': True,
                  'screen_and_microphone_requested_once': True, 'fullscreen_denial_waits_for_user_choice': True,
                  'windowed_fallback_verified': True, 'cancel_and_escape_release_tracks': True,
                  'microphone_denial_releases_display': True, 'human_screen_or_microphone_used': False}
        (ROOT / 'screen_fullscreen_verification.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))
    finally:
        if client:
            try: client.evaluate('clearInterval(redraw);(window.audioContexts||[]).forEach(c=>c.close())')
            except Exception: pass
            client.sock.close()
        browser.terminate()
        try: browser.wait(timeout=8)
        except subprocess.TimeoutExpired: browser.kill(); browser.wait()
        server.shutdown(); server.server_close(); log.close(); profile.cleanup()


if __name__ == '__main__': main()
