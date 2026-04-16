/**
 * app.js — Doc-Review PoC Frontend
 * Handles all API calls, UI state, tabs, chat, search, upload, analyze.
 */

// ── State ─────────────────────────────────────────────────────
const state = {
  lastUpload: null,       // most recent UploadResponse
  selectedFile: null,     // File object pending upload
  chatHistory: [],        // [{role, content}]
  lastAnalysis: null,     // most recent AnalyzeResponse
};

// ── On load ───────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  checkHealth();
  loadDocuments();
  setupDropZone();
});

// ── Health check ──────────────────────────────────────────────
async function checkHealth() {
  try {
    const data = await apiFetch('/api/health');
    const badge = document.getElementById('health-badge');
    const label = document.getElementById('auth-mode-label');
    badge.classList.remove('hidden');
    badge.classList.add('flex');
    label.textContent = data.auth_mode.includes('keyless') ? 'Keyless Auth ✓' : 'API Key Auth ✓';
  } catch (e) {
    console.warn('Health check failed:', e);
  }
}

// ── Tab navigation ────────────────────────────────────────────
function showTab(name) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(`tab-${name}`).classList.remove('hidden');
  document.querySelector(`[data-tab="${name}"]`).classList.add('active');
}

// ── Upload ────────────────────────────────────────────────────
function setupDropZone() {
  const zone = document.getElementById('drop-zone');

  zone.addEventListener('dragover', e => {
    e.preventDefault();
    zone.classList.add('border-azure-500', 'bg-azure-50');
  });
  zone.addEventListener('dragleave', () => {
    zone.classList.remove('border-azure-500', 'bg-azure-50');
  });
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('border-azure-500', 'bg-azure-50');
    const file = e.dataTransfer.files[0];
    if (file) setSelectedFile(file);
  });
}

function onFileSelected(input) {
  if (input.files[0]) setSelectedFile(input.files[0]);
}

function setSelectedFile(file) {
  state.selectedFile = file;
  document.getElementById('drop-filename').textContent =
    `${file.name}  (${formatBytes(file.size)})`;
  document.getElementById('upload-btn').disabled = false;
}

async function doUpload() {
  if (!state.selectedFile) return;

  const formData = new FormData();
  formData.append('file', state.selectedFile);

  showLoading('Uploading to Azure Blob Storage…');
  try {
    const data = await apiFetch('/api/upload', {
      method: 'POST',
      body: formData,
    });

    state.lastUpload = data;

    // Show result
    const resultEl = document.getElementById('upload-result');
    resultEl.classList.remove('hidden');
    document.getElementById('upload-result-json').textContent =
      JSON.stringify(data, null, 2);

    showToast(`✅ Uploaded: ${data.filename}`);
    loadDocuments();

    // Pre-fill analyze & chat doc ID fields
    document.getElementById('analyze-doc-id').value = data.doc_id;
    document.getElementById('chat-doc-id').value = data.doc_id;

  } catch (e) {
    showToast(`❌ Upload failed: ${e.message}`, true);
  } finally {
    hideLoading();
  }
}

function copyDocId() {
  if (state.lastUpload?.doc_id) {
    navigator.clipboard.writeText(state.lastUpload.doc_id);
    showToast('doc_id copied to clipboard');
  }
}

async function loadDocuments() {
  const list = document.getElementById('docs-list');
  try {
    const docs = await apiFetch('/api/upload/list');
    if (!docs.length) {
      list.innerHTML = '<p class="text-gray-400 text-sm text-center py-8">No documents uploaded yet.</p>';
      return;
    }

    list.innerHTML = docs.map(doc => `
      <div class="doc-item" onclick="selectDoc('${doc.doc_id}', '${escHtml(doc.filename)}')">
        <div class="flex items-center gap-3">
          <span class="text-xl">${fileIcon(doc.filename)}</span>
          <div>
            <p class="text-sm font-medium text-gray-800">${escHtml(doc.filename)}</p>
            <p class="text-xs text-gray-400">${formatBytes(doc.size_bytes)}</p>
          </div>
        </div>
        <span class="doc-arrow text-gray-300 text-lg">›</span>
      </div>
    `).join('');
  } catch (e) {
    list.innerHTML = `<p class="text-red-400 text-sm text-center py-6">Could not load documents: ${e.message}</p>`;
  }
}

function selectDoc(docId, filename) {
  document.getElementById('analyze-doc-id').value = docId;
  document.getElementById('chat-doc-id').value = docId;
  document.getElementById('search-doc-filter').value = docId;
  showToast(`Selected: ${filename}`);
}

function pickRecentDocId(targetId) {
  const recentId = state.lastUpload?.doc_id
    || document.getElementById('analyze-doc-id').value
    || '';
  if (recentId) document.getElementById(targetId).value = recentId;
  else showToast('No recent upload found. Upload a document first.', true);
}

// ── Analyze ───────────────────────────────────────────────────
async function doAnalyze() {
  const docId = document.getElementById('analyze-doc-id').value.trim();
  if (!docId) { showToast('Enter a document ID first', true); return; }

  showLoading('Running Content Understanding extraction…');
  const resultEl = document.getElementById('analyze-result');

  try {
    const data = await apiFetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ doc_id: docId }),
    });

    state.lastAnalysis = data;
    renderAnalysisResult(data, resultEl);
    if (data.indexed) showToast('✅ Extracted + indexed into AI Search');
    else showToast('⚠️ Extracted but indexing was skipped or failed', true);

  } catch (e) {
    resultEl.innerHTML = errorBlock(e.message);
    showToast(`❌ Analysis failed: ${e.message}`, true);
  } finally {
    hideLoading();
  }
}

function renderAnalysisResult(data, container) {
  const fields = data.fields || [];
  const fieldHtml = fields.length
    ? fields.map(f => `
        <div class="field-row">
          <span class="field-name">${escHtml(f.name)}</span>
          <span class="field-value">${escHtml(String(f.value ?? '—'))}</span>
          ${f.confidence != null ? `<span class="field-confidence">${(f.confidence * 100).toFixed(0)}%</span>` : ''}
        </div>`).join('')
    : '<p class="text-sm text-gray-400 py-4">No structured fields extracted. Check your Content Understanding analyzer configuration.</p>';

  container.innerHTML = `
    <div class="mb-4">
      <div class="flex items-center justify-between mb-2">
        <span class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Extracted Fields</span>
        <span class="text-xs text-gray-400">${fields.length} field${fields.length !== 1 ? 's' : ''}</span>
      </div>
      ${fieldHtml}
    </div>
    ${data.raw_content ? `
    <div class="mt-4 pt-4 border-t border-gray-100">
      <div class="flex items-center justify-between mb-2">
        <span class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Raw Extracted Text</span>
        <span class="text-xs ${data.indexed ? 'text-green-500' : 'text-gray-400'}">
          ${data.indexed ? '✓ Indexed in AI Search' : 'Not indexed'}
        </span>
      </div>
      <div class="json-block text-xs max-h-48 overflow-y-auto">${escHtml(data.raw_content.slice(0, 2000))}${data.raw_content.length > 2000 ? '\n…(truncated)' : ''}</div>
    </div>` : ''}
  `;
}

async function doLLMAnalysis() {
  const docId = document.getElementById('analyze-doc-id').value.trim();
  if (!docId) { showToast('Enter a document ID first', true); return; }

  // Use raw content from last extraction, or fetch it
  let content = state.lastAnalysis?.raw_content;
  if (!content) {
    showToast('Run extraction first to get document content', true);
    return;
  }

  showLoading('Asking GPT-4o to analyze document…');
  const panel = document.getElementById('llm-analysis-panel');
  const contentEl = document.getElementById('llm-analysis-content');

  try {
    const data = await apiFetch('/api/chat/analyze-text', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });

    panel.classList.remove('hidden');
    contentEl.innerHTML = markdownToHtml(data.analysis);
    panel.scrollIntoView({ behavior: 'smooth', block: 'start' });

  } catch (e) {
    panel.classList.remove('hidden');
    contentEl.innerHTML = errorBlock(e.message);
  } finally {
    hideLoading();
  }
}

// ── Search ────────────────────────────────────────────────────
async function doSearch() {
  const query = document.getElementById('search-query').value.trim();
  if (!query) { showToast('Enter a search query', true); return; }

  const top = document.getElementById('search-top').value;
  const semantic = document.getElementById('semantic-toggle').checked;
  const docFilter = document.getElementById('search-doc-filter').value.trim();

  const resultsEl = document.getElementById('search-results');
  resultsEl.innerHTML = '<div class="flex items-center gap-3 py-6 text-gray-400"><div class="spinner"></div> Searching…</div>';

  const params = new URLSearchParams({ q: query, top, semantic });
  if (docFilter) params.append('doc_id', docFilter);

  try {
    const data = await apiFetch(`/api/search?${params}`);

    if (!data.results.length) {
      resultsEl.innerHTML = '<p class="text-gray-400 text-sm text-center py-8">No results found. Make sure you\'ve analyzed and indexed a document first.</p>';
      return;
    }

    resultsEl.innerHTML = `
      <p class="text-xs text-gray-400 mb-3">${data.total} result${data.total !== 1 ? 's' : ''} for "<strong>${escHtml(query)}</strong>"</p>
      ${data.results.map((r, i) => `
        <div class="search-card">
          <div class="flex items-start justify-between gap-2 mb-2">
            <div class="flex items-center gap-2">
              <span class="bg-azure-100 text-azure-700 text-xs font-bold px-2 py-0.5 rounded">#${i+1}</span>
              <span class="text-xs text-gray-500 font-medium">${escHtml(r.filename)}</span>
            </div>
            <span class="text-xs text-gray-400 shrink-0">score: ${r.score.toFixed(3)}</span>
          </div>
          ${r.highlights.length
            ? r.highlights.map(h => `<p class="text-sm text-gray-700 leading-relaxed">${h}</p>`).join('')
            : `<p class="text-sm text-gray-700 leading-relaxed">${escHtml(r.chunk.slice(0, 300))}…</p>`
          }
        </div>
      `).join('')}
    `;
  } catch (e) {
    resultsEl.innerHTML = errorBlock(e.message);
  }
}

// ── Chat ──────────────────────────────────────────────────────
async function doChat() {
  const input = document.getElementById('chat-input');
  const message = input.value.trim();
  if (!message) return;

  const docId = document.getElementById('chat-doc-id').value.trim() || null;
  const useRag = document.getElementById('rag-toggle').checked;

  // Add user message to UI
  appendChatMessage('user', message);
  state.chatHistory.push({ role: 'user', content: message });
  input.value = '';
  input.style.height = 'auto';

  // Show typing indicator
  const typingId = appendChatMessage('assistant', '…', true);

  document.getElementById('chat-send-btn').disabled = true;

  try {
    const data = await apiFetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: state.chatHistory,
        doc_id: docId,
        use_rag: useRag,
      }),
    });

    // Replace typing indicator with real response
    document.getElementById(typingId)?.remove();
    appendChatMessage('assistant', data.reply);
    state.chatHistory.push({ role: 'assistant', content: data.reply });

    // Show sources if any
    renderChatSources(data.sources || []);

  } catch (e) {
    document.getElementById(typingId)?.remove();
    appendChatMessage('assistant', `❌ Error: ${e.message}`);
  } finally {
    document.getElementById('chat-send-btn').disabled = false;
    input.focus();
  }
}

function appendChatMessage(role, content, isTyping = false) {
  const id = `msg-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const messagesEl = document.getElementById('chat-messages');

  const bubble = `
    <div id="${id}" class="chat-msg ${role}">
      <div class="chat-bubble ${role}-bubble ${isTyping ? 'opacity-50 italic' : ''}">
        ${role === 'assistant' ? markdownToHtml(content) : escHtml(content)}
      </div>
    </div>`;

  messagesEl.insertAdjacentHTML('beforeend', bubble);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return id;
}

function renderChatSources(sources) {
  const panel = document.getElementById('chat-sources');
  const list = document.getElementById('chat-sources-list');

  if (!sources.length) {
    panel.classList.add('hidden');
    return;
  }

  panel.classList.remove('hidden');
  list.innerHTML = sources.map((s, i) =>
    `<p class="text-xs text-azure-700">
      <span class="font-semibold">[${i+1}]</span>
      ${escHtml(s.filename)} — ${escHtml(s.chunk.slice(0, 100))}…
    </p>`
  ).join('');
}

function setPrompt(text) {
  document.getElementById('chat-input').value = text;
  document.getElementById('chat-input').focus();
}

function clearChat() {
  state.chatHistory = [];
  const el = document.getElementById('chat-messages');
  el.innerHTML = `
    <div class="chat-msg assistant">
      <div class="chat-bubble assistant-bubble">
        Chat cleared. Ask me anything about your document.
      </div>
    </div>`;
  document.getElementById('chat-sources').classList.add('hidden');
}

// ── API helper ────────────────────────────────────────────────
async function apiFetch(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const err = await res.json();
      detail = err.detail || JSON.stringify(err);
    } catch {}
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json();
}

// ── UI helpers ────────────────────────────────────────────────
function showLoading(msg = 'Processing…') {
  document.getElementById('loading-msg').textContent = msg;
  document.getElementById('loading').classList.remove('hidden');
}
function hideLoading() {
  document.getElementById('loading').classList.add('hidden');
}

let toastTimer;
function showToast(msg, isError = false) {
  const el = document.getElementById('toast');
  const msgEl = document.getElementById('toast-msg');
  msgEl.textContent = msg;
  el.className = `fixed bottom-6 right-6 text-white text-sm px-5 py-3 rounded-xl shadow-2xl z-50 transition-all
    ${isError ? 'bg-red-600' : 'bg-gray-900'}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.add('hidden'), 3500);
}

function errorBlock(msg) {
  return `<div class="bg-red-50 border border-red-200 rounded-xl p-4">
    <p class="text-red-600 text-sm font-medium">Error</p>
    <p class="text-red-500 text-xs mt-1">${escHtml(msg)}</p>
  </div>`;
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function formatBytes(b) {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / (1024 * 1024)).toFixed(1)} MB`;
}

function fileIcon(name) {
  const ext = name.split('.').pop()?.toLowerCase();
  return { pdf: '📄', txt: '📝', docx: '📋', doc: '📋', png: '🖼️', jpg: '🖼️', jpeg: '🖼️' }[ext] || '📁';
}

/** Minimal markdown → HTML (bold, headers, lists, line breaks) */
function markdownToHtml(text) {
  return escHtml(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^### (.+)$/gm, '<h3 class="font-semibold text-gray-800 mt-3 mb-1 text-sm">$1</h3>')
    .replace(/^## (.+)$/gm,  '<h2 class="font-semibold text-gray-800 mt-4 mb-1">$1</h2>')
    .replace(/^# (.+)$/gm,   '<h1 class="font-bold text-gray-900 mt-4 mb-2 text-lg">$1</h1>')
    .replace(/^\d+\. (.+)$/gm, '<li class="ml-4 text-sm text-gray-700">$1</li>')
    .replace(/^[-*] (.+)$/gm,  '<li class="ml-4 list-disc text-sm text-gray-700">$1</li>')
    .replace(/\n\n/g, '</p><p class="mb-2">')
    .replace(/\n/g, '<br />');
}
