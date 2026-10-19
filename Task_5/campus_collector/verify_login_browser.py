"""Exercise the owner-account sign-in form in an isolated Chrome profile.

Uses a temporary mock collector and synthetic credentials. No real user data,
media devices, GPU renderers, or operating-system trust stores are touched.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'level3_manual_collector_v2'))
from browser_cdp import CDP
from test_gateway import GatewayTests


def main():
    GatewayTests.setUpClass()
    server=GatewayTests.server
    password=GatewayTests.password
    server.accounts.add("browser_contributor",password)
    profile=tempfile.TemporaryDirectory(prefix='task5-registration-browser-')
    log=open(Path(profile.name)/'browser.log','wb')
    process=subprocess.Popen([shutil.which('google-chrome'),'--headless','--no-sandbox','--disable-gpu',
        '--disable-dev-shm-usage','--remote-debugging-port=0','--user-data-dir='+profile.name,
        '--window-size=1280,1000',GatewayTests.origin],stdout=log,stderr=log)
    client=None
    def until(script):
        for _ in range(100):
            try:
                result=client.evaluate(script)
                if result:return result
            except Exception:pass
            time.sleep(.1)
        raise AssertionError('Browser condition timed out: '+script)
    def navigate(path):
        client.call('Page.navigate',{'url':GatewayTests.origin+path})
        until('document.readyState === "complete" && location.pathname === '+json.dumps(path))
    def fill_and_submit(fields):
        client.evaluate('(()=>{const values='+json.dumps(fields)+';for(const [name,value] of Object.entries(values))document.querySelector("[name="+name+"]").value=value;document.querySelector("form").requestSubmit()})()')
    try:
        for _ in range(100):
            try:
                port=(Path(profile.name)/'DevToolsActivePort').read_text().splitlines()[0]
                pages=json.load(urllib.request.urlopen('http://127.0.0.1:'+port+'/json'))
                page=next(p for p in pages if p.get('type')=='page' and p.get('url','').startswith(GatewayTests.origin))
                client=CDP(page['webSocketDebuggerUrl']);break
            except Exception:time.sleep(.1)
        assert client
        until('!!document.querySelector("form[action=\\\"/auth/login\\\"]")')
        assert not client.evaluate('!!document.querySelector("a[href=\\\"/register\\\"]")')
        assert not client.evaluate('!!document.querySelector("[name=invite]")')
        assert client.evaluate('document.querySelector("[name=password]").autocomplete')=='current-password'
        client.call('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
        assert client.evaluate('document.documentElement.scrollWidth <= innerWidth')
        fill_and_submit({'username':'browser_contributor','password':'deliberately-wrong-password'})
        until('document.body.textContent.includes("Invalid contributor ID or password")')
        assert client.evaluate('document.querySelector("[name=password]").value')==''
        fill_and_submit({'username':'browser_contributor','password':password})
        identity=until('(async()=>{const r=await fetch("/auth/me");const v=await r.json();return v.username==="browser_contributor"&&v})()')
        assert identity['username']=='browser_contributor'
        until('(async()=>{const r=await fetch("/api/state");return r.ok})()')
        assert client.evaluate('(async()=>{const r=await fetch("/auth/logout",{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"});return r.status})()')==200
        navigate('/login')
        assert client.evaluate('(async()=>{const r=await fetch("/auth/me");return r.status})()')==401
        assert client.evaluate('(async()=>{const r=await fetch("/register");return r.status})()')==404
        assert client.evaluate('(async()=>{const r=await fetch("/auth/register",{method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body:"username=unapproved"});return r.status})()')==404
        report={'passed':True,'actual_browser_login':True,'mobile_layout_fits':True,
                'wrong_password_feedback':True,'owner_created_account_signs_in':True,
                'logout_clears_login':True,'self_registration_unavailable':True,
                'no_invitation_field':True,'synthetic_credentials_only':True}
        (ROOT/'login_browser_verification.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
    finally:
        if client:client.sock.close()
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait()
        log.close();profile.cleanup();GatewayTests.tearDownClass()


if __name__=='__main__':main()
