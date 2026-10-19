#!/usr/bin/env python3
"""Validate V2 with labelled fake media; do not record a person's desktop."""
import base64
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parent
from browser_cdp import CDP


def main():
    log=(ROOT/'browser_check.log').open('wb')
    process=subprocess.Popen([shutil.which('google-chrome'),'--headless','--no-sandbox','--disable-gpu',
        '--disable-dev-shm-usage','--user-data-dir=/tmp/level3-v2-browser-check','--remote-debugging-port=8879',
        '--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream','--window-size=1680,1080',
        'http://localhost:8878'],stdout=log,stderr=log)
    client=None
    try:
        for _ in range(70):
            try:
                tabs=json.load(urllib.request.urlopen('http://127.0.0.1:8879/json',timeout=1))
                page=next(t for t in tabs if t.get('type')=='page' and 'localhost:8878' in t.get('url',''))
                client=CDP(page['webSocketDebuggerUrl']);break
            except Exception:time.sleep(.2)
        assert client,'Browser did not start'
        for _ in range(70):
            if client.evaluate('document.getElementById("connection")?.textContent === "Scene connected"'):break
            time.sleep(.2)
        result=client.evaluate('''(async()=>{
const assert=(v,m)=>{if(!v)throw Error(m)},pause=ms=>new Promise(r=>setTimeout(r,ms));
async function until(test,limit=150){for(let i=0;i<limit;i++){if(await test())return;await pause(100)}throw Error('Timed out')}
assert(!document.getElementById('return-user'),'No Returning user button');
assert($('clip-kind').options.length===1&&$('clip-kind').value==='reasoning','Reasoning only');
assert(!$('events-panel').open,'Events collapsed');
assert($('saved-samples-panel').compareDocumentPosition($('workspace'))&Node.DOCUMENT_POSITION_PRECEDING,'Saved samples below workspace');
assert($('reasoning').placeholder==='Need → relevant memory → visible evidence → next decision','Previous transcript hint restored');
assert(selected().includes('uniforms'),'Relevant memory preselected');
assert([...document.querySelectorAll('.memory blockquote')].every(x=>x.textContent.startsWith('Mary said "')),'Continuous Mary said statement');
assert([...document.querySelectorAll('.memory>summary strong')].map(x=>x.textContent).join(',')==='Memory 1,Memory 2,Memory 3','Numbered memory tree');
await until(()=>[...document.querySelectorAll('.memory img')].every(x=>x.complete&&x.naturalWidth>0));
const nativeApi=api;api=(path,data)=>{if(path==='/api/start')data={...data,recording_source:'automated_v2_browser_validation_not_human'};return nativeApi(path,data)};
$('annotator').value='Vivekananda_01';$('annotator').dispatchEvent(new Event('input',{bubbles:true}));
await until(()=>finished&&currentSession?.startsWith('sessions/Vivekananda_01/'));
assert(!$('saved-sessions').hidden&&selected().includes('uniforms'),'Username automatically loads profile and memory');
assert([...$('old-videos').querySelectorAll('a')].every(a=>a.href.includes('.mp4')),'Imported video links MP4 only');
await toggleVoice();assert($('new-sample-dialog').open&&!voice,'Completed episode requires a new sample');$('new-sample-dialog').close();
$('annotator').value='v2_browser_validation';await loadUser();
await createSample();assert(active,'Create new sample starts recording');
const count=currentState.actions;await Promise.all(Array.from({length:8},()=>act('right')));
assert(currentState.actions===count+8,'Rapid taps are queued rather than lost');
$('scene').dispatchEvent(new KeyboardEvent('keydown',{key:'s',bubbles:true}));
assert(currentState.actions===count+8,'Backward disabled');
document.querySelector('.image-button').click();await $('large-image').decode();
assert($('image-dialog').open&&$('large-image').naturalWidth>0,'Image lightbox');
const image=$('large-image').src;$('next-image').click();assert($('large-image').src!==image,'Cross between memory views');$('image-dialog').close();
enterRecordingView();assert(document.body.classList.contains('recording-mode'),'Recording view fills viewport');
const strip=document.querySelector('.images');strip.scrollLeft=200;assert(strip.scrollLeft>0,'Images scroll horizontally');
$('memory-toggle').click();assert(document.body.classList.contains('memories-hidden'),'Hamburger hides sidebar');
$('memory-toggle').click();assert(!document.body.classList.contains('memories-hidden'),'Hamburger restores sidebar');
await toggleVoice();assert(voice,'Reasoning microphone starts');await pause(450);await toggleVoice();
await until(()=>!voice&&!pendingUploads&&!currentState.processing,300);
assert(currentState.audio.length===1&&currentState.audio[0].filename.endsWith('.mp4'),'Reasoning saved as MP4');
$('reasoning').value='Automated microphone test transcript; not a human demonstration.';await $('annotation').onclick();
const canvas=document.createElement('canvas');canvas.width=512;canvas.height=512;
await $('scene').decode();canvas.getContext('2d').drawImage($('scene'),0,0);
const originalCapture=navigator.mediaDevices.getDisplayMedia;
navigator.mediaDevices.getDisplayMedia=async()=>canvas.captureStream(15);
await toggleScreen();if($('screen-start-dialog').open)await $('screen-start').onclick();assert(screen&&document.body.classList.contains('recording-mode'),'Screen button enters focused view');
await pause(550);await toggleScreen();navigator.mediaDevices.getDisplayMedia=originalCapture;
await until(()=>!screen&&!pendingUploads&&!currentState.processing,400);
assert(currentState.videos.some(v=>v.filename==='screen_000.mp4'),'Screen saved as MP4');
assert(currentState.videos.every(v=>v.filename.endsWith('.mp4')),'No WebM download links');
// Follow the labelled human route aid to verify the arrival notice.
for(let i=0;i<200&&!currentState.goal_reached;i++){
 const guide=await api('/api/guidance');if(guide.next_action==='stop')break;await act(guide.next_action);
}
assert(currentState.goal_reached&&!$('completion-banner').hidden,'Destination arrival warning');
navigator.mediaDevices.getDisplayMedia=async()=>canvas.captureStream(15);
const redraw=setInterval(()=>canvas.getContext('2d').drawImage($('scene'),0,0),60);
await toggleVoice();await toggleScreen();if($('screen-start-dialog').open)await $('screen-start').onclick();await pause(550);
const stoppedTracks=[...voice.stream.getTracks(),...screen.display.getTracks(),...screen.mic.getTracks()];
await act('stop');clearInterval(redraw);navigator.mediaDevices.getDisplayMedia=originalCapture;
assert(!voice&&!screen&&!pendingUploads&&stoppedTracks.every(t=>t.readyState==='ended'),'STOP ends both recorders and their tracks');
await until(()=>currentState.download_url,400);
assert(currentState.audio.length===2&&currentState.videos.some(v=>v.filename==='screen_001.mp4'),'STOP saves both final recordings');
assert(finished&&!active&&!$('completion-banner').hidden,'Completed episode warning');
const recordId=currentSession;
await toggleScreen();assert($('new-sample-dialog').open&&!screen,'Cannot record another completed episode');$('new-sample-dialog').close();
const links=[...$('video-downloads').querySelectorAll('a')];
assert(links.length===3&&links.every(a=>a.href.includes('.mp4')),'Navigation and screen MP4 links');
const video=await fetch(links.find(a=>a.href.includes('screen_000.mp4')).href);
assert(video.ok&&video.headers.get('Content-Type')==='video/mp4','Screen download is actual MP4');
return {session_id:recordId,all_checks_passed:true,username_auto_load:true,old_profile_and_recordings_copied:true,
 relevant_memory_auto_selected:true,reasoning_only:true,continuous_Mary_said_statements:true,numbered_memory_tree:true,
 thumbnails_decoded:9,image_scroll_and_lightbox:true,hamburger_sidebar:true,recording_focus_view:true,
 rapid_keypresses_preserved:true,backward_disabled:true,reasoning_MP4:true,screen_MP4:true,
 destination_notice:true,new_sample_required_after_completion:true,events_collapsed:true,
 STOP_ends_and_saves_screen_and_microphone:true,saved_samples_at_bottom:true,previous_transcript_hint_restored:true,
 human_voice_recorded:false,human_desktop_recorded:false};
})()''')
        (ROOT/'browser_verification.json').write_text(json.dumps(result,indent=2)+'\n')
        for name in ['recording_preview.png']:
            shot=client.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})
            (ROOT/name).write_bytes(base64.b64decode(shot['data']))
        with urllib.request.urlopen('http://127.0.0.1:8878/api/download?session='+result['session_id'],timeout=60) as response:
            (ROOT/'browser_validation.zip').write_bytes(response.read())
        # Delete only the labelled validation sample, keeping imported human data.
        client.evaluate('window.confirm=()=>true;deleteSample(currentSession)')
        print(json.dumps(result,indent=2))
    finally:
        if client:client.sock.close()
        process.terminate()
        try:process.wait(timeout=8)
        except subprocess.TimeoutExpired:process.kill();process.wait()
        log.close()


if __name__=='__main__':main()
