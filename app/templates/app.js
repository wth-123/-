(() => {
  'use strict';

  const apiBase = (window.API_BASE || '').replace(/\/$/, '');
  const passwordKey = 'archiveAccessPassword';
  const expiryKey = 'archiveAccessPasswordExpiry';
  const gate = document.querySelector('#access-gate');
  const form = document.querySelector('#access-form');
  const passwordInput = document.querySelector('#access-password');
  const submitButton = document.querySelector('#access-submit');
  const feedback = document.querySelector('#access-feedback');
  const status = document.querySelector('#status');
  const rows = document.querySelector('#rows');
  let batchId = '';
  let memoryPassword = '';

  const text = {
    checking: '\u6b63\u5728\u9a8c\u8bc1...',
    checkingAccess: '\u6b63\u5728\u6838\u9a8c\u8bbf\u95ee\u6743\u9650',
    enter: '\u8fdb\u5165\u5ba1\u6838\u53f0',
    success: '\u767b\u5f55\u6210\u529f\uff0c\u6b63\u5728\u8fdb\u5165\u5ba1\u6838\u53f0',
    empty: '\u8bf7\u8f93\u5165\u8bbf\u95ee\u5bc6\u7801',
    invalid: '\u5bc6\u7801\u4e0d\u6b63\u786e\uff0c\u8bf7\u91cd\u65b0\u8f93\u5165',
    unavailable: '\u6682\u65f6\u65e0\u6cd5\u9a8c\u8bc1\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5',
    expired: '\u5bc6\u7801\u5df2\u5931\u6548\uff0c\u8bf7\u91cd\u65b0\u8f93\u5165',
    selectFile: '\u8bf7\u9009\u62e9\u81f3\u5c11\u4e00\u4efd\u8d44\u6599\u3002',
    uploading: '\u6b63\u5728\u4e0a\u4f20\u8d44\u6599...',
    uploadDone: '\u8d44\u6599\u5df2\u4e0a\u4f20\u3002',
    selectBatch: '\u8bf7\u5148\u4e0a\u4f20\u8d44\u6599\u3002',
    processing: '\u6b63\u5728\u5904\u7406\u5f85\u529e\u8d44\u6599...'
  };

  const escapeHtml = (value = '') => String(value).replace(/[&<>'"]/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  }[char]));

  function setMetric(id, value) {
    document.querySelector(id).textContent = value || 0;
  }

  function clearPassword() {
    memoryPassword = '';
    try {
      localStorage.removeItem(passwordKey);
      localStorage.removeItem(expiryKey);
    } catch {}
  }

  function savedPassword() {
    try {
      const expiry = Number(localStorage.getItem(expiryKey) || 0);
      if (!expiry || expiry < Date.now()) {
        clearPassword();
        return '';
      }
      return localStorage.getItem(passwordKey) || memoryPassword;
    } catch {
      return memoryPassword;
    }
  }

  function savePassword(password) {
    memoryPassword = password;
    try {
      localStorage.setItem(passwordKey, password);
      localStorage.setItem(expiryKey, String(Date.now() + 7 * 24 * 60 * 60 * 1000));
    } catch {}
  }

  function setGateState(state, message = '', tone = '') {
    form.dataset.state = state;
    submitButton.disabled = state === 'pending';
    submitButton.textContent = state === 'pending' ? text.checking : text.enter;
    passwordInput.setAttribute('aria-invalid', tone === 'error' ? 'true' : 'false');
    feedback.textContent = message;
    feedback.dataset.tone = tone;
  }

  function showGate(message = '', tone = '') {
    gate.hidden = false;
    setGateState(tone === 'error' ? 'error' : 'idle', message, tone);
    if (tone === 'error') passwordInput.focus();
  }

  function enterWorkbench() {
    setGateState('success', text.success, 'success');
    window.setTimeout(() => { gate.hidden = true; }, 420);
  }

  async function verifyPassword(password) {
    if (!apiBase) throw new Error('API endpoint is not configured');
    return fetch(`${apiBase}/access/verify`, {
      headers: { 'X-Access-Password': password }
    });
  }

  async function unlock(event) {
    event.preventDefault();
    const password = passwordInput.value;
    if (!password) {
      showGate(text.empty, 'error');
      return;
    }
    setGateState('pending', text.checkingAccess);
    try {
      const response = await verifyPassword(password);
      if (response.status === 401) {
        showGate(text.invalid, 'error');
        return;
      }
      if (!response.ok) {
        showGate(text.unavailable, 'error');
        return;
      }
      savePassword(password);
      enterWorkbench();
    } catch {
      showGate(text.unavailable, 'error');
    }
  }

  async function restoreAccess() {
    const password = savedPassword();
    if (!password) {
      showGate();
      return;
    }
    setGateState('pending', text.checkingAccess);
    try {
      const response = await verifyPassword(password);
      if (response.ok) {
        enterWorkbench();
        return;
      }
      clearPassword();
      showGate(text.expired, 'error');
    } catch {
      showGate(text.unavailable, 'error');
    }
  }

  async function apiFetch(path, options = {}) {
    const headers = new Headers(options.headers || {});
    const password = savedPassword();
    if (password) headers.set('X-Access-Password', password);
    const response = await fetch(`${apiBase}${path}`, { ...options, headers });
    if (response.status === 401) {
      clearPassword();
      showGate(text.expired, 'error');
      throw new Error('Access password required');
    }
    return response;
  }

  function documentRow(item) {
    const review = item.review_status || 'pending';
    const state = item.status || 'uploaded';
    return `<tr class="document-row" data-review="${escapeHtml(review)}" data-status="${escapeHtml(state)}"><td><span class="file-name">${escapeHtml(item.filename)}</span><span class="file-meta">${escapeHtml(item.document_type || '')} / ${escapeHtml(state)}</span></td><td><input class="review-field" id="c-${item.id}" value="${escapeHtml(item.classification)}"></td><td><textarea class="review-field" id="s-${item.id}">${escapeHtml(item.summary)}</textarea></td><td><span class="confidence">${Number(item.confidence || 0).toFixed(2)}</span></td><td><select class="review-field" id="r-${item.id}"><option value="pending">pending</option><option value="confirmed">confirmed</option><option value="reprocess">reprocess</option></select></td><td><textarea class="review-field" id="n-${item.id}">${escapeHtml(item.reviewer_notes)}</textarea></td><td><button class="save-action" type="button" onclick="save('${item.id}')">Save</button></td></tr>`;
  }

  window.refresh = async function () {
    if (!batchId) return;
    const response = await apiFetch(`/batches/${batchId}`);
    const result = await response.json();
    setMetric('#processed-count', result.progress.processed);
    setMetric('#failed-count', result.progress.failed);
    setMetric('#pending-count', result.documents.filter(item => item.review_status === 'pending').length);
    rows.innerHTML = result.documents.length ? result.documents.map(documentRow).join('') : '<tr class="empty-row"><td colspan="7">No documents uploaded.</td></tr>';
    result.documents.forEach(item => {
      const field = document.querySelector(`#r-${item.id}`);
      if (field) field.value = item.review_status || 'pending';
    });
  };

  window.upload = async function () {
    const data = new FormData();
    for (const file of document.querySelector('#files').files) data.append('files', file);
    if (!data.has('files')) {
      status.textContent = text.selectFile;
      return;
    }
    status.textContent = text.uploading;
    const response = await apiFetch('/documents', { method: 'POST', body: data });
    const result = await response.json();
    batchId = result.batch_id;
    status.textContent = text.uploadDone;
    await window.refresh();
  };

  window.processBatch = async function () {
    if (!batchId) {
      status.textContent = text.selectBatch;
      return;
    }
    status.textContent = text.processing;
    await apiFetch(`/batches/${batchId}/process`, { method: 'POST' });
    await window.refresh();
  };

  window.save = async function (id) {
    const payload = {
      classification: document.querySelector(`#c-${id}`).value,
      summary: document.querySelector(`#s-${id}`).value,
      review_status: document.querySelector(`#r-${id}`).value,
      reviewer_notes: document.querySelector(`#n-${id}`).value
    };
    await apiFetch(`/documents/${id}/review`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    await window.refresh();
  };

  window.download = async function () {
    if (!batchId) {
      status.textContent = text.selectBatch;
      return;
    }
    const response = await apiFetch(`/batches/${batchId}/export`);
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement('a');
    link.href = url;
    link.download = 'confirmed-documents.xlsx';
    link.click();
    URL.revokeObjectURL(url);
  };

  form.addEventListener('submit', unlock);
  restoreAccess();
})();
