"""Local demonstration dashboard backed exclusively by MongoDB."""

from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import date, datetime, timezone
import json
import logging
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from zipfile import BadZipFile
from xml.etree.ElementTree import ParseError

from bson import ObjectId
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pymongo import MongoClient, ReturnDocument
from pymongo.errors import PyMongoError

from src.project_health_agent import ProjectHealthAgent

ROOT = Path(__file__).resolve().parent.parent
LOGGER = logging.getLogger(__name__)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
SAMPLE_FILES = ("S2P Project (1).xlsx", "Project Plan B (1).xlsx")


@asynccontextmanager
async def lifespan(app: FastAPI):
    client: MongoClient = MongoClient(
        os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017"),
        serverSelectionTimeoutMS=3000,
        connectTimeoutMS=3000,
        socketTimeoutMS=10000,
        tz_aware=True,
    )
    app.state.database = client[os.getenv("MONGODB_DATABASE", "project_health")]
    try:
        yield
    finally:
        client.close()


app = FastAPI(title="Project Health MongoDB API", lifespan=lifespan)


@app.exception_handler(PyMongoError)
async def database_error(request: Request, exc: PyMongoError):
    LOGGER.error("MongoDB operation failed on %s: %s", request.url.path, type(exc).__name__)
    return JSONResponse(
        status_code=503,
        content={"detail": "MongoDB is unavailable. Start MongoDB and check the server configuration."},
    )


class AnalyzeSamples(BaseModel):
    as_of: date = date(2026, 7, 9)


class ReportNotes(BaseModel):
    notes: str = Field(max_length=2000)


def object_id(report_id: str) -> ObjectId:
    if not ObjectId.is_valid(report_id):
        raise HTTPException(422, "Invalid MongoDB document ID.")
    return ObjectId(report_id)


def serialize(document: dict[str, Any]) -> dict[str, Any]:
    return {**document, "_id": str(document["_id"])}


def analyze(path: Path, as_of: date, source_name: str) -> dict[str, Any]:
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    result = asdict(ProjectHealthAgent(as_of, config).evaluate(path))
    if not result["metrics"]["total_tasks"]:
        raise HTTPException(422, "The workbook does not contain recognizable project tasks.")
    result["source_file"] = source_name
    now = datetime.now(timezone.utc)
    return {**result, "created_at": now, "updated_at": now, "notes": "", "analysis_mode": "deterministic"}


@app.get("/api/health")
def health(request: Request):
    db = request.app.state.database
    db.command("ping")
    return {
        "status": "connected",
        "database": db.name,
        "collection": "reports",
        "document_count": db.reports.count_documents({}),
        "storage": "MongoDB",
    }


@app.get("/api/reports")
def list_reports(request: Request, page: int = 1):
    if page < 1:
        raise HTTPException(422, "Page must be at least 1.")
    collection = request.app.state.database.reports
    documents = collection.find().sort([("created_at", -1), ("_id", -1)]).skip((page - 1) * 20).limit(20)
    return {
        "items": [serialize(document) for document in documents],
        "total": collection.count_documents({}),
        "page": page,
        "page_size": 20,
    }


@app.post("/api/reports/samples", status_code=201)
def create_samples(body: AnalyzeSamples, request: Request):
    documents = [analyze(ROOT / name, body.as_of, name) for name in SAMPLE_FILES]
    request.app.state.database.reports.insert_many(documents, ordered=True)
    return {"items": [serialize(document) for document in documents]}


@app.post("/api/reports/upload", status_code=201)
def upload_report(
    request: Request,
    file: UploadFile = File(...),
    as_of: date = Form(...),
):
    filename = (file.filename or "").replace("\\", "/").split("/")[-1]
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(422, "Please upload an .xlsx project plan.")
    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "The upload limit is 10 MB.")
    with TemporaryDirectory() as directory:
        path = Path(directory) / "project.xlsx"
        path.write_bytes(content)
        try:
            document = analyze(path, as_of, filename)
        except (BadZipFile, ParseError, KeyError, ValueError, StopIteration) as exc:
            LOGGER.warning("Invalid workbook upload: %s", type(exc).__name__)
            raise HTTPException(422, "Invalid or unsupported Excel workbook.") from exc
    request.app.state.database.reports.insert_one(document)
    return serialize(document)


@app.get("/api/reports/{report_id}")
def get_report(report_id: str, request: Request):
    document = request.app.state.database.reports.find_one({"_id": object_id(report_id)})
    if document is None:
        raise HTTPException(404, "Report not found.")
    return serialize(document)


@app.patch("/api/reports/{report_id}")
def update_notes(report_id: str, body: ReportNotes, request: Request):
    document = request.app.state.database.reports.find_one_and_update(
        {"_id": object_id(report_id)},
        {"$set": {"notes": body.notes, "updated_at": datetime.now(timezone.utc)}},
        return_document=ReturnDocument.AFTER,
    )
    if document is None:
        raise HTTPException(404, "Report not found.")
    return serialize(document)


@app.delete("/api/reports/{report_id}", status_code=204)
def delete_report(report_id: str, request: Request):
    result = request.app.state.database.reports.delete_one({"_id": object_id(report_id)})
    if not result.deleted_count:
        raise HTTPException(404, "Report not found.")


app.mount("/", StaticFiles(directory=ROOT / "frontend", html=True), name="frontend")
