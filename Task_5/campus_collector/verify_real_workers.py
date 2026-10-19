"""Server-side synthetic integration check; never uses a person's mic or screen."""
from http.client import HTTPConnection
import json
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import threading
import time
from urllib.parse import urlencode
import wave
from gateway import Gateway

ROOT=Path(__file__).resolve().parent


def main():
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    cfg=dict(bind='127.0.0.1',port=port,public_origin=f'http://127.0.0.1:{port}',
             allowed_networks=['127.0.0.1/32'],data_root=str(ROOT/'synthetic_validation_data'),
             template_root=str(ROOT/'template'),backend_python='/home/guest-isl/rishabh/bench/envs/navila/bin/python',
             worker_port_start=9130,max_workers=2,minimum_free_bytes=0)
    server=Gateway(cfg,dev=True);threading.Thread(target=server.serve_forever,daemon=True).start()
    tokens={};checks=[];name_suffix=secrets.token_hex(3)
    users=['campus_qa_a_'+name_suffix,'campus_qa_b_'+name_suffix,'campus_qa_c_'+name_suffix]
    def request(path,method='GET',body=None,user=None,ctype='application/json'):
        headers={'Host':f'127.0.0.1:{port}','Content-Type':ctype}
        if user:headers['Cookie']=tokens[user]
        if method=='POST':headers['Origin']=cfg['public_origin']
        con=HTTPConnection('127.0.0.1',port,timeout=90)
        try:
            con.request(method,path,body,headers);response=con.getresponse()
            return response.status,dict(response.getheaders()),response.read()
        finally:con.close()
    def api(path,user,payload=None):
        status,_,raw=request(path,'GET' if payload is None else 'POST',None if payload is None else json.dumps(payload).encode(),user)
        assert status==200,(path,status,raw[:200]);return json.loads(raw)
    try:
        password=secrets.token_urlsafe(24)
        for user in users:
            server.accounts.add(user,password)
            code,headers,_=request('/auth/login','POST',urlencode({'username':user,'password':password}).encode(),ctype='application/x-www-form-urlencoded')
            assert code==303;tokens[user]=headers['Set-Cookie'].split(';')[0]
        for user in users[:2]:server.pool.get(user)
        deadline=time.monotonic()+150
        pending=set(users[:2])
        while pending and time.monotonic()<deadline:
            for user in list(pending):
                w=server.pool.workers[user]
                if w.process.poll() is not None:raise RuntimeError('Renderer exited; inspect '+str(server.pool.root/user/'worker.log'))
                if server.pool.state(w):pending.remove(user);print('Independent renderer ready:',user,flush=True)
            time.sleep(.3)
        assert not pending,'Renderers did not become ready'
        checks.append('two simultaneous actual Habitat renderers on GPU 0')
        assert request('/api/state',user=users[2])[0]==503
        checks.append('capacity guard refuses a third active renderer')
        sessions={}
        for user in users[:2]:
            case=api('/api/case',user)
            state=api('/api/start',user,{'annotator':'forged_other_person','request':case['default_request'],
                'current_state':case['default_current_state'],'episode_key':case['episode_key'],
                'relevant_memory_ids':case.get('default_relevant_memory_ids',[]),
                'recording_source':'automated_campus_gateway_validation_SYNTHETIC'})
            assert state['annotator']==user;sessions[user]=state['session_id']
        checks.append('server binds recorded annotator to authenticated contributor')
        api('/api/action',users[0],{'action':'right','client_elapsed_ms':100})
        assert api('/api/state',users[0])['actions']==1 and api('/api/state',users[1])['actions']==0
        checks.append('one contributor navigation does not move the other simulator')
        assert request('/api/media?'+urlencode({'session':sessions[users[1]],'file':'navigation.mp4'}),user=users[0])[0]==403
        checks.append('cross-contributor media request denied')
        # Generate synthetic test media entirely on CPU.
        audio=ROOT/'synthetic_test.wav'
        with wave.open(str(audio),'wb') as stream:
            stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(16000);stream.writeframes(b'\0\0'*16000)
        ffmpeg=subprocess.check_output([cfg['backend_python'],'-c','import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())'],text=True).strip()
        video=ROOT/'synthetic_test.mp4'
        subprocess.run([ffmpeg,'-y','-loglevel','error','-f','lavfi','-i','color=c=blue:s=128x128:r=10',
                        '-i',str(audio),'-t','1','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',str(video)],check=True)
        for user in users[:2]:
            for kind,file,mime in [('voice',audio,'audio/wav'),('screen',video,'video/mp4')]:
                status,_,raw=request('/api/upload?'+urlencode({'kind':kind,'session':sessions[user],'mime':mime,
                    'start_ms':0,'end_ms':1000}),'POST',file.read_bytes(),user,ctype=mime)
                assert status==200,(status,raw[:200])
            api('/api/action',user,{'action':'stop','client_elapsed_ms':1200})
        deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            states={user:api('/api/state',user) for user in users[:2]}
            if all(not s['processing'] for s in states.values()):break
            time.sleep(.5)
        for user,state in states.items():
            assert state['finished'] and not state['processing']
            assert not any(j['status']=='error' for j in state['media_jobs']),state['media_jobs']
            folder=server.pool.root/user/sessions[user]
            for relative in ['navigation.mp4','audio/voice_000.mp4','screen/screen_000.mp4','manifest.json','inputs.json']:
                assert (folder/relative).is_file(),str(folder/relative)
        checks.append('synthetic audio, screen video, navigation MP4 and metadata saved in each contributor folder')
        for user in users[:2]:assert request('/auth/logout','POST',b'{}',user)[0]==200
        checks.append('finished contributors release their own renderer safely')
        report={'passed':True,'checks':checks,'human_audio_recorded':False,'human_screen_recorded':False,
                'campus_listener_published':False,'gpu':0,'simultaneous_contributors_tested':2,
                'sessions':sessions,'data_root':cfg['data_root']}
        (ROOT/'real_worker_verification.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2),flush=True)
    finally:
        for user in users:server.accounts.disable(user)
        server.shutdown();server.server_close();server.pool.close()


if __name__=='__main__':main()
