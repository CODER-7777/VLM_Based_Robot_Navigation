/* Browser acceptance checks using the installed Chrome and its DevTools protocol. */
const fs=require('fs'),path=require('path'),{spawn}=require('child_process'),WebSocket=require('/usr/share/nodejs/ws');
const root=__dirname,runtime=path.join(root,'.runtime'),shots=path.join(runtime,'screenshots');fs.mkdirSync(shots,{recursive:true});
const key=fs.readFileSync(path.join(runtime,'remote_author_key'),'utf8').trim();
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const chrome=spawn('/usr/bin/google-chrome',['--headless=new','--no-sandbox','--disable-dev-shm-usage','--disable-gpu','--remote-debugging-port=0',`--user-data-dir=${runtime}/chrome-qa`],{stdio:['ignore','ignore','pipe']});
let ws,id=0;const pending=new Map(),exceptions=[];
async function main(){
 const url=await new Promise((resolve,reject)=>{let buf='';chrome.stderr.on('data',d=>{buf+=d;const match=buf.match(/DevTools listening on (ws:\/\/[^\s]+)/);if(match)resolve(match[1]);});chrome.on('exit',code=>reject(Error('Chrome exited '+code)));setTimeout(()=>reject(Error('Chrome did not start')),15000);});
 ws=new WebSocket(url);await new Promise(r=>ws.on('open',r));ws.on('message',raw=>{const d=JSON.parse(raw);if(d.id){const p=pending.get(d.id);if(p){pending.delete(d.id);d.error?p.reject(Error(d.error.message)):p.resolve(d.result);}}else if(d.method==='Runtime.exceptionThrown')exceptions.push(d.params.exceptionDetails.text);});
 async function call(method,params={},sessionId){const message={id:++id,method,params};if(sessionId)message.sessionId=sessionId;return new Promise((resolve,reject)=>{pending.set(id,{resolve,reject});ws.send(JSON.stringify(message));});}
 const target=await call('Target.createTarget',{url:'about:blank'});const {sessionId:sid}=await call('Target.attachToTarget',{targetId:target.targetId,flatten:true});
 const c=(m,p)=>call(m,p,sid);await c('Page.enable');await c('Runtime.enable');await c('Emulation.setDeviceMetricsOverride',{width:1520,height:1100,deviceScaleFactor:1,mobile:false});
 async function evaluate(expression,session=sid){const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true},session);if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;}
 async function until(expression,session=sid,ms=30000){const end=Date.now()+ms;while(Date.now()<end){if(await evaluate(expression,session))return;await sleep(200);}throw Error('Timed out: '+expression);}
 async function screenshot(name){const {data}=await c('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync(path.join(shots,name+'.png'),Buffer.from(data,'base64'));}
 function check(condition,label){if(!condition)throw Error(label);console.log('PASS '+label);}
 await c('Page.navigate',{url:`http://127.0.0.1:8896/review?key=${key}`});await until('!!document.querySelector("#reviewForm")');
 check(await evaluate('document.querySelectorAll(".case-row").length===40'),'40 case selectors');
 check(await evaluate('document.querySelector(".type-note").textContent.includes("L1")'),'type-specific checks visible');
 await screenshot('case_review');
 await evaluate('document.querySelector("[data-tab=memories]").click()');await until('document.querySelectorAll(".memory").length>0');
 check(await evaluate('document.querySelectorAll(".memory").length===2'),'only two relevant memories for case 1');
 check(await evaluate('Array.from(document.querySelectorAll(".memory-head b")).map(e=>e.textContent).join(",")==="T01,T02"'),'key and competitor retained; unrelated memories hidden');await screenshot('memories');
 if(process.argv.includes('--types-only')){
  await evaluate(`document.querySelector('[data-case="2azQ1b91cZZ_case30"]').click()`);await until('document.querySelector(".heading").textContent.includes("Case 30")');
  check(await evaluate('document.querySelector("#rubric").textContent.includes("Review focus: M3") && document.querySelector("#reviewForm [name=memory]").closest("label").textContent.includes("where to collect the item") && document.querySelector("#reviewForm [name=form]").closest("label").textContent.includes("infer the pickup")'),'M3 questions check implied pickup and recipient location');
  check(await evaluate('document.querySelector(".same-request-note").textContent.includes("same instruction") && document.querySelector("[data-variant=form0]").textContent.includes("same request")'),'identical request wording is explicitly explained');
  await evaluate('document.querySelector("#reviewNote").value="Temporary M3 draft";document.querySelector("#reviewForm [name=props]").value="major";document.querySelector("[data-variant=form0]").click()');
  check(await evaluate('document.querySelector("#rubric").textContent.includes("Review focus: M1") && document.querySelector("#reviewForm [name=form]").closest("label").textContent.includes("first stop, then the next stop") && !document.querySelector("#rubric").textContent.includes("infer the pickup")'),'M1 changes the questions to stop order');
  await evaluate('document.querySelector("[data-variant=level3]").click()');
  check(await evaluate('document.querySelector("#reviewNote").value==="Temporary M3 draft" && document.querySelector("#reviewForm [name=props]").value==="major"'),'type switching preserves the M3 draft and prop issue');
  await evaluate(`document.querySelector('[data-case="2azQ1b91cZZ_case34"]').click()`);await until('document.querySelector(".heading").textContent.includes("Case 34")');
  check(await evaluate('document.querySelector("#reviewForm [name=memory]").closest("label").textContent.includes("routine that applies on this day")'),'T3 asks about evidence for the applicable routine');
  await evaluate(`document.querySelector('[data-case="2azQ1b91cZZ_case16"]').click()`);await until('document.querySelector(".heading").textContent.includes("Case 16")');
  check(await evaluate('document.querySelector("#reviewForm [name=grounding]").closest("label").textContent.includes("nickname")'),'L1 asks about the nickname');
  check(exceptions.length===0,'no browser runtime exceptions');await screenshot('type_specific_questions');await call('Browser.close');return;
 }
 if(process.argv.includes('--return-only')){
  await evaluate(`document.querySelector('[data-case="2azQ1b91cZZ_case02"]').click()`);await until('document.querySelector(".heading").textContent.includes("Case 02")');
  await evaluate('document.querySelector("[data-variant=form0]").click();document.querySelector("#startNav").click()');
  await until('!!document.querySelector("#view")',sid,90000);
  await evaluate('document.querySelector("[data-action=a]").click()');await until('document.querySelector("#navStatus").textContent.includes("1 actions")');
  await evaluate('document.querySelector("[data-tab=memories]").click();document.querySelector("#reviewNote").value="Keep this review draft after Props";document.querySelector("#reviewForm [name=instruction]").value="minor";document.querySelector("#walked").checked=true;document.querySelector(".sidebar").scrollTop=110;window.scrollTo(0,180)');
  const previous=await evaluate('({token:state.token,scrollY:window.scrollY,sidebarScroll:document.querySelector(".sidebar").scrollTop})');
  await evaluate(`document.querySelector('a[href="/props"]').click()`);await until('document.querySelectorAll("[data-save-prop]").length===5',sid,90000);
  await evaluate(`document.querySelector('a[href="/review"]').click()`);await until('document.querySelector(".heading")?.textContent.includes("Case 02") && !!document.querySelector("#reviewNote")');
  check(await evaluate('document.querySelector("[data-variant=form0]").classList.contains("active") && document.querySelector("[data-tab=memories]").classList.contains("active")'),'return from Props restores the same case, request variant and tab');
  check(await evaluate('document.querySelector("#reviewNote").value==="Keep this review draft after Props" && document.querySelector("#reviewForm [name=instruction]").value==="minor" && document.querySelector("#walked").checked'),'return from Props restores unsaved review notes and ratings');
  await until('!state.busy && !!state.imageURL');
  check(await evaluate('state.token==='+JSON.stringify(previous.token)),'return reuses the existing navigation session');
  await until('Math.abs(window.scrollY-'+previous.scrollY+')<3 && Math.abs(document.querySelector(".sidebar").scrollTop-'+previous.sidebarScroll+')<3');
  check(true,'page and case-list scroll positions restored');
  await evaluate('document.querySelector("[data-tab=navigate]").click();document.querySelector("[data-action=d]").click()');await until('document.querySelector("#navStatus").textContent.includes("2 actions")');
  check(true,'navigation continues from the earlier position');
  check(exceptions.length===0,'no browser runtime exceptions');await call('Browser.close');return;
 }
 if(process.argv.includes('--locator-only')){
  await evaluate('document.querySelector("[data-variant=level2]").click();document.querySelector("[data-tab=navigate]").click();document.querySelector("#startNav").click()');
  await until('document.querySelector("#locator img")?.naturalWidth>0',sid,90000);
  check(await evaluate('!document.querySelector("#overlays") && !document.querySelector("#navStatus").textContent.includes("route end")'),'Level 2 has a location map without route hints');
  const mapBefore=await evaluate('document.querySelector("#locator img").src');
  await evaluate('document.querySelector("[data-action=a]").click()');
  await until('document.querySelector("#locator img")?.naturalWidth>0 && document.querySelector("#locator img").src!=='+JSON.stringify(mapBefore));
  check(await evaluate('document.querySelector("#navStatus").textContent.includes("1 actions")'),'Level 2 movement updates the position map');
  await evaluate('document.querySelector("#locator").scrollIntoView()');await screenshot('position_map');
  await evaluate('document.querySelector("#locator img").click()');
  check(await evaluate('document.querySelector("#lightbox").open && document.querySelector("#largeImage").src.includes("/api/nav/map?")'),'enlarged map retains the position marker');
  await evaluate('document.querySelector("#closeLightbox").click();document.querySelector("[data-tab=photos]").click()');
  await until('document.querySelector(".locator-map")?.naturalWidth>0');
  check(await evaluate('!!document.querySelector(".locator-map")'),'floor-plan tab keeps the current location');
  check(exceptions.length===0,'no browser runtime exceptions');await call('Browser.close');return;
 }
 if(process.argv.includes('--variants-only')){
  check(await evaluate('!document.body.textContent.includes("Authored type and original Level 1")'),'old source instruction section removed');
  check(await evaluate('document.querySelector(".type-note").textContent.includes("L1") && !document.querySelector(".type-note").textContent.includes("C1")'),'base request has only its own guidance');
  check(await evaluate('!document.querySelector("#reviewForm select[name=form]") && !document.querySelector("#reviewForm select[name=props]")'),'unrelated rule and prop checks hidden');
  await evaluate('document.querySelector("[data-variant=form0]").click()');
  check(await evaluate('document.querySelector(".type-note").textContent.includes("C1") && document.querySelector(".badges").textContent.includes("C1")'),'off-limits guidance and badge switch together');
  check(await evaluate('!!document.querySelector("#reviewForm select[name=form]")'),'off-limits rule question is shown');
  check(await evaluate('document.querySelectorAll(".memory").length===3 && document.querySelector("#memories").textContent.includes("breakfast room") && Array.from(document.querySelectorAll(".memory-head b")).some(e=>e.textContent==="B01")'),'off-limits includes the breakfast-room photo memory');
  await evaluate('document.querySelector("#reviewNote").value="Keep this off-limits note";document.querySelector("[data-variant=level2]").click()');
  check(await evaluate('document.querySelector(".type-note").textContent.includes("Everyday need") && !document.querySelector("#workspace").textContent.includes("C1")'),'Level 2 contains no off-limits guidance');
  check(await evaluate('!document.querySelector("#reviewForm select[name=memory]") && !document.querySelector("#reviewForm select[name=grounding]") && !document.querySelector("#reviewForm select[name=form]")'),'Level 2 shows only applicable review questions');
  await evaluate('document.querySelector("[data-tab=photos]").click();document.querySelector("#reveal").click()');
  check(await evaluate('document.querySelectorAll("#expected li").length===4 && !document.querySelector(".photos-grid img[src*=sheet_]")'),'Level 2 answer shows only its four allowed destinations');
  await evaluate('document.querySelector("[data-variant=form0]").click()');
  check(await evaluate('document.querySelector("#reviewNote").value==="Keep this off-limits note"'),'unsaved notes stay with their request');
  await evaluate('document.querySelector("[data-tab=memories]").click()');
  check(await evaluate('document.querySelectorAll(".memory").length===3'),'off-limits retains destination and forbidden-room memories');
 }
 if(process.argv.includes('--memories-only')||process.argv.includes('--variants-only')){
  await evaluate(`document.querySelector('[data-case="2azQ1b91cZZ_case02"]').click()`);await until('document.querySelector(".heading").textContent.includes("Case 02")');
  await evaluate('document.querySelector("[data-tab=memories]").click()');
  check(await evaluate('document.querySelectorAll("#memories .memory").length===2'),'coffee request keeps its two selected memories');
  await evaluate('document.querySelector("[data-variant=form0]").click()');
  check(await evaluate('document.querySelectorAll("#memories .memory").length===3 && document.querySelector("#memories").textContent.includes("Dishes go in the big sink") && document.querySelector("[data-tab=memories]").textContent.includes("(3)")'),'multi-goal adds the sink memory and updates the count');
  check(await evaluate('!document.querySelector("#otherMemories").open && !document.querySelector("#otherMemoryList").children.length'),'other earlier memories stay collapsed by default');
  await evaluate('document.querySelector("#otherMemories").open=true');await until('document.querySelectorAll("#otherMemoryList .memory").length>0');
  check(await evaluate('document.querySelectorAll("#memories .memory").length===3 && !document.querySelector("#otherMemoryList").textContent.includes("Dishes go in the big sink")'),'audit fallback exposes other earlier memories without duplicating selected evidence');
  await evaluate(`document.querySelector('[data-case="2azQ1b91cZZ_case04"]').click()`);await until('document.querySelector(".heading").textContent.includes("Case 04")');
  await evaluate('document.querySelector("[data-tab=memories]").click()');
  check(await evaluate('document.querySelectorAll(".memory").length===2'),'base request excludes form-only memory');
  await evaluate('document.querySelector("[data-variant=form0]").click()');
  check(await evaluate('document.querySelectorAll(".memory").length===4 && document.querySelector("[data-tab=memories]").textContent.includes("(4)")'),'selecting the form includes its extra and first-stop memories and updates the count');
  await evaluate('document.querySelector("[data-variant=level2]").click()');
  check(await evaluate('document.querySelectorAll(".memory").length===0 && document.querySelector("#memories").textContent.includes("no authored memory dependency")'),'everyday need has no unrelated memory cards');
  if(process.argv.includes('--variants-only')){
   await evaluate(`document.querySelector('[data-case="2azQ1b91cZZ_case03"]').click()`);await until('document.querySelector(".heading").textContent.includes("Case 03")');
   check(await evaluate('!document.querySelector("#reviewForm select[name=props]")'),'calculator check hidden for the headphones request');
   await evaluate('document.querySelector("[data-variant=form0]").click()');
   check(await evaluate('!!document.querySelector("#reviewForm select[name=props]")'),'calculator check appears for the calculator request');
   await screenshot('selected_request_only');
  }
  check(exceptions.length===0,'no browser runtime exceptions');
  fs.writeFileSync(path.join(runtime,'memory_filter_checks.json'),JSON.stringify({passed:true,case1:2,case2:2,case2_form:3,case4:2,case4_form:4,level2:0},null,2));
  await call('Browser.close');return;
 }
 await evaluate(`document.querySelector('[data-case="2azQ1b91cZZ_case25"]').click()`);await until('document.querySelector("h1") && document.querySelector(".heading").textContent.includes("Case 25")');
 await evaluate('document.querySelector("[data-tab=photos]").click();document.querySelector("#reveal").click()');
 check(await evaluate('document.querySelectorAll("#expected li").length===3'),'all three acceptable destinations for exclusion case');
 await evaluate('document.querySelector("[data-tab=navigate]").click();document.querySelector("#startNav").click()');await until('!!document.querySelector("#view")',sid,90000);
 const before=await evaluate('document.querySelector("#navStatus").textContent');await evaluate('document.querySelector("[data-action=w]").click()');await until('document.querySelector("#navStatus").textContent!=='+JSON.stringify(before));
 check(await evaluate('document.querySelector("#navStatus").textContent.includes("1 actions")'),'navigation action works');await screenshot('navigation');
 await c('Page.navigate',{url:'http://127.0.0.1:8896/props'});await until('document.querySelectorAll("[data-save-prop]").length===5',sid,90000);await until('Array.from(document.querySelectorAll("#propGrid img")).every(i=>i.complete)');
 await screenshot('props');const failedImages=await evaluate('Array.from(document.querySelectorAll("#propGrid img")).filter(i=>!i.naturalWidth).map(i=>({src:i.src,alt:i.alt}))');
 check(failedImages.length===0,'five prop previews load '+JSON.stringify(failedImages));
 const context=await call('Target.createBrowserContext');const bt=await call('Target.createTarget',{url:'about:blank',browserContextId:context.browserContextId});const {sessionId:blind}=await call('Target.attachToTarget',{targetId:bt.targetId,flatten:true});await call('Runtime.enable',{},blind);await call('Page.enable',{},blind);
 await call('Page.navigate',{url:'http://127.0.0.1:8896/blind'},blind);await until('!!document.querySelector("#blindAnswer")',blind);
 check(await evaluate('!document.querySelector(".type-note") && !document.querySelector("#reveal") && !document.querySelector("#overlays")',blind),'blind page hides types, answers and route overlays');
 check(await evaluate('fetch("/api/catalog?mode=review").then(r=>r.status)',blind)===403,'blind browser cannot read private author data');
 await call('Page.navigate',{url:'http://127.0.0.1:8896/naturalness'},blind);await until('document.querySelectorAll("[data-natural]").length===62',blind);console.log('PASS 62 naturalness requests');
 await c('Page.navigate',{url:'http://127.0.0.1:8896/review'});await until('!!document.querySelector("#reviewForm")');await c('Emulation.setDeviceMetricsOverride',{width:420,height:900,deviceScaleFactor:1,mobile:true});await sleep(300);
 check(await evaluate('document.documentElement.scrollWidth<=window.innerWidth+1'),'mobile layout fits viewport');await screenshot('mobile');
 check(exceptions.length===0,'no browser runtime exceptions');
 fs.writeFileSync(path.join(runtime,'browser_checks.json'),JSON.stringify({passed:true,exceptions,screenshots:fs.readdirSync(shots)},null,2));
 await call('Browser.close');
}
main().catch(e=>{console.error(e.stack);process.exitCode=1;}).finally(()=>{if(ws)ws.close();chrome.kill();});
