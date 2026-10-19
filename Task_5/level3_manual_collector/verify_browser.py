#!/usr/bin/env python3
"""Use an isolated CPU browser to verify UI controls and fake microphone media."""
import base64
import hashlib
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import time
import urllib.request
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent


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


def main():
    import shutil
    chrome=shutil.which('google-chrome')
    assert chrome
    log=(ROOT/'browser_check.log').open('wb')
    process=subprocess.Popen([chrome,'--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage',
        '--user-data-dir=/tmp/level3-collector-browser-check','--remote-debugging-port=8877',
        '--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream',
        '--window-size=1680,1050','http://localhost:8876'],stdout=log,stderr=log)
    client=None
    try:
        last_error=None
        for _ in range(60):
            try:
                tabs=json.load(urllib.request.urlopen('http://127.0.0.1:8877/json',timeout=1))
                tab=next(x for x in tabs if x.get('type')=='page' and 'localhost:8876' in x.get('url',''))
                client=CDP(tab['webSocketDebuggerUrl']);break
            except Exception as error:last_error=error;time.sleep(.2)
        assert client,f'Browser connection failed: {last_error}'
        for _ in range(60):
            ready=client.evaluate('document.getElementById("connection")?.textContent === "Scene connected"')
            if ready:break
            time.sleep(.2)
        assert ready,'Collector UI did not connect'
        screenshot=client.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})
        (ROOT/'collector_preview.png').write_bytes(base64.b64decode(screenshot['data']))
        checks=client.evaluate('''(async()=>{
const assert=(value,message)=>{if(!value)throw Error(message)},pause=ms=>new Promise(r=>setTimeout(r,ms));
assert(window.isSecureContext,'Microphone secure context');
assert(document.querySelectorAll('.memory').length===3,'Three memory cards');
assert([...document.querySelectorAll('.memory img')].every(i=>i.complete&&i.naturalWidth>0),'Memory images decoded');
assert($('scene').complete&&$('scene').naturalWidth===512,'Live image loaded');
assert(!(await api('/api/state')).active,'Do not interrupt active recording');
$('annotator').value='browser_validation';
// Mark fake microphone/control data in the server manifest.
started=performance.now();
update(await api('/api/start',{annotator:'browser_validation',recording_source:'automated_browser_check_with_fake_microphone_not_human',relevant_memory_ids:['uniforms']}));
const activeDelete=await fetch('/api/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:currentSession,confirm_session:currentSession})});
assert(activeDelete.status===400&&(await api('/api/state')).active,'Active sample cannot be deleted');
const before=(await api('/api/state')).actions;
await act('forward');assert((await api('/api/state')).actions===before+1,'Forward button API');
$('scene').focus();lastKeyAt=0;
$('scene').dispatchEvent(new KeyboardEvent('keydown',{key:'d',bubbles:true}));await pause(300);
assert((await api('/api/state')).actions===before+2,'D key executes right turn');
$('scene').dispatchEvent(new KeyboardEvent('keydown',{key:'s',bubbles:true}));await pause(100);
assert((await api('/api/state')).actions===before+2,'S does not move');
await toggleVoice();assert(voice,'Voice recorder started');await pause(500);
await toggleVoice();for(let i=0;i<60&&(voice||pendingUploads);i++)await pause(100);
assert(!voice&&!pendingUploads,'Fake microphone clip saved');
assert($('media-list').querySelector('audio'),'Audio playback control created');
assert($('media-list').querySelector('.media-download'),'Direct voice download created');
// A canvas video verifies saved screen-file downloads without recording a
// person's desktop. Its provenance is explicitly automated test data.
await $('scene').decode();
const canvas=document.createElement('canvas');canvas.width=512;canvas.height=512;
canvas.getContext('2d').drawImage($('scene'),0,0,512,512);
const fixtureStream=canvas.captureStream(5),fixtureRecorder=new MediaRecorder(fixtureStream,{mimeType:'video/webm'}),fixtureChunks=[];
fixtureRecorder.ondataavailable=e=>{if(e.data.size)fixtureChunks.push(e.data)};
const fixtureStart=elapsed();fixtureRecorder.start();await pause(300);
await new Promise(resolve=>{fixtureRecorder.onstop=resolve;fixtureRecorder.stop()});fixtureStream.getTracks().forEach(t=>t.stop());
const screenFile=await upload(new Blob(fixtureChunks,{type:'video/webm'}),'screen','video/webm',fixtureStart,elapsed());
await api('/api/annotate',{kind:'validation_provenance',text:'Screen video is a canvas fixture, not a human desktop recording.'});
const screenResponse=await fetch(screenFile.download_url);assert(screenResponse.ok,'Screen download HTTP success');
assert(screenResponse.headers.get('Content-Type')==='video/webm','Screen download MIME');
assert((await screenResponse.arrayBuffer()).byteLength>0,'Screen download contains video');
$('reasoning').value='Browser verification transcript placeholder, not human speech.';
await $('annotation').onclick();assert($('reasoning').value==='','Transcript saved');
// Verify screen capture can remain active while navigation finishes. Actual
// display selection is left to the real browser user, not faked as a recording.
screen={validation_placeholder:true};
await act('stop');assert(finished&&!active,'STOP finishes recording');
assert(!$('screen').disabled&&$('download').hidden,'Screen remains stoppable; download waits');
screen=null;update(await api('/api/state'));
assert(!$('download').hidden,'ZIP download appears');
const links=[...$('video-downloads').querySelectorAll('a')];assert(links.length===2,'Separate navigation and screen links');
const mp4Link=links.find(a=>a.textContent==='Download navigation MP4');assert(mp4Link,'Navigation download label');
const mp4Response=await fetch(mp4Link.href);assert(mp4Response.ok&&mp4Response.headers.get('Content-Type')==='video/mp4','Navigation download content');
assert((await mp4Response.arrayBuffer()).byteLength>0,'Navigation MP4 not empty');
const session=currentSession;
const blocked=await fetch('/api/media?'+new URLSearchParams({session,file:'../inputs.json'}));assert(blocked.status===400,'Media path traversal rejected');
await $('return-user').onclick();assert(!$('saved-sessions').hidden,'Returning user sees saved session');
assert($('old-videos').querySelectorAll('a').length===2,'Returning user individual video links');
assert(!$('delete-current').hidden&&!$('delete-saved').hidden,'Current and saved Delete buttons appear');
const missingConfirm=await fetch('/api/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:session})});
assert(missingConfirm.status===400,'Backend requires exact sample confirmation');
const confirmOriginal=window.confirm;let prompt='';
try{
 window.confirm=text=>{prompt=text;return false};await $('delete-current').onclick();
 assert(prompt.includes(session)&&prompt.includes('recovered'),'Confirmation identifies exact sample and recovery');
 assert((await api('/api/sessions?annotator=browser_validation')).some(s=>s.id===session),'Cancel keeps the sample');
 window.confirm=()=>true;await $('delete-current').onclick();
 assert(!(await api('/api/sessions?annotator=browser_validation')).some(s=>s.id===session),'Confirmed current sample removed');
 assert((await api('/api/state')).session_id===null&&$('delete-current').hidden,'Delete resets current sample');
 assert((await fetch(mp4Link.href)).status===400,'Deleted recording disappears from downloads');
 // Deleting an older saved test sample must preserve another active sample.
 $('annotator').value='deletion_validation';started=performance.now();
 const older=await api('/api/start',{annotator:'deletion_validation',recording_source:'automated_deletion_validation_not_human'});
 await api('/api/action',{action:'stop'});
 const newer=await api('/api/start',{annotator:'deletion_validation',recording_source:'automated_deletion_validation_not_human'});
 update(await api('/api/action',{action:'right'}));
 const imageBefore=new Uint8Array(await (await fetch('/api/frame')).arrayBuffer());
 await $('return-user').onclick();
 const option=[...$('saved-sessions').options].find(o=>o.dataset.session===older.session_id);
 assert(option,'Older test sample is selectable');$('saved-sessions').value=option.value;$('saved-sessions').onchange();
 await $('delete-saved').onclick();
 const stillActive=await api('/api/state'),imageAfter=new Uint8Array(await (await fetch('/api/frame')).arrayBuffer());
 assert(stillActive.active&&stillActive.session_id===newer.session_id&&stillActive.actions===1,'Deleting old sample preserves active sample');
 assert(imageBefore.length===imageAfter.length&&imageBefore.every((v,i)=>v===imageAfter[i]),'Active camera pose unchanged');
 update(await api('/api/action',{action:'stop'}));await $('delete-current').onclick();
 assert((await api('/api/state')).session_id===null,'Validation cleaned up');
}finally{window.confirm=confirmOriginal}
return {three_memory_cards:true,nine_images_decoded:true,live_frame_loaded:true,forward_control:true,D_turn_control:true,S_does_not_move:true,secure_context:true,fake_microphone_recording_and_upload:true,transcript_annotation_saved:true,STOP_and_download:true,screen_can_continue_through_STOP:true,returning_user_session_list:true,direct_navigation_MP4_download:true,direct_screen_video_download:true,returning_user_video_downloads:true,media_path_traversal_rejected:true,current_and_saved_Delete_buttons:true,exact_sample_confirmation_required:true,cancel_keeps_sample:true,active_sample_deletion_rejected:true,deleted_sample_removed_from_saved_list:true,older_sample_deletion_preserves_active_recording_and_pose:true,human_voice_recorded:false,human_screen_recorded:false,screen_capture_requires_real_user_selection:true};
})()''')
        checks['all_checks_passed']=True
        (ROOT/'browser_verification.json').write_text(json.dumps(checks,indent=2)+'\n')
        print(json.dumps(checks,indent=2))
    finally:
        if client:client.sock.close()
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait()
        log.close()


if __name__=='__main__':main()
