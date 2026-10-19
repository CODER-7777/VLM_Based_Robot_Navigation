#!/usr/bin/env python3
"""Check UI lifecycle in an isolated browser with synthetic data and media.

The dashboard HTML/JS/CSS are exercised without calling the shared simulator.
Chrome's Fullscreen API is real; microphone/video inputs are explicit fixtures.
"""
import json
from pathlib import Path
import shutil
import subprocess
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from browser_cdp import CDP

ROOT = Path(__file__).resolve().parent
FIXTURE = '''
window.fixtureSessions=[];
window.fixtureCalls=[];
api=async(path,data)=>{
 fixtureCalls.push(path);
 if(path.startsWith('/api/sessions?'))return structuredClone(fixtureSessions);
 throw Error('Unexpected backend call in isolated UI test: '+path);
};
caseData={default_relevant_memory_ids:['uniforms']};
function fixtureState(values={}){return {active:false,finished:false,session_id:null,
 annotator:'fixture_user',actions:0,path_length_m:0,elapsed_seconds:0,processing:false,
 download_url:null,media_jobs:[],videos:[],audio:[],...values};}
const pixel='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg==';
function fixtureCase(key,scene,speaker){return {
 episode_key:key,scene,title:speaker+' task',index:scene==='first'?1:2,
 default_request:'Help '+speaker,default_current_state:'It is Thursday morning.',
 default_relevant_memory_ids:[key+'_memory_2'],
 memories:[1,2,3].map(number=>({id:key+'_memory_'+number,who:speaker,said:'Statement '+number,
 when:'Wednesday 18:00',image_urls:[pixel],original_view_indices:[1],view_descriptions:['Fixture view'],
 navigation_paragraph:'Synthetic test description'})),
 voice_examples:{before:speaker+' said the relevant statement.',decision:'Choose a movement from visible evidence.',
 passing:'Review this room.',correction:'Review the route.',arrival:'I reached the relevant place.'}};}
window.fixtureCases={first_episode:fixtureCase('first_episode','first','Riya'),second_episode:fixtureCase('second_episode','second','Asha')};
const listApi=api;
api=async(path,data)=>{
 if(path==='/api/select'){fixtureCalls.push(path);const c=fixtureCases[data.episode_key];return fixtureState({scene:c.scene,episode_key:c.episode_key,case:c,frame_data_url:pixel})}
 if(path==='/api/load'){fixtureCalls.push(path);const c=fixtureCases.second_episode;return fixtureState({finished:true,session_id:data.session_id,scene:c.scene,episode_key:c.episode_key,case:c,
 inputs:{request:'Saved Asha request',current_state:'Saved Asha context',human_selected_memory_ids:c.default_relevant_memory_ids}})}
 return listApi(path,data);
};
$('annotator').value='fixture_user';$('request').value='Take the carried clothes to laundry';
$('current-state').value='I already have the dirty clothes';banner();
update(fixtureState());
'''


class FixtureHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            content = (ROOT/'web/index.html').read_bytes();mime='text/html'
        elif self.path == '/app.js':
            source = (ROOT/'web/app.js').read_text()
            # Omit automatic initialization: never contact the actual simulator.
            content = (source.rsplit('(async()=>{',1)[0] + FIXTURE).encode();mime='text/javascript'
        elif self.path == '/style.css':
            content = (ROOT/'web/style.css').read_bytes();mime='text/css'
        elif self.path in ['/fixture-navigation.mp4','/fixture-screen.mp4']:
            name = 'navigation.mp4' if 'navigation' in self.path else 'screen_001.mp4'
            content = (ROOT/name).read_bytes();mime='video/mp4'
        else:
            self.send_error(404);return
        self.send_response(200);self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(content)));self.end_headers();self.wfile.write(content)

    def log_message(self,*args):
        pass


def click(client,selector):
    point=client.evaluate('''(()=>{const r=document.querySelector('''+json.dumps(selector)+''').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})()''')
    for kind in ['mousePressed','mouseReleased']:
        client.call('Input.dispatchMouseEvent',{'type':kind,'button':'left','clickCount':1,**point})


def main():
    server=ThreadingHTTPServer(('127.0.0.1',8882),FixtureHandler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    log=(ROOT/'updates_browser_check.log').open('wb')
    process=subprocess.Popen([shutil.which('google-chrome'),'--headless','--no-sandbox','--disable-gpu',
        '--disable-dev-shm-usage','--user-data-dir=/tmp/level3-updates-browser-profile',
        '--remote-debugging-port=8883','--window-size=1680,1080',
        '--autoplay-policy=no-user-gesture-required','--use-fake-device-for-media-stream',
        '--use-fake-ui-for-media-stream','http://localhost:8882'],stdout=log,stderr=log)
    client=None
    try:
        for _ in range(70):
            try:
                tabs=json.load(urllib.request.urlopen('http://127.0.0.1:8883/json',timeout=1))
                page=next(t for t in tabs if t.get('type')=='page' and 'localhost:8882' in t.get('url',''))
                client=CDP(page['webSocketDebuggerUrl']);break
            except Exception:time.sleep(.1)
        assert client
        for _ in range(60):
            if client.evaluate('typeof fixtureState === "function" && !!currentState'):break
            time.sleep(.1)
        report=client.evaluate('''(async()=>{
const assert=(v,m)=>{if(!v)throw Error(m)},pause=ms=>new Promise(r=>setTimeout(r,ms));
async function until(test){for(let i=0;i<100;i++){if(test())return;await pause(100)}throw Error('Timed out')}
const old={id:'sessions/fixture_user/old',download:'/old.zip',videos:[]};
const fresh={id:'sessions/fixture_user/new',download:'/new.zip',videos:[]};
fixtureSessions=[old];renderSavedSessions('fixture_user',fixtureSessions,old.id);
$('reasoning').value='Keep this unsaved transcript';
update(fixtureState({active:true,session_id:fresh.id}));
assert($('sample-preview').hidden,'No saved preview during active recording');
fixtureSessions=[fresh,old];
update(fixtureState({finished:true,session_id:fresh.id,processing:true}));
await until(()=>$('saved-sessions').options.length===2&&$('saved-sessions').value===fresh.id);
assert(!$('sample-preview').hidden&&$('sample-video').hidden,'Waiting preview shown after STOP');
const navigation={filename:'navigation.mp4',label:'Download navigation MP4',url:'/fixture-navigation.mp4'};
const screenVideo={filename:'screen_000.mp4',label:'Download screen recording',url:'/fixture-screen.mp4'};
fixtureSessions[0].videos=[navigation,screenVideo];
const saved=fixtureState({finished:true,session_id:fresh.id,videos:[navigation,screenVideo],download_url:'/new.zip',
 media_jobs:[{id:'fixture_ready',status:'ready',kind:'screen',path:'screen/screen_000.mp4'}]});
update(saved);
await until(()=>$('old-videos').querySelectorAll('a').length===2);
assert($('sample-video').dataset.source===screenVideo.url,'Preview prefers screen recording');
await until(()=>$('sample-video').readyState>=2);
const video=$('sample-video');video.muted=true;await video.play();await pause(130);
const position=video.currentTime;assert(position>0,'Saved preview actually plays');
update(saved);assert(video.currentTime>=position,'Polling does not reset playback');
$('preview-recording').value='navigation.mp4';$('preview-recording').dispatchEvent(new Event('change'));
assert(video.dataset.source===navigation.url,'Navigation preview selected');update(saved);
assert(video.dataset.source===navigation.url,'Polling preserves manual preview selection');
$('saved-sessions').value=old.id;
fixtureSessions.unshift({id:'sessions/fixture_user/external',download:'/external.zip',videos:[]});
await until(()=>$('saved-sessions').options.length===3);
assert($('saved-sessions').value===old.id,'Periodic refresh preserves chosen saved sample');
assert($('reasoning').value==='Keep this unsaved transcript','Refresh preserves unsaved transcript');
assert(currentSession===fresh.id,'List polling never loads or resets the simulator');
assert(fixtureCalls.every(path=>path.startsWith('/api/sessions?')),'Refresh uses read-only listing only');
environmentChoices=Object.values(fixtureCases).map(c=>({scene:c.scene,label:c.scene,available:true,
 episodes:[{episode_key:c.episode_key,title:c.title,index:c.index}]}));
for(const env of environmentChoices){const o=document.createElement('option');o.value=env.scene;o.textContent=env.label;$('environment-select').append(o)}
await selectEpisode('second_episode');
assert($('environment-select').value==='second'&&$('episode-select').value==='second_episode','Environment and episode selectors synced');
assert($('request').value==='Help Asha'&&$('current-state').value==='It is Thursday morning.','Correct episode task and context');
assert([...document.querySelectorAll('.memory blockquote')].every(e=>e.textContent.startsWith('Asha said')),'New environment memory speakers');
assert(selected().join(',')==='second_episode_memory_2','New episode relevant memory selected');
assert($('voice-before').textContent.includes('Asha'),'Voice template matches episode');
await selectEpisode('first_episode');
assert(document.querySelector('.memory blockquote').textContent.startsWith('Riya said'),'Other environment memories rendered');
await loadSession({id:'sessions/fixture_user/saved_second'});
assert($('environment-select').value==='second'&&$('request').value==='Saved Asha request','Saved sample restores matching environment');
assert(selected().join(',')==='second_episode_memory_2','Saved sample restores correct selected memory');
update(fixtureState({active:true,session_id:'sessions/fixture_user/fullscreen'}));
const switchCount=fixtureCalls.filter(p=>p==='/api/select').length;
await selectEpisode('first_episode');
assert(fixtureCalls.filter(p=>p==='/api/select').length===switchCount,'Active recording blocks environment switch');
assert($('environment-select').value==='second','Rejected switch keeps environment selection');

window.captureRequests=0;
const canvas=document.createElement('canvas');canvas.width=512;canvas.height=512;
window.drawTimer=setInterval(()=>{const c=canvas.getContext('2d');c.fillStyle='#276955';c.fillRect(0,0,512,512)},60);
navigator.mediaDevices.getDisplayMedia=async()=>{
 if(!navigator.userActivation.isActive)throw Error('Capture requires a real button click');
 captureRequests++;return canvas.captureStream(15);
};
upload=async()=>({status:'fixture_not_human'});
$('screen').scrollIntoView({block:'center'});
return {saved_list_updates_after_STOP:true,MP4_links_update_after_export:true,
 periodic_list_refresh_without_page_reload:true,chosen_saved_sample_preserved:true,
 unsaved_transcript_preserved:true,preview_appears_after_STOP:true,screen_preview_preferred:true,
 preview_playback_verified:true,navigation_preview_selectable:true,playback_not_reset_by_polling:true,
 simulator_not_changed_by_list_polling:true,environment_episode_selectors_synced:true,
 new_episode_task_context_and_speakers_correct:true,relevant_memory_and_voice_template_update:true,
 saved_session_restores_correct_environment_UI:true,active_recording_blocks_scene_switch:true};
})()''')
        click(client,'#screen')
        for _ in range(60):
            if client.evaluate('!!document.fullscreenElement && $("screen-start-dialog").open'):break
            time.sleep(.1)
        assert client.evaluate('!!document.fullscreenElement && $("screen-start-dialog").open'), 'Native fullscreen failed'
        assert client.evaluate('captureRequests===0'), 'Capture started before the fullscreen continuation click'
        click(client,'#screen-start')
        for _ in range(70):
            if client.evaluate('!!screen'):break
            time.sleep(.1)
        assert client.evaluate('!!screen && captureRequests===1 && !!document.fullscreenElement'), 'Fullscreen capture failed'
        client.evaluate('screen.recorder.stop();clearInterval(drawTimer)')
        for _ in range(60):
            if client.evaluate('!screen'):break
            time.sleep(.1)
        report.update(native_browser_fullscreen_verified=True,
            capture_starts_from_fresh_trusted_click=True,fullscreen_remains_active_during_capture=True,
            human_screen_recorded=False,shared_simulator_requests=0,all_checks_passed=True)
        (ROOT/'updates_verification.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
    finally:
        if client:client.sock.close()
        process.terminate()
        try:process.wait(timeout=8)
        except subprocess.TimeoutExpired:process.kill();process.wait()
        server.shutdown();server.server_close();log.close()


if __name__=='__main__':main()
