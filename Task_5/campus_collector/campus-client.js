'use strict';
(async()=>{
  const response=await fetch('/auth/me');
  if(!response.ok){location.href='/';return}
  const {username,role}=await response.json();
  const style=document.createElement('link');style.rel='stylesheet';style.href='/campus.css';document.head.appendChild(style);
  const bar=document.createElement('div');bar.className='campus-account';
  const message=document.createElement('span');message.textContent='Signed in as '+username+' · independent recording session · uploads save directly to the research server';
  const recover=document.createElement('button');recover.textContent='Recover uploads';recover.onclick=()=>CampusUploads.show();
  document.addEventListener('campus-pending-media',e=>{recover.textContent=e.detail.count?'Recover uploads ('+e.detail.count+')':'Recover uploads'});
  await CampusUploads.setAccount(username);
  const signout=document.createElement('button');signout.textContent='Save, then sign out';
  bar.append(message,recover,signout);document.body.prepend(bar);
  if(role==='admin'){
    const link=document.createElement('a');link.href='/admin';link.textContent='Study administration';
    link.style.color='white';bar.insertBefore(link,recover);
  }
  const field=document.getElementById('annotator');
  localStorage.setItem('collector_v2_username',username);
  if(field){field.value=username;field.readOnly=true;field.title='Your authenticated contributor ID';}
  const changeUser=document.getElementById('new-user');if(changeUser)changeUser.hidden=true;
  // The identity is enforced by the server as well; this only keeps the UI clear.
  const busy=()=>active||voice||screen||screenStarting||pendingUploads||currentState?.processing||CampusUploads.pending()>0;
  const protect=()=>{if(field&&field.value!==username)field.value=username;signout.disabled=!!busy();};
  const timer=setInterval(protect,800);
  signout.onclick=async()=>{
    if(busy()){alert('STOP & save, resolve pending uploads and wait for MP4 preparation first.');return}
    signout.disabled=true;
    try{
      const result=await fetch('/auth/logout',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
      const value=await result.json();
      if(!result.ok){alert(value.error||'Finish recording and uploads before signing out.');return;}
      clearInterval(timer);location.href='/';
    }finally{signout.disabled=false;}
  };
})();
