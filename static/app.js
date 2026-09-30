const chat = document.querySelector('#chat');
const form = document.querySelector('#message-form');
const input = document.querySelector('#message');
const preferences = document.querySelector('#preferences');

function escapeHtml(value = '') {
  return String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
}
function tags(text='') { return text.split(';').filter(Boolean).map(tag => `<span class="tag">${escapeHtml(tag.trim())}</span>`).join(''); }
function recordCard(record) {
  return `<article class="org-card"><h3>${escapeHtml(record.name)}</h3><p>${escapeHtml(record.description)}</p><div class="tags">${tags(record.causes)}${tags(record.program_types)}</div><p><b>Locations listed:</b> ${escapeHtml(record.locations)}<br><b>Source checked:</b> ${escapeHtml(record.source_accessed || 'Date not recorded')}</p><a class="source-link" href="${escapeHtml(record.source_url)}" target="_blank" rel="noopener">View source ↗</a>${record.notes ? `<p><b>Data note:</b> ${escapeHtml(record.notes)}</p>`:''}</article>`;
}
function addMessage(role, content, records=[], steps=[]) {
  const item = document.createElement('div'); item.className = `message ${role}`;
  item.innerHTML = `<div class="bubble">${escapeHtml(content)}${records.length ? `<div class="results">${records.map(recordCard).join('')}</div>`:''}${steps.length ? `<details class="agent-details"><summary>What the guide did</summary><ul>${steps.map(step=>`<li>${escapeHtml(step)}</li>`).join('')}</ul></details>`:''}</div>`;
  chat.append(item); chat.scrollTop = chat.scrollHeight;
}
function showPreferences(prefs={}) {
  preferences.textContent = ['cause','program','location'].map(key => `${key}: ${prefs[key] || 'not specified'}`).join(' · ');
}
form.addEventListener('submit', async event => {
  event.preventDefault(); const message = input.value.trim(); if (!message) return;
  addMessage('user', message); input.value=''; input.disabled=true;
  try {
    const response = await fetch('/api/message', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message})});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Could not process your message.');
    addMessage('assistant', result.reply, result.records || [], result.steps || []); showPreferences(result.preferences);
  } catch(error) { addMessage('assistant', `Sorry, something went wrong. ${error.message}`); }
  finally { input.disabled=false; input.focus(); }
});
document.querySelector('#new-session').addEventListener('click', async () => {
  await fetch('/api/reset',{method:'POST'}); chat.innerHTML='<div class="welcome"><span class="welcome-icon">✦</span><div><strong>Hi, I’m your donor guide.</strong><p>Try “I want to support education in India” or “I care about older people.”</p></div></div>'; showPreferences(); input.focus();
});
async function loadDirectory() {
  const query=document.querySelector('#search').value.trim(); const cause=document.querySelector('#cause-filter').value;
  const response=await fetch(`/api/organizations?q=${encodeURIComponent(query)}&cause=${encodeURIComponent(cause)}`); const data=await response.json();
  document.querySelector('#result-count').textContent=`${data.records.length} organizations`;
  document.querySelector('#directory-cards').innerHTML=data.records.map(row=>`<article class="directory-card"><h3>${escapeHtml(row.name)}</h3><p>${escapeHtml(row.description)}</p><div class="tags">${tags(row.causes)}</div><p>${escapeHtml(row.locations)}</p><a class="source-link" href="${escapeHtml(row.source_url)}" target="_blank" rel="noopener">View source ↗</a></article>`).join('') || '<p>No records match those filters.</p>';
  const select=document.querySelector('#cause-filter');
  if (select.options.length===1) data.causes.forEach(causeName=>select.add(new Option(causeName,causeName)));
}
document.querySelector('#search').addEventListener('input',loadDirectory);
document.querySelector('#cause-filter').addEventListener('change',loadDirectory);
showPreferences(); loadDirectory();
