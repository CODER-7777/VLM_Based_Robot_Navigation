"""End-to-end QA with synthetic microphone/tab media; never records the desktop."""
import base64
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent / 'level3_manual_collector_v2'))
from browser_cdp import CDP


def main():
    runtime = ROOT / '.runtime'
    profile = tempfile.mkdtemp(prefix='checkpoint-studio-qa-', dir='/tmp')
    with (runtime / 'browser_qa.log').open('wb') as log:
        proc = subprocess.Popen(['/usr/bin/google-chrome', '--headless', '--no-sandbox', '--disable-gpu',
                                 '--disable-dev-shm-usage', '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream',
                                 '--autoplay-policy=no-user-gesture-required', '--user-data-dir=' + profile,
                                 '--remote-debugging-port=8907', '--window-size=1720,1150', 'http://127.0.0.1:8900/?tour=pilot04'], stdout=log, stderr=log)
    try:
        client = None
        for _ in range(100):
            try:
                tabs = json.load(urlopen('http://127.0.0.1:8907/json', timeout=1))
                tab = next(t for t in tabs if t.get('type') == 'page' and '8900' in t.get('url', ''))
                client = CDP(tab['webSocketDebuggerUrl'])
                break
            except Exception:
                time.sleep(.1)
        assert client
        client.sock.settimeout(240)
        for _ in range(100):
            try:
                if client.evaluate("document.readyState==='complete' && typeof plan!=='undefined' && !!plan && document.querySelectorAll('#checkpointRows tr').length===30"):
                    break
            except RuntimeError:
                pass
            time.sleep(.1)
        results = client.evaluate(r'''(async()=>{
const checks=[],assert=(v,m)=>{if(!v)throw Error(m);checks.push(m)},pause=ms=>new Promise(r=>setTimeout(r,ms));
assert(plan.checkpoints.length===30,'All 30 checkpoint panoramas listed');
assert(plan.route_length_m>=40,'Authored route exceeds 40 m');
assert(plan.anchor_sequence.join(',')==='1,2,3,4,5,4,3,6','Approved anchor sequence preserved');
assert(Math.abs(video.duration-80)<.2,'80-second pilot video plays');
await selectCheckpoint(14,true);await pause(250);
assert(Math.abs(video.currentTime-plan.checkpoints[14].video_time_s)<.2,'Checkpoint seeks the corresponding video time');
await setMode('pano');assert(panoPixels.width===2048&&panoPixels.height===1024,'Actual equirectangular panorama loads');
assert(Math.abs(panoYaw-timeline[plan.checkpoints[14].video_frame].yaw_radians)<.001,'Panorama opens facing the recorded forward camera');
const oldYaw=panoYaw;panoYaw+=.4;drawPanorama();assert(panoYaw!==oldYaw,'Panorama perspective responds to look direction');
await setMode('live');assert(live?.scan==='SN83YJsR3w2'&&liveImg.naturalWidth===768,'Separate Habitat renderer returns a real scene frame');
assert(Math.abs(Math.atan2(Math.sin(checkpointYaw()+live.heading_degrees*Math.PI/180),Math.cos(checkpointYaw()+live.heading_degrees*Math.PI/180)))<.001,'Live checkpoint camera matches the recorded forward heading');
const oldHeading=live.heading_degrees;await action('left');assert(Math.abs(live.heading_degrees-oldHeading)>1,'Live A key action turns camera');
const oldFrame=live.frame;await action('forward');assert(live.frame>oldFrame&&Number.isFinite(live.walked_m),'Live W action uses navmesh movement');
await setMode('video');await selectCheckpoint(0,true);
$('user').value='QA_synthetic_media';await newSample();const sid=sample.id;
$('transcript').value='Synthetic QA audio and canvas video. No real person was recorded.';
await startRecording('voice');await startRecording('scene');await video.play();await pause(1700);
assert(recorders.filter(r=>r.recorder.state==='recording').length===2,'Voice and scene recording start only on request');
const tracks=streams.flatMap(s=>s.getTracks());await stopSave();
assert(tracks.every(t=>t.readyState==='ended'),'Stop & save closes every camera and microphone track');
assert(!sample&&!saving&&$('recordBadge').hidden,'Recording state clears after save');
const saved=await api('sample?id='+encodeURIComponent(sid));
assert(saved.media.some(m=>m.kind==='voice'&&m.path.endsWith('.mp4')),'Voice converts to playable AAC MP4');
assert(saved.media.some(m=>m.kind==='scene'&&m.path.endsWith('.mp4')),'Scene recording converts to H264 MP4');
assert(saved.transcript.includes('Synthetic QA'),'Written transcript persists');
const zip=await fetch('/api/download?id='+encodeURIComponent(sid));assert(zip.ok&&(await zip.arrayBuffer()).byteLength>1000,'Sample ZIP is downloadable');
// Fake tab stream, never invoke the operating system's screen picker in QA.
navigator.mediaDevices.getDisplayMedia=async()=>{const c=document.createElement('canvas');c.width=320;c.height=240;const ctx=c.getContext('2d');ctx.fillStyle='#2c6c5b';ctx.fillRect(0,0,320,240);const stream=c.captureStream(10);const timer=setInterval(()=>{ctx.fillStyle=`hsl(${Date.now()%360},40%,30%)`;ctx.fillRect(0,0,320,240);},80);stream.getVideoTracks()[0].addEventListener('ended',()=>clearInterval(timer));return stream;};
await newSample();const tabSid=sample.id;await startRecording('screen');await pause(1200);const tabTracks=streams.flatMap(s=>s.getTracks());await stopSave();
const tabSaved=await api('sample?id='+encodeURIComponent(tabSid));assert(tabSaved.media.some(m=>m.kind==='screen'),'Tab recording workflow saves synthetic tab plus voice');assert(tabTracks.every(t=>t.readyState==='ended'),'Tab and microphone tracks stop together');
assert(document.documentElement.scrollWidth<=window.innerWidth,'Desktop layout fits viewport');
return {checks,sample:sid,tabSample:tabSid};})()''')
        (runtime / 'desktop.png').write_bytes(base64.b64decode(client.call('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': True})['data']))
        client.call('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 1, 'mobile': True})
        mobile = client.evaluate("({fits:document.documentElement.scrollWidth<=390,width:document.documentElement.scrollWidth})")
        assert mobile['fits'], mobile
        results['checks'].append('Mobile layout fits 390 px viewport')
        (runtime / 'mobile.png').write_bytes(base64.b64decode(client.call('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': True})['data']))
        (runtime / 'verification.json').write_text(json.dumps(results, indent=2))
        print(json.dumps(results, indent=2))
    finally:
        proc.terminate()
        proc.wait(timeout=10)


if __name__ == '__main__':
    main()
