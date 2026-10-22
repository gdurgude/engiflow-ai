const $=id=>document.getElementById(id);let projects=[],current='',csrf='',signedInUser=null;
let signupMode=false;
function toggleAuth(mode){signupMode=mode;$('authHeading').textContent=mode?'Create your account':'Welcome back';$('authDescription').textContent=mode?'Get your own private EngiFlow workspace.':'Sign in to access your private projects and documents.';$('nameField').hidden=!mode;$('authName').required=mode;$('authPassword').autocomplete=mode?'new-password':'current-password';$('authSubmit').textContent=mode?'Create account →':'Sign in →';$('authSwitchText').textContent=mode?'Already have an account?':'New to EngiFlow?';$('authToggle').textContent=mode?'Sign in':'Create an account';$('authError').textContent=''}
$('authToggle').onclick=()=>toggleAuth(!signupMode);

function showAuth(){signedInUser=null;csrf='';$('workspaceShell').hidden=true;$('authScreen').hidden=false;$('verifyScreen').hidden=true;$('profileMenu').hidden=true}

function showWorkspace(user){signedInUser=user;const initials=((parts)=>parts[0][0]+(parts.length>1?parts[parts.length-1][0]:''))(user.name.trim().split(/\s+/)).toUpperCase();$('profileAvatar').textContent=initials;$('topProfile').textContent=initials;$('profileName').textContent=user.name;$('profileEmail').textContent=user.email;$('menuEmail').textContent=user.email;$('authScreen').hidden=true;$('verifyScreen').hidden=true;$('workspaceShell').hidden=false;refresh()}

$('authForm').onsubmit=async e=>{e.preventDefault();const data={email:$('authEmail').value.trim(),password:$('authPassword').value};if(signupMode)data.name=$('authName').value.trim();const btn=$('authSubmit');btn.disabled=true;$('authError').textContent='';try{const r=await api(signupMode?'/auth/signup':'/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});$('authPassword').value='';if(r.verification_required){$('verifyAddress').textContent=data.email;$('verifyScreen').hidden=false;$('authScreen').hidden=true;$('verifyCode').focus()}else{csrf=r.csrf;showWorkspace(r.user)}}catch(err){$('authError').textContent=err.message}finally{btn.disabled=false}};

$('verifyForm').onsubmit=async e=>{e.preventDefault();const email=$('verifyAddress').textContent,code=$('verifyCode').value;try{const r=await api('/auth/verify-email',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,code})});csrf=r.csrf;$('verifyCode').value='';showWorkspace(r.user)}catch(err){$('verifyError').textContent=err.message}};

$('resendCode').onclick=async()=>{const b=$('resendCode');b.disabled=true;try{const r=await api('/auth/resend-verification',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:$('verifyAddress').textContent})});$('verifyError').textContent=r.message}catch(e){$('verifyError').textContent=e.message}finally{window.setTimeout(()=>{b.disabled=false},60000)}};

$('backToLogin').onclick=()=>{toggleAuth(false);showAuth()};
$('openVerification').onclick=()=>{const email=$('authEmail').value.trim();if(!email){$('authError').textContent='Enter your registered email first.';return}$('verifyAddress').textContent=email;$('verifyScreen').hidden=false;$('authScreen').hidden=true;$('verifyError').textContent='Click Resend code to receive a new verification code.'};
function toggleProfile(){const menu=$('profileMenu');menu.hidden=!menu.hidden;$('profileButton').setAttribute('aria-expanded',String(!menu.hidden))}
$('profileButton').onclick=toggleProfile;$('topProfile').onclick=toggleProfile;
$('logoutButton').onclick=async()=>{try{await api('/auth/logout',{method:'POST'})}catch(e){console.warn(e.message)}showAuth();$('chatMessages').replaceChildren();projects=[];current=''};

async function api(path,opts={}){let res;try{opts.credentials='same-origin';if(csrf && opts.method && !['GET','HEAD'].includes(opts.method.toUpperCase()))opts.headers={...(opts.headers||{}),'X-CSRF-Token':csrf};res=await fetch(path,opts)}catch{throw Error('Cannot connect to backend. Check that the server is running.')}let data=await res.json().catch(()=>({}));if(res.status===401 && signedInUser){showAuth()}if(!res.ok)throw Error(typeof data.detail==='string'?data.detail:`Request failed (${res.status})`);return data}
function el(tag,cls,txt){const n=document.createElement(tag);if(cls)n.className=cls;if(txt!==undefined)n.textContent=txt;return n}
function empty(title,desc,onClick){let box=el('div','empty');box.append(el('div','emptyicon','◈'),el('b','',title),el('div','',desc));if(onClick){let b=el('button','primary','＋  Create project');b.onclick=onClick;box.append(b)}return box}
function goto(view){document.querySelectorAll('.view').forEach(e=>e.classList.toggle('active',e.id===view));document.querySelectorAll('.navlink').forEach(e=>e.classList.toggle('active',e.dataset.view===view));$('currentPage').textContent={overview:'Overview',documents:'Documents',assistant:'AI Assistant',requirements:'Requirements',review:'Engineering Review'}[view];if(view==='documents')loadDocs();if(view==='requirements')loadReqs();if(view==='review')resetReview();window.scrollTo(0,0)}
document.querySelectorAll('[data-view]').forEach(e=>e.addEventListener('click',()=>goto(e.dataset.view)));document.querySelectorAll('[data-goto]').forEach(e=>e.addEventListener('click',()=>goto(e.dataset.goto)));
function openModal(){$('modal').hidden=false;$('projectName').focus()}function closeModal(){$('modal').hidden=true;$('projectError').textContent=''}$('newProject').onclick=openModal;$('closeModal').onclick=closeModal;$('cancelModal').onclick=closeModal;$('modal').addEventListener('click',e=>{if(e.target===$('modal'))closeModal()});
function syncSelects(){for(let id of ['docProject','askProject','reqProject','reviewProject']){let select=$(id),prior=select.value;select.replaceChildren();if(!projects.length){let opt=new Option('Create a project first','');select.add(opt)}else{projects.forEach(p=>select.add(new Option(p.name,p.id)));select.value=projects.some(p=>p.id===prior)?prior:(current||projects[0].id)}}}
async function refresh(){try{projects=await api('/projects');if(!projects.some(p=>p.id===current))current=projects[0]?.id||'';$('projectCount').textContent=projects.length;syncSelects();let docs=await Promise.all(projects.map(p=>api(`/projects/${p.id}/documents`)));$('docCount').textContent=docs.reduce((n,v)=>n+v.length,0);let reqs=await Promise.all(projects.map(p=>api(`/projects/${p.id}/requirements`)));$('reqCount').textContent=reqs.reduce((n,v)=>n+v.candidates.length,0);const host=$('projects');host.replaceChildren();if(!projects.length){host.append(empty('No projects yet','Create your first project to start organizing technical documents.',openModal));return}projects.forEach((p,i)=>{let card=el('button','project-card');card.append(el('div','project-symbol','◈'),el('b','',p.name),el('p','',`${docs[i].length} document${docs[i].length!==1?'s':''}  ·  View workspace →`));card.onclick=()=>{current=p.id;syncSelects();goto('documents')};host.append(card)})}catch(e){$('projects').replaceChildren(empty('Connection issue',e.message))}}
$('projectForm').addEventListener('submit',async e=>{e.preventDefault();let name=$('projectName').value.trim();if(!name)return;try{let p=await api('/projects',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});current=p.id;$('projectName').value='';closeModal();await refresh()}catch(err){$('projectError').textContent=err.message}});
async function loadDocs(){let id=$('docProject').value,host=$('documentList');host.replaceChildren();if(!id){host.append(empty('No project selected','Create a project to begin uploading.'));return}try{let docs=await api(`/projects/${id}/documents`);if(!docs.length)host.append(empty('No documents yet','Upload a text-based PDF to start analyzing your project.'));docs.forEach(d=>{let row=el('div','doc-row'),ic=el('div','doc-icon','▤'),meta=el('div');meta.append(el('b','',d.filename),el('small','',`${d.page_count} page${d.page_count===1?'':'s'} · Uploaded ${d.created_at||''}`));row.append(ic,meta);host.append(row)})}catch(e){host.append(empty('Could not load documents',e.message))}}
$('docProject').onchange=loadDocs;$('fileInput').onchange=()=>{$('fileName').textContent=$('fileInput').files[0]?.name||'No file selected'};
$('uploadBtn').onclick=async()=>{let id=$('docProject').value,file=$('fileInput').files[0],msg=$('uploadMessage');msg.className='message';if(!id||!file){msg.textContent='Select a project and a PDF first.';return}let fd=new FormData();fd.append('project_id',id);fd.append('file',file);let btn=$('uploadBtn');btn.disabled=true;btn.textContent='Uploading…';try{let d=await api('/documents/upload',{method:'POST',body:fd});msg.textContent=`Uploaded ${d.filename} (${d.page_count} pages).`;msg.className='message ok';$('fileInput').value='';$('fileName').textContent='No file selected';await loadDocs();await refresh()}catch(e){msg.textContent=e.message}finally{btn.disabled=false;btn.textContent='Upload document →'}};
// Render model Markdown as safe DOM nodes (never inject untrusted text as HTML).
function renderAnswer(container, raw) {
  // Normalize escaped Markdown without using innerHTML for model-supplied text.
  let text=String(raw||'').replace(/\\([*_.#\[\]`|])/g,'$1')
    .replace(/\s+(?=\d+\.\s+\*\*)/g,'\n')
    .replace(/<br\s*\/?\s*>/gi,'\n');
  const inline=(parent,line)=>{
    for(const part of line.split(/(\*\*[^*]+\*\*|(?<!\*)\*[^*]+\*(?!\*))/g)){
      if(part.startsWith('**')&&part.endsWith('**')) parent.append(el('strong','',part.slice(2,-2)));
      else if(part.startsWith('*')&&part.endsWith('*')&&part.length>2)parent.append(el('em','',part.slice(1,-1)));
      else parent.append(document.createTextNode(part));
    }
  };
  let lines=text.split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
  const isPipeRow=line=>/^\|.+\|$/.test(line)||(/^\S[^|]*\|/.test(line)&&line.includes('|'));
  const isDivider=line=>/^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$/.test(line);
  const cells=line=>line.replace(/^\|/,'').replace(/\|$/,'').split('|').map(c=>c.trim());
  for(let i=0;i<lines.length;){
    const trimmed=lines[i];
    if(isPipeRow(trimmed)&&i+1<lines.length&&isDivider(lines[i+1])){
      let headers=cells(trimmed), table=el('table','answer-table'),thead=el('thead'),hr=el('tr');
      headers.forEach(h=>{let th=el('th');inline(th,h);hr.append(th)});thead.append(hr);table.append(thead);
      let tbody=el('tbody');i+=2;
      while(i<lines.length&&isPipeRow(lines[i])&&!isDivider(lines[i])){
        let tr=el('tr');cells(lines[i]).forEach(c=>{let td=el('td');inline(td,c);tr.append(td)});tbody.append(tr);i++;
      }
      table.append(tbody);let wrapper=el('div','answer-table-wrap');wrapper.append(table);container.append(wrapper);continue;
    }
    let m=trimmed.match(/^(\d+)\.\s+(.+)$/);
    if(m){let row=el('div','answer-list-row');row.append(el('span','answer-number',m[1]));let body=el('div');inline(body,m[2]);row.append(body);container.append(row);i++;continue}
    m=trimmed.match(/^[-•]\s+(.+)$/);
    if(m){let row=el('div','answer-list-row');row.append(el('span','answer-bullet','•'));let body=el('div');inline(body,m[1]);row.append(body);container.append(row);i++;continue}
    m=trimmed.match(/^#{1,3}\s+(.+)$/);
    if(m){let heading=el('div','answer-heading');inline(heading,m[1]);container.append(heading);i++;continue}
    if(isDivider(trimmed)){i++;continue}
    let para=el('p','answer-paragraph');inline(para,trimmed);container.append(para);i++;
  }
}
function addChat(role,text,sources=[]){
  let container=$('chatMessages'),outer=el('div',role==='user'?'user-message':'ai-message');
  if(role!=='user')outer.append(el('div','assistant-avatar mini','✳'));
  let bubble=el('div','bubble');
  if(role==='ai')renderAnswer(bubble,text);else bubble.textContent=text;
  if(sources.length){
    let details=document.createElement('details');details.className='sources';
    let summary=el('summary','');summary.append(el('span','source-icon','▤'),document.createTextNode(` Sources · ${sources.length}`),el('span','source-chevron','⌄'));summary.setAttribute('aria-label',`Show ${sources.length} supporting document sources`);details.append(summary);
    sources.forEach((s,i)=>{let entry=el('div','source-entry');entry.append(el('strong','',`Source ${i+1} · ${s.filename} · page ${s.page}`));if(s.excerpt)entry.append(el('p','',s.excerpt.slice(0,220)));details.append(entry)});
    bubble.append(details);
  }
  outer.append(bubble);container.append(outer);container.scrollTop=container.scrollHeight;return outer
}
$('askForm').onsubmit=async e=>{e.preventDefault();let question=$('question').value.trim(),id=$('askProject').value;if(!id){addChat('ai','Create a project and upload a PDF first.');return}if(question.length<3)return;addChat('user',question);$('question').value='';let pending=addChat('ai','Reviewing your documents…'),btn=$('askForm').querySelector('button');pending.classList.add('thinking');btn.disabled=true;try{let res=await api('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project_id:id,question})});pending.remove();addChat('ai',res.answer,res.sources||[])}catch(err){pending.remove();addChat('ai',err.message)}finally{btn.disabled=false}};
document.querySelectorAll('[data-prompt]').forEach(e=>e.onclick=()=>{$('question').value=e.dataset.prompt;goto('assistant');$('question').focus()});
async function loadReqs(){let id=$('reqProject').value,host=$('requirementsList');host.replaceChildren();if(!id){host.append(empty('No project selected','Create a project to extract technical values.'));return}try{let result=await api(`/projects/${id}/requirements`);if(!result.candidates.length){host.append(empty('No values detected','Upload documents mentioning voltages, capacities, or frequencies.'));return}result.candidates.forEach(r=>{let row=el('div','req-row'),tag=el('div','req-tag',r.value),meta=el('div');meta.append(el('b','',`${r.filename} · page ${r.page}`),el('small','',r.context));row.append(tag,meta);host.append(row)})}catch(err){host.append(empty('Could not load requirements',err.message))}}
$('reqProject').onchange=loadReqs;
async function boot(){try{const r=await api('/auth/me');csrf=r.csrf;showWorkspace(r.user)}catch{showAuth()}finally{const intro=$('intro');const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;window.setTimeout(()=>{intro.classList.add('intro-leave');window.setTimeout(()=>intro.remove(),reduced?0:420)},reduced?0:2400)}}
boot();

// Evidence-first engineering review. All text is rendered as textContent, never HTML.
let lastReview=null;
function resetReview(){lastReview=null;$('downloadReview').disabled=true;$('reviewSummary').replaceChildren();$('reviewResults').replaceChildren();$('reviewNotice').textContent='Select a project and run a review.'}
$('reviewProject').onchange=resetReview;
$('runReview').onclick=async()=>{let id=$('reviewProject').value;if(!id){$('reviewNotice').textContent='Create a project and upload a document first.';return}const btn=$('runReview');btn.disabled=true;btn.textContent='Reviewing documents…';$('reviewNotice').textContent='Scanning your uploaded text for engineering evidence…';try{const result=await api(`/projects/${encodeURIComponent(id)}/engineering-review`);lastReview=result;$('downloadReview').disabled=false;const found=result.checks.filter(c=>c.status==='evidence_found').length;$('reviewNotice').textContent=result.document_count?result.disclaimer:'No document text is available in this project yet. Upload a PDF first.';const summary=$('reviewSummary');summary.replaceChildren();summary.append(el('div','review-metric',`${result.document_count} documents reviewed`),el('div','review-metric',`${found} / ${result.checks.length} topics with evidence`));const host=$('reviewResults');host.replaceChildren();result.checks.forEach(check=>{const card=el('article','review-card'),header=el('div','review-card-head');header.append(el('strong','',check.label),el('span',check.status==='evidence_found'?'review-tag found':'review-tag missing',check.status==='evidence_found'?'Evidence found':'Not found in text'));card.append(header);card.append(el('p','review-help',check.guidance));check.evidence.forEach(e=>{let evidence=el('div','review-evidence');evidence.append(el('b','',`${e.value} · ${e.filename} · p. ${e.page}`),el('p','',e.excerpt));card.append(evidence)});host.append(card)})}catch(e){$('reviewNotice').textContent=e.message}finally{btn.disabled=false;btn.textContent='✦  Run engineering review'}};
$('downloadReview').onclick=()=>{if(!lastReview)return;const blob=new Blob([JSON.stringify(lastReview,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='engiflow-engineering-review.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),2000)};

// Cross-document comparison: independent of engineering screening, evidence-first.
let lastConflicts=null;
function renderConflicts(result){
  const host=$('conflictResults');host.replaceChildren();
  $('conflictNotice').textContent=result.document_count<2?`Only ${result.document_count} document(s) available. Upload another specification to compare.`:`${result.possible_conflicts} candidate discrepancies across ${result.document_count} PDFs. Values with different engineering roles are intentionally not compared.`;
  result.checks.forEach(check=>{
    const card=el('article','review-card'),head=el('div','review-card-head');
    const bad=check.status==='possible_conflict';
    head.append(el('strong','',check.label),el('span',bad?'review-tag conflict-tag':'review-tag found',bad?'Review difference':check.document_count>1?'No difference detected':'Insufficient comparison'));
    card.append(head,el('p','review-help',check.note));
    const details=el('details','conflict-evidence'),sum=el('summary','',`${check.evidence.length} source match(es) · ${check.document_count} document(s)`);
    details.append(sum);
    check.evidence.forEach(e=>{const item=el('div','review-evidence');item.append(el('b','',`${e.value} · ${e.filename} · p. ${e.page}`),el('p','',e.excerpt));details.append(item)});
    card.append(details);host.append(card);
  });
}
$('runConflicts').onclick=async()=>{
  const id=$('reviewProject').value,btn=$('runConflicts');if(!id){$('conflictNotice').textContent='Choose a project first.';return}
  btn.disabled=true;$('conflictNotice').textContent='Comparing documented engineering values…';
  try{const data=await api(`/projects/${encodeURIComponent(id)}/conflicts`);lastConflicts=data;$('exportConflicts').disabled=false;renderConflicts(data)}
  catch(err){$('conflictNotice').textContent=err.message}
  finally{btn.disabled=false}
};
$('exportConflicts').onclick=()=>{
  if(!lastConflicts)return;
  const url=URL.createObjectURL(new Blob([JSON.stringify(lastConflicts,null,2)],{type:'application/json'}));
  const a=document.createElement('a');a.href=url;a.download='engiflow-conflict-review.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);
};
$('reviewProject').addEventListener('change',()=>{lastConflicts=null;$('conflictResults').replaceChildren();$('exportConflicts').disabled=true;$('conflictNotice').textContent='Select Compare specifications to analyze this project.'});

// Authenticated, server-generated PDF report for selected project.
$('exportPdfReport').onclick=async()=>{
  const id=$('reviewProject').value,btn=$('exportPdfReport');
  if(!id){$('conflictNotice').textContent='Select a project first.';return;}
  btn.disabled=true;const prior=btn.textContent;btn.textContent='Preparing PDF…';
  try{
    const resp=await fetch(`/projects/${encodeURIComponent(id)}/engineering-report.pdf`,{credentials:'same-origin'});
    if(!resp.ok){let detail='Could not generate report';try{const j=await resp.json();detail=j.detail||detail}catch{}throw new Error(detail)}
    const url=URL.createObjectURL(await resp.blob()),a=document.createElement('a');a.href=url;a.download='engiflow-engineering-review.pdf';a.click();setTimeout(()=>URL.revokeObjectURL(url),4000);
  }catch(err){$('conflictNotice').textContent=err.message}finally{btn.disabled=false;btn.textContent=prior}
};

// Close profile popup when clicking away or pressing Escape.
document.addEventListener('pointerdown',e=>{
  const menu=$('profileMenu'),button=$('profileButton'),top=$('topProfile');
  if(!menu.hidden && !menu.contains(e.target) && !button.contains(e.target) && !top.contains(e.target)){
    menu.hidden=true;button.setAttribute('aria-expanded','false');
  }
});
document.addEventListener('keydown',e=>{
  if(e.key==='Escape'){$('profileMenu').hidden=true;$('profileButton').setAttribute('aria-expanded','false');}
});
