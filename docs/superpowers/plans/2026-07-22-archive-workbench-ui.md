# Archive Workbench UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the sparse single-page review UI with a compact, responsive archive workbench while preserving every existing API contract.

**Architecture:** Move the presentation out of `app.main.index` into a dedicated HTML template. The API continues to serve the template at `GET /`; its client-side code continues to call the existing upload, batch processing, review, and export endpoints. The redesign is entirely presentation-layer work.

**Tech Stack:** FastAPI, Python, HTML, CSS, vanilla JavaScript, pytest/TestClient.

---

### Task 1: Lock the page contract with a response test

**Files:**
- Modify: `tests/test_api.py`

- [ ] **Step 1: Add the failing archive-workbench test**

```python
def test_index_exposes_archive_workbench_landmarks(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert 'class="workbench"' in response.text
    assert 'id="files"' in response.text
    assert 'id="rows"' in response.text
    assert "上传资料" in response.text
    assert "处理待办" in response.text
    assert "导出已确认" in response.text
```

- [ ] **Step 2: Run the test to verify RED**

Run: `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_api.py::test_index_exposes_archive_workbench_landmarks -q`

Expected: FAIL because the current root page does not expose `class="workbench"`.

### Task 2: Build the archive-workbench template

**Files:**
- Create: `app/templates/index.html`

- [ ] **Step 1: Add the semantic page structure**

Create a `main.workbench` with these stable landmarks:

```html
<header class="masthead">
  <div class="brand"><span class="kicker">LOCAL ARCHIVE / REVIEW</span><h1>资料整理 Agent</h1></div>
  <button class="export-action" onclick="download()">导出已确认</button>
</header>
<section class="operations" aria-label="批次操作">
  <label class="upload-control"><input id="files" type="file" multiple>选择资料</label>
  <button class="primary-action" onclick="upload()">上传资料</button>
  <button class="secondary-action" onclick="processBatch()">处理待办</button>
  <p id="status" role="status">上传资料后开始审核。</p>
</section>
<section class="review-surface" aria-label="审核队列">
  <table><thead>...</thead><tbody id="rows"></tbody></table>
</section>
```

- [ ] **Step 2: Implement the compact visual token system**

Use CSS variables exactly for the approved palette and give table rows a narrow left archive tag:

```css
:root { --paper:#f2f3ef; --ink:#183b3a; --archive:#fff; --vermilion:#c55438; }
.document-row { border-left: 5px solid var(--ink); }
.document-row[data-review="confirmed"] { border-left-color: #4f7a61; }
.document-row[data-review="reprocess"], .document-row[data-status="failed"] { border-left-color: var(--vermilion); }
```

Add a desktop grid for compact controls, sticky table headers, focused field styling, an empty-row message, a `prefers-reduced-motion` rule, and a `max-width: 760px` layout that turns rows into stacked archive cards without horizontal overflow.

- [ ] **Step 3: Keep the existing client-side behavior**

Implement `upload`, `processBatch`, `refresh`, `save`, and `download` against the existing endpoints. In `refresh`, render values through an HTML escaping helper and apply status attributes:

```javascript
function escapeHtml(value = "") {
  return String(value).replace(/[&<>'"]/g, char => ({
    "&":"&amp;", "<":"&lt;", ">":"&gt;", "'":"&#39;", '"':"&quot;"
  })[char]);
}
```

Render no raw text, redacted text, extracted text, or source locations. Preserve human edits for classification, summary, review status, and reviewer notes.

### Task 3: Serve the template and complete verification

**Files:**
- Modify: `app/main.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Replace the inline document response**

Add a template path near the imports and change the route to read the template with UTF-8 encoding:

```python
TEMPLATE_PATH = Path(__file__).parent / "templates" / "index.html"

@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return TEMPLATE_PATH.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run the focused test to verify GREEN**

Run: `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_api.py::test_index_exposes_archive_workbench_landmarks -q`

Expected: PASS.

- [ ] **Step 3: Run the full regression suite**

Run: `.\\.venv\\Scripts\\python.exe -m pytest -q`

Expected: all API, parsing, and domain tests pass.

- [ ] **Step 4: Inspect rendered desktop and mobile states**

Start the local server, open `/`, and verify: page title and action strip fit at desktop width; empty state prompts for an upload; table headers remain readable; mobile rows stack; focus outlines remain visible; and no raw or redacted content appears in the browser.

## Plan Self-Review

- Spec coverage: Tasks 1-3 cover the approved archive-workbench structure, palette, dense rows, archive tags, responsive behavior, accessibility, API preservation, and verification.
- Placeholder scan: no incomplete implementation instructions or deferred work remain.
- Type consistency: all new DOM ids preserve the existing client API contract; Python uses the existing `Path` and `HTMLResponse` imports.
