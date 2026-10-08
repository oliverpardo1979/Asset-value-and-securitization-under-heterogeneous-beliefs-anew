'use strict';
// Display only stored, validated data. There is deliberately no browser solver.
const $ = id => document.getElementById(id);
const fmt = (x, n = 3) => Number(x).toFixed(n);
const esc = text => String(text).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const ink = '#173c39', accent = '#b96241', grid = '#dde3de', muted = '#59676b';
let data, meta, activeEq = 0, selectedCase, chartWindow = 'full', mathReady = false, readerPromise;

async function get(url, type = 'json') {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
  return response[type]();
}
function table(headers, rows) {
  return `<table><thead><tr>${headers.map(x => `<th scope="col">${x}</th>`).join('')}</tr></thead><tbody>${rows.map(row => `<tr>${row.map((x, i) => i ? `<td>${x}</td>` : `<th scope="row">${x}</th>`).join('')}</tr>`).join('')}</tbody></table>`;
}
function matrix(values, name) {
  return `<div><h4>${esc(name)}</h4>${table(['Current → next', 'l', 'm', 'h'], values.map((row, i) => [['l','m','h'][i], ...row.map(v => fmt(v, 4))]))}</div>`;
}
function svgFrame(title, body, w = 530, h = 340) {
  return `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(title)}"><title>${esc(title)}</title>${body}</svg>`;
}
function line(x1, y1, x2, y2, color = grid, dash = '') {
  return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${color}"${dash ? ` stroke-dasharray="${dash}"` : ''}/>`;
}
function text(x, y, content, anchor = 'start', color = muted) {
  return `<text x="${x}" y="${y}" text-anchor="${anchor}" style="fill:${color}">${esc(content)}</text>`;
}
function saveSelection() {
  const u = new URL(location.href);
  u.searchParams.set('eq', activeEq + 1);
  u.searchParams.set('case', selectedCase.id);
  u.searchParams.set('window', chartWindow);
  history.replaceState(null, '', u);
}

function showPayoff() {
  const q = Number($('payoff-inspect').value), k = 2.25;
  $('payoff-value').textContent = fmt(q, 2);
  const senior = Math.min(q, k), junior = Math.max(q - k, 0);
  $('payoff-values').innerHTML = `<span>Senior <b>${fmt(senior,2)}</b></span><span>Junior <b>${fmt(junior,2)}</b></span><span>Total <b>${fmt(q,2)}</b></span>`;
  const x = v => 55 + 420 * v / 4, y = v => 285 - 225 * v / 4;
  let body = '';
  for (let i=0;i<=4;i++) body += line(55,y(i),475,y(i)) + text(42,y(i)+5,i,'end') + text(x(i),310,i,'middle');
  body += text(55,23,'Tranche payoff') + text(265,336,'Asset resale price','middle');
  body += line(x(k),50,x(k),285,muted,'5 5') + text(x(k)+8,45,'K = 2.25');
  body += `<path d="M ${x(0)},${y(0)} L ${x(k)},${y(k)} L ${x(4)},${y(k)}" fill="none" stroke="${ink}" stroke-width="3"/>`;
  body += `<path d="M ${x(0)},${y(0)} L ${x(k)},${y(0)} L ${x(4)},${y(4-k)}" fill="none" stroke="${accent}" stroke-width="3"/>`;
  body += line(x(q),50,x(q),285,'#a1aeb0','3 4');
  for (const [v,c] of [[senior,ink],[junior,accent]]) body += `<circle cx="${x(q)}" cy="${y(v)}" r="5" fill="${c}"/>`;
  $('payoff-chart').innerHTML = svgFrame('Payoffs of senior and junior tranches with attachment point 2.25',body);
}

function showMotivating() {
  const values = data.motivating.valuations;
  $('motivating-valuations').innerHTML = table(['Claim', 'Theory A', 'Theory B', 'Price'], ['Senior','Junior'].map((name,t) => {
    const a = values[t][0][1], b = values[t][1][1];
    return [name, `<span class="${a>b?'winner':''}">${fmt(a)}</span>`, `<span class="${b>a?'winner':''}">${fmt(b)}</span>`, fmt(Math.max(a,b))];
  }));
  showPayoff();
}

function showEquilibrium() {
  const names = ['Lowest equilibrium', 'Middle equilibrium', 'Highest equilibrium'];
  const labels = ['Junior never pays', 'Junior pays only in h', 'Junior pays in m and h'];
  const e = data.example1_equilibria[activeEq], q = e.q;
  $('equilibrium-controls').innerHTML = names.map((name,i) => `<button type="button" data-eq="${i}" aria-pressed="${i===activeEq}"><b>${name}</b><span>q${i+1} · ${labels[i]}</span></button>`).join('');
  $('equilibrium-label').textContent = `q${activeEq+1} · ${names[activeEq]}`;
  $('payment-pattern').textContent = labels[activeEq];
  $('equilibrium-values').innerHTML = table(['Next state', 'Asset price', 'Senior payoff', 'Junior payoff'], q.map((v,i) => [['l','m','h'][i],fmt(v),fmt(e.payoffs[0][i]),fmt(e.payoffs[1][i]) ]));
  $('equilibrium-note').textContent = `The payoffs in each row add up to the asset price. Direct-substitution residual is ${e.residual.toExponential(1)} in floating-point arithmetic.`;
  let body = '';
  const x = i => 130 + i*140, y = v => 275-(v-2.4)*245/.9;
  for (let tick=2.4;tick<3.31;tick+=.15) body += line(70,y(tick),480,y(tick)) + text(59,y(tick)+5,fmt(tick,2),'end');
  body += line(70,y(3),480,y(3),accent,'6 5') + text(475,y(3)-10,'Attachment = 3','end',accent);
  q.forEach((v,i) => {
    body += `<line x1="${x(i)}" y1="${y(2.4)}" x2="${x(i)}" y2="${y(v)}" stroke="${ink}" stroke-width="3"/>`;
    body += `<circle cx="${x(i)}" cy="${y(v)}" r="7" fill="${ink}"/>` + text(x(i),y(v)-14,fmt(v),'middle',ink);
    body += text(x(i),304,['l','m','h'][i],'middle');
  });
  body += text(55,17,'Asset price') + text(265,335,'Next-period state','middle');
  $('equilibrium-chart').innerHTML = svgFrame(`Equilibrium ${activeEq+1}: asset prices ${q.map(v=>fmt(v)).join(', ')}, attachment 3. Vertical axis starts at 2.4.`,body);
  const ex = data.cases.find(c=>c.id==='example1-tranches');
  $('example1-parameters').innerHTML = `<div class="matrix-grid">${matrix(ex.theories[0],'Theory A')}${matrix(ex.theories[1],'Theory B / objective process')}</div>`;
  $('valuation-check').innerHTML = table(['Current state','Dividend / R','Senior price','Junior price','Sum = asset price'], [0,1,2].map(i => {
    const senior=Math.max(e.valuations[0][0][i],e.valuations[0][1][i]);
    const junior=Math.max(e.valuations[1][0][i],e.valuations[1][1][i]);
    return [['l','m','h'][i],fmt(ex.dividends[i]/ex.returns[i],6),fmt(senior,6),fmt(junior,6),fmt(q[i],6)];
  }));
}

function stored(path, n) { return path[Math.min(n,path.length-1)]; }
function showIteration() {
  const c = selectedCase, count = Math.max(c.iterations_min,c.iterations_max);
  const start = chartWindow==='late' ? Math.min(40,Math.floor(count*.3)) : 0;
  const inspect = Number($('iteration-inspect').value);
  $('iteration-inspect').min = start;
  $('iteration-inspect').max = count;
  $('iteration-inspect').value = Math.max(start,Math.min(count,inspect));
  const n = Number($('iteration-inspect').value);
  const bounds = [stored(c.lower_path,n),stored(c.upper_path,n)];
  $('iteration-label').textContent = `n = ${n}`;
  $('iteration-scope').textContent = c.full_support
    ? 'All subjective transition probabilities in this stored economy are positive. Lines connect successive iterations. Axes adapt to the chosen example and iteration window.'
    : 'This is the ε = 0 limit of the motivating example. Its transition matrices have zero entries. Lines connect successive iterations. Axes adapt to the chosen example and iteration window.';
  $('iteration-charts').innerHTML = c.states.map((state,i)=>{
    let lo=stored(c.lower_path,start)[i],hi=stored(c.upper_path,start)[i];
    const span=Math.max(hi-lo,1e-6), pad=span*.12;
    lo=Math.max(0,lo-pad);hi+=pad;
    const x=v=>67+330*(v-start)/Math.max(1,count-start),y=v=>230-190*(v-lo)/(hi-lo);
    let body='';
    for(let j=0;j<=4;j++) {const tick=lo+(hi-lo)*j/4;body+=line(67,y(tick),397,y(tick))+text(59,y(tick)+5,fmt(tick,hi-lo<.1?3:hi<5?2:1),'end');}
    for(const j of [start,Math.round((start+count)/2),count]) body+=text(x(j),253,j,'middle');
    for(const [path,color,limit] of [[c.lower_path,ink,c.q_min[i]],[c.upper_path,accent,c.q_max[i]]]) {
      body+=line(67,y(limit),397,y(limit),color,'3 4');
      const points=Array.from({length:count-start+1},(_,j)=>`${x(start+j)},${y(stored(path,start+j)[i])}`).join(' ');
      body+=`<polyline points="${points}" stroke="${color}" stroke-width="2.5" fill="none"/>`;
      body+=`<circle cx="${x(n)}" cy="${y(stored(path,n)[i])}" r="4" fill="${color}"/>`;
    }
    body+=line(x(n),40,x(n),230,'#9ca6a8','2 3')+text(65,19,'Price')+text(233,278,'Iteration n','middle');
    return `<div class="chart-card"><h2>State ${esc(state)}</h2><p class="unit">Limits ${fmt(c.q_min[i])} and ${fmt(c.q_max[i])}</p>${svgFrame(`State ${state}. Lower limit ${c.q_min[i]}, upper limit ${c.q_max[i]}. Iterations ${start} to ${count}.`,body,445,285)}</div>`;
  }).join('');
  $('iteration-table').innerHTML=table(['State','Lower iterate','Upper iterate','Lowest equilibrium','Highest equilibrium'],c.states.map((s,i)=>[s,fmt(bounds[0][i],6),fmt(bounds[1][i],6),fmt(c.q_min[i],6),fmt(c.q_max[i],6)]));
}

function selectCase(id) {
  selectedCase=data.cases.find(c=>c.id===id) || data.cases[4];
  $('case-select').value=selectedCase.id;
  const c=selectedCase;
  $('iteration-inspect').value='0';
  $('iteration-parameters').innerHTML=`<p>Dividends (${c.dividends.map(v=>fmt(v,6)).join(', ')}). Gross returns (${c.returns.map(v=>fmt(v,6)).join(', ')}). Attachment points (${c.attachments.map(v=>fmt(v,6)).join(', ')}), followed by an unbounded final tranche.</p><div class="matrix-grid">${c.theories.map((m,i)=>matrix(m,`Theory ${c.theory_names[i]}`)).join('')}</div><p>The initial upper price in every state is M = (maximum dividend + highest attachment point) / (minimum gross return − 1) = ${fmt(c.upper_bound,6)}.</p><p>The code stops each sequence when both its step and fixed-point residual are at most 10⁻¹² + 10⁻¹² × max(1, largest price). This is a residual stopping rule, not a certified bound on the distance to an equilibrium.</p><p>The lower sequence took ${c.iterations_min} iterations, with residual ${c.residual_min.toExponential(3)}. The upper sequence took ${c.iterations_max} iterations, with residual ${c.residual_max.toExponential(3)}. The explorer checks both outputs against the known price vectors in the companion. After a sequence stops, its last recorded value is held fixed for display.</p>`;
  showIteration();
}

function openParents(target) {
  let parent=target?.parentElement;
  while(parent) { if(parent.tagName==='DETAILS')parent.open=true;parent=parent.parentElement; }
}
async function typesetReader() {
  if(mathReady)return;
  $('math-status').textContent='Rendering equations…';
  try {
    if (!window.MathJax?.startup?.promise) throw new Error('MathJax is not available');
    await MathJax.startup.promise;
    // Typeset all proofs at their final reading width, then restore their state.
    const proofs=[...$('manuscript').querySelectorAll('details.proof')];
    const states=proofs.map(d=>d.open);proofs.forEach(d=>d.open=true);
    await MathJax.typesetPromise([$ ('manuscript')]);
    proofs.forEach((d,i)=>d.open=states[i]);
    mathReady=true;$('math-status').textContent='';
  } catch(error) {
    $('math-status').innerHTML='Equation rendering could not load. The LaTeX remains visible. <a href="paper/asset-value-and-securitization.pdf">Read the typeset PDF</a>.';
  }
}
async function loadReader() {
  if(readerPromise)return readerPromise;
  readerPromise=(async()=>{
    $('manuscript').innerHTML=await get('generated/manuscript.html','text');
    document.querySelectorAll('#manuscript div.proof').forEach(div=>{
      const details=document.createElement('details');details.className='proof';
      const summary=document.createElement('summary');summary.textContent='Proof · expand';
      details.appendChild(summary);div.className='proof-content';div.replaceWith(details);details.appendChild(div);
      details.addEventListener('toggle',()=>{summary.textContent=details.open?'Proof · collapse':'Proof · expand';});
    });
    document.querySelectorAll('#manuscript table').forEach(t=>{
      const wrap=document.createElement('div');wrap.className='table-wrap';t.replaceWith(wrap);wrap.appendChild(t);
    });
    $('contents').innerHTML=meta.sections.filter(s=>s.level<3 && s.title!==meta.title).map(s=>`<a class="level-${s.level}" href="#${esc(s.id)}">${s.number?esc(s.number)+' ':''}${esc(s.title)}</a>`).join('');
  })();
  return readerPromise;
}
async function route() {
  const hash=decodeURIComponent(location.hash.slice(1))||'overview';
  if(hash==='main'){document.querySelector('main').focus();return;}
  const view=['overview','explore','replicate','mechanism'].includes(hash)?hash:'paper';
  document.querySelectorAll('.view').forEach(s=>s.hidden=s.id!==view);
  document.querySelectorAll('nav [data-view]').forEach(a=>{
    if(a.dataset.view===(view==='mechanism'?'explore':view))a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');
  });
  if(view==='paper') {
    await loadReader();await typesetReader();
    if((decodeURIComponent(location.hash.slice(1))||'overview')!==hash)return;
    const target=$(hash);
    if(target&&hash!=='paper'){openParents(target);target.scrollIntoView({block:'start'});}
    else window.scrollTo({top:0,behavior:'instant'});
  } else window.scrollTo({top:0,behavior:'instant'});
}

async function init() {
  [data,meta]=await Promise.all([get('generated/examples.json'),get('generated/manuscript-meta.json')]);
  $('abstract-preview').innerHTML=meta.abstract_html;
  $('source-stamp').textContent=`From the manuscript at commit ${meta.source_commit.slice(0,7)}. The PDF and HTML present the same paper.`;
  $('provenance').innerHTML=`<p>Manuscript source SHA-256<br><code>${meta.source_sha256}</code></p><p>Published PDF SHA-256<br><code>${meta.pdf_sha256}</code></p><p><a href="generated/manuscript-meta.json">Download manuscript conversion metadata</a> · <a href="generated/examples.json">Download the example data and code hashes</a></p>`;
  const params=new URLSearchParams(location.search);
  activeEq=Math.max(0,Math.min(2,(Number(params.get('eq'))||1)-1));
  activeEq=Math.floor(activeEq);
  chartWindow=params.get('window')==='late'?'late':'full';
  $('case-select').innerHTML=data.cases.map(c=>`<option value="${c.id}">${esc(c.name)}</option>`).join('');
  showEquilibrium();showMotivating();selectCase(params.get('case'));
  document.querySelectorAll('[data-window]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.window===chartWindow));
  $('equilibrium-controls').addEventListener('click',event=>{const b=event.target.closest('[data-eq]');if(b){activeEq=Number(b.dataset.eq);showEquilibrium();saveSelection();}});
  $('payoff-inspect').addEventListener('input',showPayoff);
  $('case-select').addEventListener('change',event=>{selectCase(event.target.value);saveSelection();});
  $('iteration-inspect').addEventListener('input',showIteration);
  document.querySelectorAll('[data-window]').forEach(b=>b.addEventListener('click',()=>{
    chartWindow=b.dataset.window;document.querySelectorAll('[data-window]').forEach(a=>a.setAttribute('aria-pressed',a===b));showIteration();saveSelection();
  }));
  $('proof-toggle').addEventListener('click',()=>{
    const proofs=[...document.querySelectorAll('#manuscript details.proof')];
    const expand=proofs.some(d=>!d.open);proofs.forEach(d=>d.open=expand);
    $('proof-toggle').textContent=expand?'Collapse all proofs':'Expand all proofs';
  });
  window.addEventListener('hashchange',()=>route().catch(showError));
  await route();
}
function showError(error) {
  console.error(error);
  const notice=document.createElement('p');notice.className='error';notice.setAttribute('role','alert');
  notice.innerHTML='The digital edition could not finish loading. Please reload, or <a href="paper/asset-value-and-securitization.pdf">download the complete PDF</a>.';
  document.querySelector('main').prepend(notice);
}
init().catch(showError);
