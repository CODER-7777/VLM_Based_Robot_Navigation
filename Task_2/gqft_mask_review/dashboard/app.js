'use strict';
(() => {
  const D = window.GQFT_DATA, $ = id => document.getElementById(id);
  const ARMS = Object.keys(D.provenance.checkpoints), GT = '#ee00bb';
  const names = Object.fromEntries(ARMS.map(a => [a, D.provenance.checkpoints[a].label]));
  const short = {reference:'Reference',masked_only:'Soft mask',yaw_local_only:'Yaw-local',masked_yaw_local:'Mask + yaw',pretrained_yaw:'Original yaw'};
  const colors = {...Object.fromEntries(ARMS.map(a => [a,D.provenance.checkpoints[a].color])),masked_only:'#65cd98',yaw_local_only:'#b092ff',pretrained_yaw:'#7aaacb'};
  const state = {leg:'0',a:'pretrained_yaw',b:'masked_yaw_local',pose:24,tab:'compare',visible:new Set(ARMS),
    error:'ground',history:24,pair:0,layer:'attention_weights',opacity:.7,showGT:true,showFuture:true,
    viewport:null,sort:'mean_ground_error_m',descending:false,playing:false};
  let timer = null, images = {}, dragging = null;
  const windowData = () => D.legs[state.leg];
  const escape = text => String(text).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt = (x,n=2) => Number.isFinite(x) ? x.toFixed(n) : '—';
  const delta = (a,b) => (b-a)/Math.max(Math.abs(a),1e-12)*100;
  function percentLabel(value) { return `${value>0?'+':''}${fmt(value,1)}%`; }
  function tooltip(text,event) {
    const t=$('tooltip');t.textContent=text;t.hidden=false;
    t.style.left=Math.max(8,Math.min(event.clientX+14,window.innerWidth-285))+'px';
    t.style.top=Math.max(8,Math.min(event.clientY+12,window.innerHeight-105))+'px';
  }
  function hideTooltip(){ $('tooltip').hidden=true; }
  function download(name,body,type='application/json') {
    const blob=new Blob([body],{type}),url=URL.createObjectURL(blob),a=document.createElement('a');
    a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  function noteKey(){return `gqft-note-${D.pilot}-ep629-leg${state.leg}`;}
  function readNote(){try{return localStorage.getItem(noteKey())||'';}catch{return '';}}
  function stop(){if(timer)clearInterval(timer);timer=null;state.playing=false;$('play').textContent='▶';$('play').setAttribute('aria-label','Play trajectory');}
  function setPose(value){state.pose=Math.max(0,Math.min(24,Math.round(Number(value))));renderCompare();}
  function setLeg(leg){
    if(!D.legs[String(leg)])return;stop();state.leg=String(leg);state.viewport=null;state.pose=24;
    $('notes').value=readNote();$('notes-status').textContent='';render();
  }
  function setTab(tab){
    if(!['compare','attention','validation'].includes(tab))return;stop();state.tab=tab;
    document.querySelectorAll('.tab').forEach(b=>{const active=b.dataset.tab===tab;b.classList.toggle('active',active);b.setAttribute('aria-selected',String(active));b.tabIndex=active?0:-1;});
    document.querySelectorAll('.tab-view').forEach(v=>v.hidden=v.id!==`view-${tab}`);
    $('scope-badge').textContent=tab==='validation'?'FIXED VALIDATION WINDOWS':'EPISODE WINDOW';
    render();
  }
  function metricCard(label,value,unit,note,cls=''){
    return `<div class="metric-card"><div class="label">${label}</div><div class="metric-value ${cls}">${value}<small>${unit}</small></div><div class="metric-note">${note}</div></div>`;
  }
  function initSelects(){
    for(const side of ['a','b'])$('model-'+side).innerHTML=ARMS.map(a=>`<option value="${a}">${names[a]}</option>`).join('');
    $('validation-history').innerHTML=D.validation.reference.histories.map(r=>`<option value="${r.history}">${r.history} pairs</option>`).join('');
  }
  function renderLegs(){
    $('leg-list').innerHTML=Object.entries(D.legs).map(([leg,w])=>{
      const begin=w.inputs.window_start_episode_frame;
      return `<button class="leg-button ${leg===state.leg?'active':''}" data-leg="${leg}" aria-pressed="${leg===state.leg}"><div><strong>Leg ${leg.padStart(2,'0')}</strong><small>FRAMES ${begin}–${begin+24}</small></div><span class="leg-number">↗</span></button>`;
    }).join('');
    $('leg-list').querySelectorAll('button').forEach(b=>b.onclick=()=>setLeg(b.dataset.leg));
  }
  function render(){
    renderLegs();$('model-a').value=state.a;$('model-b').value=state.b;
    $('leg-heading').textContent='Leg '+state.leg.padStart(2,'0');
    const begin=windowData().inputs.window_start_episode_frame;
    $('window-description').textContent=`Recorded frames ${begin}–${begin+24} · 24 flow pairs · identical inputs and ground truth`;
    if(state.tab==='compare')renderCompare();
    else if(state.tab==='attention')renderAttention();
    else renderValidation();
  }
  function setupCanvas(canvas,ratio=1.35){
    const width=canvas.getBoundingClientRect().width||500,height=width/ratio,dpr=Math.min(devicePixelRatio||1,2);
    canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);
    const ctx=canvas.getContext('2d');ctx.scale(dpr,dpr);
    return {ctx,width,height};
  }
  function transform(width,height){
    const v=state.viewport||{cx:480,cy:410,zoom:1};
    const scale=Math.min(width/960,height/830)*v.zoom;
    return {scale,x:x=>width/2+(x-v.cx)*scale,y:y=>height/2+(y-v.cy)*scale};
  }
  function drawPath(ctx,points,color,map,options={}){
    const end=options.end??24;ctx.save();ctx.strokeStyle=color;ctx.lineWidth=options.width||2.4;
    ctx.setLineDash(options.dashed?[4,5]:[]);ctx.globalAlpha=options.alpha??1;ctx.beginPath();
    let fresh=true;
    for(let i=0;i<=end;i++){
      const point=points[i];
      if(!point||!point.every(Number.isFinite)||(options.valid&&!options.valid[i])){fresh=true;continue;}
      if(fresh){ctx.moveTo(map.x(point[0]),map.y(point[1]));fresh=false;}else ctx.lineTo(map.x(point[0]),map.y(point[1]));
    }
    ctx.stroke();ctx.restore();
  }
  function marker(ctx,x,y,color,kind='circle',size=5){
    ctx.save();ctx.strokeStyle='#13171c';ctx.fillStyle=color;ctx.lineWidth=2;
    if(kind==='cross'){ctx.strokeStyle=color;ctx.lineWidth=2.5;ctx.beginPath();ctx.moveTo(x-size,y-size);ctx.lineTo(x+size,y+size);ctx.moveTo(x+size,y-size);ctx.lineTo(x-size,y+size);ctx.stroke();}
    else{ctx.beginPath();ctx.arc(x,y,size,0,Math.PI*2);ctx.fill();ctx.stroke();}ctx.restore();
  }
  function drawOverlay(side){
    const arm=state[side],w=windowData(),p=w.predictions[arm],canvas=$('overlay-'+side);
    const {ctx,width,height}=setupCanvas(canvas,innerWidth>1800?1.5:innerWidth<620?1.3:1.35),t=transform(width,height);
    canvas._map=t;ctx.fillStyle='#10171e';ctx.fillRect(0,0,width,height);
    const image=images[state.leg]?.[0];
    if(image?.complete&&image.naturalWidth)ctx.drawImage(image,t.x(0),t.y(0),960*t.scale,540*t.scale);
    ctx.fillStyle='#1d2630';ctx.fillRect(t.x(0),t.y(540),960*t.scale,270*t.scale);
    ctx.save();ctx.beginPath();ctx.rect(t.x(0),t.y(540),960*t.scale,270*t.scale);ctx.clip();ctx.strokeStyle='#344150';ctx.lineWidth=.6;
    for(let y=t.y(540)-width;y<t.y(810)+width;y+=22){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(width,y+width*.35);ctx.stroke();}ctx.restore();
    ctx.strokeStyle='#b3bcc8';ctx.setLineDash([3,5]);ctx.lineWidth=.8;
    for(const y of [540,810]){ctx.beginPath();ctx.moveTo(t.x(0),t.y(y));ctx.lineTo(t.x(960),t.y(y));ctx.stroke();}ctx.setLineDash([]);
    const labelY=t.y(540)+16;
    if(labelY>0&&labelY<height){ctx.fillStyle='#bac5d1';ctx.font='9px system-ui';ctx.fillText('EXTENDED QUERY CANVAS',Math.max(12,t.x(0)+12),labelY);}
    if(state.showFuture){
      if(state.showGT)drawPath(ctx,w.reference_uv_px,GT,t,{alpha:.35,width:2});
      drawPath(ctx,p.uv_px,colors[arm],t,{alpha:.3,valid:p.positive_depth,dashed:true});
    }
    if(state.showGT)drawPath(ctx,w.reference_uv_px,GT,t,{end:state.pose,width:2.8});
    drawPath(ctx,p.uv_px,colors[arm],t,{end:state.pose,valid:p.positive_depth,dashed:true,alpha:.85,width:2});
    drawPath(ctx,p.uv_px,colors[arm],t,{end:state.pose,valid:p.prefix,width:2.8});
    if(state.showGT){const q=w.reference_uv_px[state.pose];marker(ctx,t.x(q[0]),t.y(q[1]),GT,'cross',6);}
    if(p.positive_depth[state.pose]){const q=p.uv_px[state.pose];marker(ctx,t.x(q[0]),t.y(q[1]),colors[arm],'circle',5);}
    const origin=w.reference_uv_px[0];ctx.fillStyle='white';ctx.fillRect(t.x(origin[0])-3,t.y(origin[1])-3,6,6);
    $('image-title-'+side).innerHTML=`<span class="model-dot" style="background:${colors[arm]}"></span> ${names[arm]}`;
    $('image-foot-'+side).textContent=`POSE ${String(state.pose).padStart(2,'0')}  ·  GROUND ${fmt(p.ground_error_cm[state.pose],1)} cm  ·  PIXEL ${fmt(p.pixel_error_px[state.pose],1)} px  ·  ${p.prefix[state.pose]?'INSIDE ANALYTIC PREFIX':'BEYOND ANALYTIC PREFIX'}`;
  }
  function renderCompare(){
    if(state.tab!=='compare')return;
    const w=windowData(),a=w.metrics[state.a],b=w.metrics[state.b],change=delta(a.mean_ground_error_m,b.mean_ground_error_m);
    $('metric-grid').innerHTML=
      metricCard('Model B · ground mean',fmt(b.mean_ground_error_m*100,2),'cm','All 24 post-origin points')+
      metricCard('Model B · endpoint',fmt(b.endpoint_ground_error_m*100,2),'cm','Ground-position error at pose 24')+
      metricCard('Model B · pixel mean',fmt(b.mean_pixel_error_px,2),'px','Same reference-valid points')+
      metricCard('Ground mean · B vs A',percentLabel(change),'',change<0?'Lower error than Model A':change>0?'Higher error than Model A':'Same selected model',change<0?'positive':change>0?'negative':'');
    $('legend-a').style.background=colors[state.a];$('legend-b').style.background=colors[state.b];
    $('pose').value=state.pose;$('pose-label').textContent=`Pose ${state.pose} / 24`;
    $('pose-detail').innerHTML=`<span>A &nbsp;${fmt(w.predictions[state.a].ground_error_cm[state.pose],2)} cm</span><br><span>B &nbsp;${fmt(w.predictions[state.b].ground_error_cm[state.pose],2)} cm</span>`;
    drawOverlay('a');drawOverlay('b');renderToggles();renderTrajectoryCharts();renderTable();
  }
  function renderToggles(){
    $('model-toggles').innerHTML=ARMS.map(arm=>`<button class="model-toggle" data-arm="${arm}" aria-pressed="${state.visible.has(arm)}"><span class="model-dot" style="background:${colors[arm]}"></span>${names[arm]}</button>`).join('');
    $('model-toggles').querySelectorAll('button').forEach(button=>button.onclick=()=>{
      const arm=button.dataset.arm;if(state.visible.has(arm))state.visible.delete(arm);else state.visible.add(arm);renderToggles();renderTrajectoryCharts();
    });
  }
  function chart(container,series,options={}){
    const W=600,H=320,p={l:58,r:20,t:32,b:options.legend?74:45};
    let xs=series.flatMap(s=>s.points.map(q=>q[0])),ys=series.flatMap(s=>s.points.map(q=>q[1]));
    if(!xs.length){xs=[0,1];ys=[0,1];}
    let x0=options.xmin??Math.min(...xs),x1=options.xmax??Math.max(...xs),y0=options.ymin??Math.min(0,...ys),y1=options.ymax??Math.max(...ys);
    if(x1-x0<1e-8){x0-=.1;x1+=.1;}if(y1-y0<1e-8){y1=y0+.1;}
    if(options.equal){const dx=(x1-x0)*.12,dy=(y1-y0)*.12;x0-=dx;x1+=dx;y0-=dy;y1+=dy;const scale=Math.min((W-p.l-p.r)/(x1-x0),(H-p.t-p.b)/(y1-y0));const cx=(x0+x1)/2,cy=(y0+y1)/2;x0=cx-(W-p.l-p.r)/scale/2;x1=cx+(W-p.l-p.r)/scale/2;y0=cy-(H-p.t-p.b)/scale/2;y1=cy+(H-p.t-p.b)/scale/2;}
    else if(options.ymax===undefined)y1+=(y1-y0)*.08;
    const X=v=>p.l+(v-x0)/(x1-x0)*(W-p.l-p.r),Y=v=>H-p.b-(v-y0)/(y1-y0)*(H-p.t-p.b);
    let svg=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${escape(options.title||'Trajectory chart')}"><text x="${p.l}" y="16" fill="#d5dce4" font-size="12">${escape(options.title||'')}</text>`;
    for(let i=0;i<=4;i++){
      const y=y0+(y1-y0)*i/4,x=x0+(x1-x0)*i/4;
      svg+=`<line class="grid" x1="${p.l}" y1="${Y(y)}" x2="${W-p.r}" y2="${Y(y)}"/><text class="chart-axis" x="${p.l-9}" y="${Y(y)+4}" text-anchor="end">${fmt(y,options.equal?2:y1<2?2:1)}</text><text class="chart-axis" x="${X(x)}" y="${H-p.b+19}" text-anchor="middle">${fmt(x,options.equal?2:0)}</text>`;
    }
    if(options.threshold!==undefined)svg+=`<line x1="${p.l}" y1="${Y(options.threshold)}" x2="${W-p.r}" y2="${Y(options.threshold)}" stroke="#f6ad73" stroke-dasharray="5 4"/><text x="${W-p.r}" y="${Y(options.threshold)-6}" text-anchor="end" fill="#f6ad73" font-size="10">≤ ${options.threshold}</text>`;
    for(const s of series){
      const path=s.points.map((q,i)=>`${i?'L':'M'}${X(q[0]).toFixed(2)},${Y(q[1]).toFixed(2)}`).join(' ');
      svg+=`<path d="${path}" fill="none" stroke="${s.color}" stroke-width="${s.width||2}" opacity="${s.opacity??1}" stroke-linejoin="round"/>`;
      const cursor=options.equal?s.points[state.pose]:null;
      if(cursor)svg+=`<circle cx="${X(cursor[0])}" cy="${Y(cursor[1])}" r="4" fill="${s.color}" stroke="#101317" stroke-width="1.5"/>`;
    }
    if(options.cursor!==undefined)svg+=`<line x1="${X(options.cursor)}" y1="${p.t}" x2="${X(options.cursor)}" y2="${H-p.b}" stroke="#edf0f4" stroke-width="1" stroke-dasharray="3 4" opacity=".65"/>`;
    svg+=`<text class="axis-label" x="${(W+p.l-p.r)/2}" y="${H-p.b+36}" text-anchor="middle">${escape(options.xlabel||'')}</text>`;
    if(options.legend)series.forEach((s,i)=>{const col=i%3,row=Math.floor(i/3),x=p.l+col*176,y=H-22+row*15;svg+=`<circle cx="${x}" cy="${y-3}" r="3" fill="${s.color}"/><text x="${x+9}" y="${y}" fill="#aab5c3" font-size="9">${escape(s.label||'')}</text>`;});
    svg+=`<rect class="hover-zone" x="${p.l}" y="${p.t}" width="${W-p.l-p.r}" height="${H-p.t-p.b}"/></svg>`;
    container.innerHTML=svg;
    const zone=container.querySelector('.hover-zone');
    zone.onpointerleave=hideTooltip;
    if(options.scrub){zone.onpointermove=event=>{
      const rect=container.querySelector('svg').getBoundingClientRect(),sx=(event.clientX-rect.left)/rect.width*W;
      const pose=Math.max(0,Math.min(24,Math.round(x0+(sx-p.l)/(W-p.l-p.r)*(x1-x0))));
      if(state.pose!==pose)setPose(pose);
      tooltip(`Pose ${pose} · A ${fmt(windowData().predictions[state.a][state.error==='ground'?'ground_error_cm':'pixel_error_px'][pose],2)} / B ${fmt(windowData().predictions[state.b][state.error==='ground'?'ground_error_cm':'pixel_error_px'][pose],2)} ${state.error==='ground'?'cm':'px'}`,event);
    };}
    else if(options.interactive){zone.onpointermove=event=>{
      const rect=container.querySelector('svg').getBoundingClientRect(),sx=(event.clientX-rect.left)/rect.width*W;
      const value=x0+(sx-p.l)/(W-p.l-p.r)*(x1-x0),available=series[0]?.points||[];
      const nearest=available.reduce((best,q)=>Math.abs(q[0]-value)<Math.abs(best[0]-value)?q:best,available[0]||[0,0]);
      tooltip(`${options.xlabel}: ${nearest[0]} · `+series.map(s=>`${s.label}: ${fmt(s.points.find(q=>q[0]===nearest[0])?.[1],3)}`).join(' / '),event);
    };}
  }
  function renderTrajectoryCharts(){
    const w=windowData(),selected=ARMS.filter(a=>state.visible.has(a));
    const series=[{color:GT,width:3,points:w.reference_ground.map(q=>[q[1],q[0]])},...selected.map(arm=>({color:colors[arm],width:arm===state.a||arm===state.b?2.7:1.4,opacity:arm===state.a||arm===state.b?1:.65,points:w.predictions[arm].ground.map(q=>[q[1],q[0]])}))];
    chart($('ground-chart'),series,{equal:true,title:'Ground trajectory · forward / left (m)',xlabel:'Left from window start (m)'});
    const key=state.error==='ground'?'ground_error_cm':'pixel_error_px';
    chart($('error-chart'),selected.map(arm=>({color:colors[arm],width:arm===state.a||arm===state.b?2.5:1.5,points:w.predictions[arm][key].map((v,i)=>[i,v])})),{xmin:0,xmax:24,ymin:0,cursor:state.pose,title:state.error==='ground'?'Per-pose ground error (cm)':'Per-pose projected error (px)',xlabel:'Pose after window start',scrub:true});
  }
  function renderTable(){
    const w=windowData(),sorted=[...ARMS].sort((a,b)=>(w.metrics[a][state.sort]-w.metrics[b][state.sort])*(state.descending?-1:1));
    const keys=['mean_ground_error_m','endpoint_ground_error_m','mean_pixel_error_px','endpoint_pixel_error_px'];
    const best=Object.fromEntries(keys.map(key=>[key,Math.min(...ARMS.map(a=>w.metrics[a][key]))]));
    $('metrics-table').querySelector('tbody').innerHTML=sorted.map(arm=>{
      const m=w.metrics[arm];return `<tr data-model="${arm}" class="${arm===state.b?'chosen':''}" tabindex="0" aria-label="Compare ${names[arm]}"><td><span class="model-dot" style="background:${colors[arm]}"></span>${names[arm]}</td>${keys.map((key,i)=>`<td class="${m[key]===best[key]?'best-cell':''}">${fmt(m[key]*(i<2?100:1),2)} ${i<2?'cm':'px'}</td>`).join('')}<td>${m.accepted_prefix_points} / 25</td></tr>`;
    }).join('');
    $('metrics-table').querySelectorAll('tbody tr').forEach(tr=>{const choose=()=>{state.b=tr.dataset.model;$('model-b').value=state.b;renderCompare();};tr.onclick=choose;tr.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose();}};});
  }
  function imageMap(arm,key){return windowData().attention[arm]?.[key]?.[state.pair]||null;}
  const heatStops=[[22,38,58],[53,65,128],[134,75,163],[230,123,112],[255,241,164]];
  function heatColor(value){const v=Math.max(0,Math.min(1,value))*4,i=Math.min(3,Math.floor(v)),t=v-i;return heatStops[i].map((x,k)=>Math.round(x*(1-t)+heatStops[i+1][k]*t));}
  function drawAttention(side,max){
    const raw=side==='raw',arm=raw?null:state[side],canvas=$('attention-'+side),{ctx,width,height}=setupCanvas(canvas,16/9),image=images[state.leg]?.[state.pair];
    ctx.fillStyle='#121922';ctx.fillRect(0,0,width,height);
    if(image?.complete&&image.naturalWidth)ctx.drawImage(image,0,0,width,height);
    const map=arm?imageMap(arm,state.layer):null;
    if(map){for(let row=0;row<6;row++)for(let col=0;col<10;col++){
      const normalized=map[row][col]/Math.max(max,1e-9),value=state.layer==='attention_weights'?Math.pow(normalized,.35):normalized;
      ctx.fillStyle=`rgba(${heatColor(value).join(',')},${state.opacity})`;
      ctx.fillRect(col*width/10,row*height/6,width/10+.5,height/6+.5);
    }ctx.strokeStyle='#ffffff25';ctx.lineWidth=.6;for(let col=1;col<10;col++){ctx.beginPath();ctx.moveTo(col*width/10,0);ctx.lineTo(col*width/10,height);ctx.stroke();}for(let row=1;row<6;row++){ctx.beginPath();ctx.moveTo(0,row*height/6);ctx.lineTo(width,row*height/6);ctx.stroke();}}
    if(raw)$('raw-foot').textContent=`EP629 · LEG ${state.leg.padStart(2,'0')} · RECORDED FRAME ${windowData().inputs.window_start_episode_frame+state.pair}`;
    else{
      $('attention-title-'+side).textContent=names[arm];
      const values=map?.flat();
      $('attention-foot-'+side).textContent=map?`MIN ${fmt(Math.min(...values),4)} · MAX ${fmt(Math.max(...values),4)} · ${state.layer==='attention_weights'?'SUM '+fmt(values.reduce((a,b)=>a+b,0),4):'PRIOR / COVERAGE'}`:'This model has no stored mask prior. Raw source is shown.';
    }
    canvas.onpointermove=event=>{
      if(!map)return;const rect=canvas.getBoundingClientRect(),col=Math.max(0,Math.min(9,Math.floor((event.clientX-rect.left)/rect.width*10))),row=Math.max(0,Math.min(5,Math.floor((event.clientY-rect.top)/rect.height*6)));
      $('cell-readout').textContent=`${names[arm]} · row ${row}, column ${col} · ${state.layer.replaceAll('_',' ')} = ${fmt(map[row][col],6)}`;
    };
  }
  function renderAttention(){
    if(state.tab!=='attention')return;
    const keys=state.layer==='attention_weights'?ARMS:[state.a,state.b],values=keys.flatMap(a=>imageMap(a,state.layer)?.flat()||[]);
    const max=state.layer==='attention_weights'?Math.max(...values,1e-6):1;
    $('scale-min').textContent='0';$('scale-max').textContent=fmt(max,4);
    for(const side of ['raw','a','b'])drawAttention(side,max);
  }
  function validationRow(arm){return D.validation[arm].histories.find(row=>row.history===state.history);}
  function renderValidation(){
    if(state.tab!=='validation')return;
    $('validation-history').value=state.history;
    const a=validationRow(state.a),b=validationRow(state.b),change=delta(a.ade_px,b.ade_px);
    $('validation-cards').innerHTML=metricCard('Model B · ADE',fmt(b.ade_px,2),'px',`History ${state.history} · 104 fixed windows`)+metricCard('Model B · FDE',fmt(b.fde_px,2),'px','Reference-valid endpoint scoring')+metricCard('ADE · B vs A',percentLabel(change),'',change<0?'Lower error than Model A':'Higher or equal error than Model A',change<0?'positive':change>0?'negative':'')+metricCard('Model B · ambiguity',fmt(b.signature_ambiguity,3),'',`Gate limit ≤ 0.05 · ${b.signature_close_pairs} close pairs`,b.signature_ambiguity<=.05?'positive':'negative');
    $('validation-table').querySelector('tbody').innerHTML=ARMS.map(arm=>{
      const row=validationRow(arm),selected=D.validation[arm].shortest_sufficient_history;
      return `<tr><td><span class="model-dot" style="background:${colors[arm]}"></span>${names[arm]}</td><td>${fmt(row.ade_px,3)}</td><td>${fmt(row.fde_px,3)}</td><td class="${row.signature_ambiguity<=.05?'positive':'negative'}">${fmt(row.signature_ambiguity,3)}</td><td>${row.signature_close_pairs} / ${row.signature_cross_sequence_eligible}</td><td class="${selected===null?'negative':'positive'}">${selected===null?'None passed':selected+' pairs'}</td></tr>`;
    }).join('');
    const series=(key)=>ARMS.map(arm=>({color:colors[arm],label:short[arm],width:arm===state.a||arm===state.b?2.5:1.3,points:D.validation[arm].histories.map(r=>[r.history,r[key]])}));
    chart($('history-chart'),series('ade_px'),{title:'Validation ADE (px)',xlabel:'Input history (flow pairs)',ymin:0,cursor:state.history,legend:true,interactive:true});
    chart($('ambiguity-chart'),series('signature_ambiguity'),{title:'Conditional ambiguity fraction',xlabel:'Input history (flow pairs)',ymin:0,ymax:.7,threshold:.05,cursor:state.history,legend:true,interactive:true});
    chart($('training-chart'),ARMS.filter(arm=>arm!=='pretrained_yaw').map(arm=>({label:short[arm],color:colors[arm],points:D.training[arm].map(r=>[r.step,r.ade_px])})),{title:'Training-time mixed-history validation ADE (px)',xlabel:'Training step',ymin:0,legend:true,interactive:true});
    $('provenance').innerHTML=`<h3>Camera and protocol</h3><p>${D.provenance.camera.width} × ${D.provenance.camera.height} pixels · height ${D.provenance.camera.camera_height_m} m · pitch ${D.provenance.camera.pitch_down_deg}° down · query (${D.provenance.query_px.join(', ')}) · no fitted scale or rotation. Episode image metrics exclude the origin; the fixed validation pixel metrics include it.</p><h3>History selection</h3><p>Among 4, 8, 12, 16, 20, 24, 30 pairs: full-reference retrieval gap within 2% of the best equal/longer history, plus ambiguity ≤ 0.05 among cosine-near pairs (cosine ≥ 0.995 and curve gap &gt; 0.10 m). Zero close pairs can produce zero measured ambiguity; inspect the close-pair counts. These are cross-sequence pairs, not necessarily different houses.</p>`+ARMS.map(arm=>`<h3>${names[arm]} · step ${D.provenance.checkpoints[arm].step}</h3><p>Spatial policy: ${escape(D.provenance.checkpoints[arm].config.spatial_mask)} · integration: ${escape(D.provenance.checkpoints[arm].config.motion_integration)}</p><code>${D.provenance.checkpoints[arm].sha256}</code>`).join('');
  }
  function fitPaths(){
    const w=windowData(),points=[...w.reference_uv_px,...w.predictions[state.a].uv_px.filter((_,i)=>w.predictions[state.a].positive_depth[i]),...w.predictions[state.b].uv_px.filter((_,i)=>w.predictions[state.b].positive_depth[i])];
    const xs=points.map(p=>p[0]),ys=points.map(p=>p[1]),x0=Math.min(...xs)-45,x1=Math.max(...xs)+45,y0=Math.min(...ys)-35,y1=Math.max(...ys)+35;
    state.viewport={cx:(x0+x1)/2,cy:(y0+y1)/2,zoom:Math.min(4,Math.min(960/Math.max(x1-x0,300),830/Math.max(y1-y0,180)))};renderCompare();
  }
  function bindCanvas(side){
    const canvas=$('overlay-'+side);
    canvas.onwheel=event=>{event.preventDefault();const current=state.viewport||{cx:480,cy:410,zoom:1};state.viewport={...current,zoom:Math.max(.6,Math.min(7,current.zoom*Math.exp(-event.deltaY*.0015)))};drawOverlay('a');drawOverlay('b');};
    canvas.addEventListener('wheel',()=>{}, {passive:false});
    canvas.onpointerdown=event=>{canvas.setPointerCapture(event.pointerId);const v=state.viewport||{cx:480,cy:410,zoom:1};dragging={x:event.clientX,y:event.clientY,view:{...v},scale:canvas._map.scale};};
    canvas.onpointermove=event=>{if(!dragging)return;state.viewport={...dragging.view,cx:dragging.view.cx-(event.clientX-dragging.x)/dragging.scale,cy:dragging.view.cy-(event.clientY-dragging.y)/dragging.scale};drawOverlay('a');drawOverlay('b');};
    canvas.onpointerup=canvas.onpointercancel=()=>{dragging=null;};
    canvas.ondblclick=()=>{state.viewport=null;drawOverlay('a');drawOverlay('b');};
  }
  function bind(){
    for(const side of ['a','b']){$('model-'+side).onchange=event=>{state[side]=event.target.value;render();};bindCanvas(side);}
    $('swap').onclick=()=>{[state.a,state.b]=[state.b,state.a];render();};
    document.querySelectorAll('.tab').forEach(button=>{button.onclick=()=>setTab(button.dataset.tab);button.onkeydown=event=>{if(event.key==='ArrowRight'||event.key==='ArrowLeft'){event.preventDefault();const tabs=['compare','attention','validation'],index=tabs.indexOf(state.tab),next=tabs[(index+(event.key==='ArrowRight'?1:2))%3];setTab(next);$('tab-'+next).focus();}};});
    $('pose').oninput=event=>{stop();setPose(event.target.value);};
    $('play').onclick=()=>{if(state.playing){stop();return;}if(state.pose===24)state.pose=0;state.playing=true;$('play').textContent='Ⅱ';$('play').setAttribute('aria-label','Pause trajectory');timer=setInterval(()=>{if(state.pose>=24){stop();return;}setPose(state.pose+1);},220);};
    $('show-gt').onchange=event=>{state.showGT=event.target.checked;renderCompare();};
    $('show-future').onchange=event=>{state.showFuture=event.target.checked;renderCompare();};
    $('fit-paths').onclick=fitPaths;
    $('reset').onclick=()=>{stop();state.viewport=null;state.pose=24;state.showGT=true;state.showFuture=true;$('show-gt').checked=true;$('show-future').checked=true;state.visible=new Set(ARMS);render();};
    $('error-metric').onchange=event=>{state.error=event.target.value;renderTrajectoryCharts();};
    $('attention-pair').onchange=event=>{state.pair=Number(event.target.value);renderAttention();};
    $('attention-layer').onchange=event=>{state.layer=event.target.value;renderAttention();};
    $('heat-opacity').oninput=event=>{state.opacity=Number(event.target.value)/100;renderAttention();};
    $('validation-history').onchange=event=>{state.history=Number(event.target.value);renderValidation();};
    document.querySelectorAll('[data-sort]').forEach(button=>button.onclick=()=>{const key=button.dataset.sort;state.descending=state.sort===key?!state.descending:false;state.sort=key;renderTable();});
    document.querySelectorAll('[data-save]').forEach(button=>button.onclick=()=>{const side=button.dataset.save,a=document.createElement('a');a.download=`ep629_leg${state.leg.padStart(2,'0')}_${state[side]}_pose${state.pose}.png`;a.href=$('overlay-'+side).toDataURL('image/png');a.click();});
    $('notes').oninput=()=>{try{localStorage.setItem(noteKey(),$('notes').value);$('notes-status').textContent='Saved locally in this browser.';}catch{$('notes-status').textContent='Browser storage is unavailable. Export the leg data to keep this note.';}};
    $('download-data').onclick=event=>{event.preventDefault();download(`ep629_leg${state.leg.padStart(2,'0')}_review.json`,JSON.stringify({pilot:D.pilot,provenance:D.provenance,leg:state.leg,notes:$('notes').value,metrics:windowData().metrics,predictions:windowData().predictions,reference_uv_px:windowData().reference_uv_px,reference_ground:windowData().reference_ground},null,2));};
    $('export-csv').onclick=()=>{const lines=['episode,leg,model,ground_mean_cm,ground_endpoint_cm,pixel_mean_px,pixel_endpoint_px,accepted_poses'];for(const [leg,w]of Object.entries(D.legs))for(const arm of ARMS){const m=w.metrics[arm];lines.push([629,leg,arm,m.mean_ground_error_m*100,m.endpoint_ground_error_m*100,m.mean_pixel_error_px,m.endpoint_pixel_error_px,m.accepted_prefix_points].join(','));}download('episode629_all_legs_metrics.csv',lines.join('\n'),'text/csv');};
    document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
    let pending;window.addEventListener('resize',()=>{clearTimeout(pending);pending=setTimeout(render,100);});
  }
  async function loadImages(){
    const pending=[];for(const [leg,w]of Object.entries(D.legs)){images[leg]={};for(const [pair,src]of Object.entries(w.images)){const image=new Image();images[leg][pair]=image;pending.push(new Promise(resolve=>{image.onload=resolve;image.onerror=()=>{window.gqftDashboard.errors.push(`Image load failed: ${leg}/${pair}`);resolve();};image.src=src;}));}}
    await Promise.all(pending);
  }
  window.gqftDashboard={state,data:D,errors:[],setLeg,setTab,setPose,render,fitPaths,ready:false};
  window.addEventListener('error',event=>window.gqftDashboard.errors.push(String(event.message)));
  window.addEventListener('unhandledrejection',event=>window.gqftDashboard.errors.push(String(event.reason)));
  initSelects();bind();$('notes').value=readNote();render();
  loadImages().then(()=>{render();window.gqftDashboard.ready=true;});
})();
