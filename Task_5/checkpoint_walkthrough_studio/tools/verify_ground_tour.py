"""Verify the actual ground-floor tour, slow controls and selected-tour recording."""
import base64
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent/'level3_manual_collector_v2'))
from browser_cdp import CDP


def main():
    profile = Path(tempfile.mkdtemp(prefix='ground-tour-browser-', dir='/tmp'))
    with (ROOT/'.runtime/ground_browser.log').open('wb') as log:
        proc = subprocess.Popen(['/usr/bin/google-chrome','--headless','--no-sandbox','--disable-gpu',
            '--disable-dev-shm-usage','--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream',
            '--autoplay-policy=no-user-gesture-required','--user-data-dir='+str(profile),
            '--remote-debugging-port=0','--window-size=1700,1150','http://127.0.0.1:8900/?tour=ground_2az'],stdout=log,stderr=log)
    client = None
    try:
        for _ in range(120):
            try:
                port=(profile/'DevToolsActivePort').read_text().splitlines()[0]
                tabs=json.load(urlopen('http://127.0.0.1:'+port+'/json',timeout=1))
                tab=next(t for t in tabs if t.get('type')=='page' and '8900' in t.get('url',''))
                client=CDP(tab['webSocketDebuggerUrl']);break
            except Exception:
                time.sleep(.1)
        assert client
        client.sock.settimeout(240)
        for _ in range(120):
            try:
                if client.evaluate("document.readyState==='complete' && typeof plan!=='undefined' && plan?.scene==='2azQ1b91cZZ' && document.querySelectorAll('#checkpointRows tr').length===96"):
                    break
            except Exception:
                pass
            time.sleep(.1)
        result=client.evaluate(r'''(async()=>{
const checks=[],assert=(v,m)=>{if(!v)throw Error(m);checks.push(m)},pause=ms=>new Promise(r=>setTimeout(r,ms));
assert(activeTour.id==='ground_2az'&&plan.scene==='2azQ1b91cZZ','Requested ground-floor tour loads');
assert(plan.floor_level===0&&plan.room_coverage_count===20,'20 ground-floor rooms identified');
assert(document.querySelectorAll('#checkpointRows tr').length===96,'All 96 checkpoints listed');
assert(document.querySelectorAll('#roomList div').length===20,'All 20 room stops shown');
for(let i=0;i<100&&!(video.readyState>=2);i++)await pause(100);
assert(Math.abs(video.duration-878.25)<.1&&video.videoWidth===1024,'Recorded 14:38.25 video decodes at expected size');
assert($('downloadVideo').href.includes('/ground_2az/')&&$('downloadCheckpoints').href.includes('/ground_2az/'),'Downloads belong to selected tour');
assert($('turnSpeed').value==='15','Slow rotation is the default');
video.currentTime=3;await pause(250);applyTurnRate();assert(video.playbackRate===1,'Native 15-degree rotation plays at normal source speed');
$('turnSpeed').value='10';applyTurnRate();assert(Math.abs(video.playbackRate-2/3)<.001,'Very-slow setting slows stationary rotation further');
const moving=timeline.find(f=>f.event==='walk'&&f.distance_m>2);video.currentTime=moving.time_s;await pause(250);applyTurnRate();assert(video.playbackRate===1,'Walking speed is unchanged by rotation setting');
$('turnSpeed').value='15';
await selectCheckpoint(40,true);assert(Math.abs(video.currentTime-plan.checkpoints[40].video_time_s)<.1,'Checkpoint selection seeks the new tour');
await setMode('pano');assert(panoPixels.width===2048&&panoPixels.height===1024,'New checkpoint panorama renders');
await selectCheckpoint(0,true);await setMode('live');assert(live?.scan==='2azQ1b91cZZ'&&liveImg.naturalWidth===768,'Live camera loads requested ground-floor scene');
const before=live.heading_degrees;await action('left');let diff=(live.heading_degrees-before+540)%360-180;assert(Math.abs(Math.abs(diff)-1.5)<.01,'Single slow turn advances 1.5 degrees');
const start=live.heading_degrees;startHeld('left');for(let i=0;i<20;i++){startHeld('left');await pause(50)}stopHeld();await pause(250);diff=(live.heading_degrees-start+540)%360-180;assert(Math.abs(diff)<=18&&Math.abs(diff)>3,'Held/repeated turn key stays within slow turn rate');
assert(Math.abs(live.position_habitat[1]-1.5-plan.floor_y_habitat)<.4,'Live starting camera remains on ground floor');
await setMode('video');await selectCheckpoint(0,true);document.querySelector('.collect').open=true;$('user').value='QA_ground_tour';await newSample();const sid=sample.id;
$('tourSelect').value='pilot04_slow';$('tourSelect').onchange();assert(activeTour.id==='ground_2az'&&$('tourSelect').value==='ground_2az','Active sample cannot silently switch tours');
$('transcript').value='Synthetic QA: selected ground-floor tour; test recording and metadata only. No human narration recorded.';await saveNote();
await startRecording('scene');await video.play();await pause(1300);const tracks=streams.flatMap(s=>s.getTracks());await stopSave();
const saved=await api('sample?id='+encodeURIComponent(sid));assert(saved.scene==='2azQ1b91cZZ'&&saved.tour_id==='ground_2az','Sample saves correct scene and tour ID');
assert(saved.media.some(m=>m.kind==='scene')&&saved.transcript.includes('Synthetic QA'),'Scene recording and written reasoning persist');
assert(tracks.every(t=>t.readyState==='ended'),'Stop & save ends all capture tracks');
assert(document.documentElement.scrollWidth<=window.innerWidth,'Desktop tour controls fit viewport');
document.querySelector('.collect').open=false;
return {checks,sample:sid};})()''')
        (ROOT/'.runtime/ground_desktop.png').write_bytes(base64.b64decode(client.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':True})['data']))
        client.call('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
        assert client.evaluate('document.documentElement.scrollWidth<=390')
        result['checks'].append('Mobile layout fits 390px')
        (ROOT/'.runtime/ground_mobile.png').write_bytes(base64.b64decode(client.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':True})['data']))
        sample=ROOT/'sessions'/result['sample']
        manifest=json.loads((sample/'manifest.json').read_text())
        recording=sample/manifest['media'][0]['path']
        streams=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(recording)]))['streams']
        rgb=next(s for s in streams if s['codec_type']=='video')
        assert rgb['codec_name']=='h264' and (rgb['width'],rgb['height'])==(1024,682)
        assert any(s['codec_name']=='aac' for s in streams)
        result['checks'].append('New recording is H264/AAC MP4 at selected tour resolution')
        for name in ['walkthrough.mp4','checkpoint_images.zip','RECORDING_AND_REASONING_GUIDE.md']:
            with urlopen(Request('http://127.0.0.1:8900/assets/ground_2az/'+name,headers={'Range':'bytes=0-99'}),timeout=10) as res:
                assert res.status==206 and len(res.read())==100
        with zipfile.ZipFile(ROOT/'assets/ground_2az/checkpoint_images.zip') as z:
            assert z.testzip() is None and sum(n.endswith('.jpg') for n in z.namelist())==192
            assert 'RECORDING_AND_REASONING_GUIDE.md' in z.namelist() and 'reasoning_template.txt' in z.namelist()
        result['checks'].append('Video/ZIP/Markdown downloads work; ZIP contains 192 images, guide and template')
        (ROOT/'.runtime/ground_browser_verification.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result,indent=2))
    finally:
        if client:
            try:
                client.call('Browser.close')
            except Exception:
                pass
        proc.terminate();proc.wait(timeout=10)


if __name__=='__main__':
    main()
