from __future__ import annotations

import hmac
import json
import os
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from openpyxl import Workbook
from pydantic import BaseModel

from .domain.models import BatchRecord, DocumentRecord, DocumentStatus, ReviewStatus
from .domain.organization import organize_document
from .domain.provider import MockModelProvider
from .parsing import ParseDocumentError, parse_document
from .store import store

ACCESS_HEADER = "X-Access-Password"
ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000").split(",") if origin.strip()]

app = FastAPI(title="Local Document Organizer")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", ACCESS_HEADER],
)
SUPPORTED_SUFFIXES = {".pdf", ".docx", ".xlsx", ".xlsm", ".csv"}
EXPORT_HEADERS = ["来源文件", "资料类型", "分类", "摘要", "关键字段", "置信度", "依据", "审核状态", "人工备注"]


def require_shared_password(request: Request) -> None:
    configured_password = os.getenv("APP_ACCESS_PASSWORD")
    if not configured_password:
        raise HTTPException(status_code=503, detail="Access password is not configured")
    presented_password = request.headers.get(ACCESS_HEADER, "")
    if not hmac.compare_digest(presented_password, configured_password):
        raise HTTPException(status_code=401, detail="Access password required")


class ReviewUpdate(BaseModel):
    classification: str | None = None
    summary: str | None = None
    key_fields: dict | None = None
    confidence: float | None = None
    evidence: list[dict] | None = None
    review_status: ReviewStatus | None = None
    reviewer_notes: str | None = None


def _require_batch(batch_id: str) -> BatchRecord:
    batch = store.batches.get(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return batch


def _require_document(document_id: str) -> DocumentRecord:
    document = store.documents.get(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


def _safe_document(document: DocumentRecord) -> dict:
    result = document.model_dump(
        exclude={"raw_text", "redacted_text", "extracted_text", "locations"}, mode="json"
    )
    result["filename"] = result.pop("source_filename")
    return result


def _progress(batch: BatchRecord) -> dict[str, int]:
    counts = {status.value: 0 for status in DocumentStatus}
    for document_id in batch.document_ids:
        counts[store.documents[document_id].status.value] += 1
    return counts


@app.get("/access/verify", status_code=204)
def verify_access(_: None = Depends(require_shared_password)) -> None:
    """Confirm a shared password without exposing any application data."""


@app.post("/documents")
async def upload_documents(
    files: list[UploadFile] = File(...),
    _: None = Depends(require_shared_password),
) -> dict:
    batch_id = uuid4().hex
    batch = BatchRecord(id=batch_id)
    store.batches[batch_id] = batch
    directory = store.upload_root / batch_id
    directory.mkdir(parents=True, exist_ok=True)
    documents, errors = [], []
    for upload in files:
        filename = Path(upload.filename or "upload").name
        if Path(filename).suffix.lower() not in SUPPORTED_SUFFIXES:
            errors.append({"filename": filename, "error": "不支持的文件类型"})
            continue
        document_id = uuid4().hex
        target = directory / f"{document_id}{Path(filename).suffix.lower()}"
        target.write_bytes(await upload.read())
        record = DocumentRecord(
            id=document_id,
            batch_id=batch_id,
            source_filename=filename,
            document_type="",
        )
        store.documents[document_id] = record
        batch.document_ids.append(document_id)
        documents.append({"id": document_id, "filename": filename, "status": record.status.value})
    return {"batch_id": batch_id, "documents": documents, "errors": errors}


@app.post("/batches/{batch_id}/process")
def process_batch(batch_id: str, _: None = Depends(require_shared_password)) -> dict:
    batch = _require_batch(batch_id)
    provider = MockModelProvider()
    for document_id in batch.document_ids:
        record = store.documents[document_id]
        eligible = record.status is DocumentStatus.UPLOADED or record.status is DocumentStatus.FAILED or record.review_status is ReviewStatus.REPROCESS
        if not eligible:
            continue
        record.status = DocumentStatus.PROCESSING
        record.error = None
        path = store.upload_root / batch_id / f"{record.id}{Path(record.source_filename).suffix.lower()}"
        try:
            parsed = parse_document(path)
            record.document_type = parsed.document_type.value
            record.raw_text = parsed.text
            record.extracted_text = parsed.text
            record.locations = [location.model_dump_json() for location in parsed.locations]
            organize_document(record, provider)
            record.review_status = ReviewStatus.PENDING
        except ParseDocumentError:
            record.status = DocumentStatus.FAILED
            record.error = "parse_error"
        except Exception:
            record.status = DocumentStatus.FAILED
            record.error = "processing_error"
    return {"batch_id": batch_id, "progress": _progress(batch)}


@app.get("/batches/{batch_id}")
def get_batch(batch_id: str, _: None = Depends(require_shared_password)) -> dict:
    batch = _require_batch(batch_id)
    return {"id": batch_id, "progress": _progress(batch), "documents": [_safe_document(store.documents[item]) for item in batch.document_ids]}


@app.patch("/documents/{document_id}/review")
def update_review(
    document_id: str,
    update: ReviewUpdate,
    _: None = Depends(require_shared_password),
) -> dict:
    record = _require_document(document_id)
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    return _safe_document(record)


@app.get("/batches/{batch_id}/export")
def export_batch(batch_id: str, _: None = Depends(require_shared_password)) -> StreamingResponse:
    batch = _require_batch(batch_id)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "审核结果"
    sheet.append(EXPORT_HEADERS)
    for document_id in batch.document_ids:
        record = store.documents[document_id]
        if record.review_status is not ReviewStatus.CONFIRMED:
            continue
        sheet.append([
            record.source_filename, record.document_type, record.classification, record.summary,
            json.dumps(record.key_fields, ensure_ascii=False), record.confidence,
            json.dumps(record.evidence, ensure_ascii=False), record.review_status.value, record.reviewer_notes,
        ])
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="{batch_id}-confirmed.xlsx"'}
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)


@app.get("/legacy", response_class=HTMLResponse, include_in_schema=False)
def index() -> str:
    return """<!doctype html><html lang=\"zh-CN\"><meta charset=\"utf-8\"><title>资料整理 Agent</title><style>body{font:14px Arial;margin:32px;background:#f6f8fa;color:#17202a}main{max-width:1200px;margin:auto}button,input,select,textarea{font:inherit;margin:4px}table{width:100%;border-collapse:collapse;background:#fff}th,td{padding:8px;border:1px solid #d0d7de;text-align:left;vertical-align:top}textarea{width:100%;min-height:54px}</style><main><h1>资料整理 Agent</h1><input id=\"files\" type=\"file\" multiple><button onclick=\"upload()\">上传资料</button><button onclick=\"processBatch()\">处理待办</button><button onclick=\"download()\">导出已确认 Excel</button><p id=\"status\"></p><table><thead><tr><th>文件</th><th>分类</th><th>摘要</th><th>置信度</th><th>审核</th><th>备注</th><th></th></tr></thead><tbody id=\"rows\"></tbody></table></main><script>let batch;const status=document.querySelector('#status');async function upload(){let d=new FormData;for(const f of files.files)d.append('files',f);let r=await fetch('/documents',{method:'POST',body:d});let x=await r.json();batch=x.batch_id;status.textContent='已上传 '+x.documents.length+' 份资料';await refresh()}async function processBatch(){if(!batch)return;await fetch('/batches/'+batch+'/process',{method:'POST'});await refresh()}async function refresh(){if(!batch)return;let x=await (await fetch('/batches/'+batch)).json();status.textContent='已处理 '+x.progress.processed+'，失败 '+x.progress.failed;rows.innerHTML=x.documents.map(d=>`<tr><td>${d.source_filename}<br>${d.status}</td><td><input value=\"${d.classification}\" id=\"c-${d.id}\"></td><td><textarea id=\"s-${d.id}\">${d.summary}</textarea></td><td>${d.confidence}</td><td><select id=\"r-${d.id}\"><option value=\"pending\">待审核</option><option value=\"confirmed\">确认</option><option value=\"reprocess\">重处理</option></select></td><td><textarea id=\"n-${d.id}\">${d.reviewer_notes}</textarea></td><td><button onclick=\"save('${d.id}')\">保存</button></td></tr>`).join('');x.documents.forEach(d=>document.querySelector('#r-'+d.id).value=d.review_status)}async function save(id){await fetch('/documents/'+id+'/review',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({classification:document.querySelector('#c-'+id).value,summary:document.querySelector('#s-'+id).value,review_status:document.querySelector('#r-'+id).value,reviewer_notes:document.querySelector('#n-'+id).value})});await refresh()}function download(){if(batch)location='/batches/'+batch+'/export'}</script></html>"""


TEMPLATE_PATH = Path(__file__).parent / "templates" / "index.html"


@app.get("/", response_class=HTMLResponse)
def archive_workbench() -> str:
    return TEMPLATE_PATH.read_text(encoding="utf-8")
