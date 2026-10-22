"""Dedicated authenticated client API. Never exposes admin training or datasets."""

import logging
import re
import secrets
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Depends, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from . import auth, config
from .store import Store

logger = logging.getLogger(__name__)


class Signup(BaseModel):
    username: str = Field(min_length=2, max_length=40)
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)


class Login(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)


class Correction(BaseModel):
    text: str = Field(min_length=1, max_length=1500)


def create_app(store=None, pipeline=None, data_dir=None):
    data = Path(data_dir or config.DATA)
    data.mkdir(parents=True, exist_ok=True)
    repo = store or Store()
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="slsl-client")
    import threading

    job_lock = threading.RLock()
    engine = pipeline

    @asynccontextmanager
    async def lifespan(app):
        for job in repo.find("jobs"):
            if job["stage"] not in ("done", "error"):
                job.update(
                    stage="error",
                    error="The service restarted. Please submit the recording again.",
                )
                repo.save("jobs", job)
        yield
        executor.shutdown(wait=True, cancel_futures=True)

    api = FastAPI(title="SLSL Connect — client API", version="1.0.0", lifespan=lifespan)

    def require_user(authorization: str = Header(default="")):
        if not authorization.startswith("Bearer "):
            raise HTTPException(401, "Please sign in.")
        session = repo.get("sessions", auth.token_hash(authorization[7:]))
        if not session or session["expires"] < time.time():
            raise HTTPException(401, "Your session expired. Please sign in again.")
        user = repo.get("users", session["user_id"])
        if not user:
            raise HTTPException(401, "Please sign in.")
        return user

    def public(user):
        return {k: user[k] for k in ("id", "username", "email")}

    def session(user):
        token = secrets.token_urlsafe(48)
        repo.save(
            "sessions",
            dict(
                id=auth.token_hash(token),
                user_id=user["id"],
                expires=time.time() + 7 * 86400,
            ),
        )
        return dict(token=token, user=public(user))

    def owned(id, user):
        row = repo.get("jobs", id)
        if not row or row["user_id"] != user["id"]:
            raise HTTPException(404, "Recording not found.")
        return row

    def payload(row):
        return {k: v for k, v in row.items() if k != "user_id"}

    @api.get("/health")
    def health():
        return dict(status="ok", storage=repo.mode)

    @api.post("/auth/signup", status_code=201)
    def signup(body: Signup, request: Request):
        auth.throttle(("signup", request.client.host))
        name = body.username.strip()
        if not re.fullmatch(r"[\w .'-]{2,40}", name):
            raise HTTPException(
                422,
                "Use 2–40 letters, numbers, spaces or simple punctuation for your name.",
            )
        email = auth.email_address(body.email)
        auth.password_check(body.password, name, email)
        user = dict(
            id=uuid.uuid4().hex,
            username=name,
            email=email,
            password_hash=auth.hasher.hash(body.password),
        )
        try:
            repo.save("users", user, insert=True)
        except Exception as exc:
            from pymongo.errors import DuplicateKeyError
            import sqlite3

            if isinstance(exc, (DuplicateKeyError, sqlite3.IntegrityError)):
                raise HTTPException(
                    409, "An account with this email already exists."
                ) from exc
            raise
        return session(user)

    @api.post("/auth/login")
    def login(body: Login, request: Request):
        email = auth.email_address(body.email)
        auth.throttle(("login", request.client.host))
        users = repo.find("users", email=email)
        user = users[0] if users else None
        valid = auth.verify(body.password, user["password_hash"] if user else None)
        if not user or not valid:
            raise HTTPException(401, "Email or password is incorrect.")
        return session(user)

    @api.get("/auth/me")
    def me(user=Depends(require_user)):
        return public(user)

    @api.post("/auth/logout", status_code=204)
    def logout(user=Depends(require_user), authorization: str = Header()):
        repo.delete("sessions", auth.token_hash(authorization[7:]))

    def update(id, **fields):
        with job_lock:
            row = repo.get("jobs", id)
            if row:
                row.update(**fields)
                repo.save("jobs", row)

    def process(id):
        nonlocal engine
        try:
            if engine is None:
                from .pipeline import Pipeline

                engine = Pipeline()
            engine.run(
                data / (id + ".csv"),
                lambda **fields: update(id, **fields),
                data / (id + ".wav"),
            )
        except Exception:
            logger.exception("Client recognition job failed: %s", id)
            row = repo.get("jobs", id)
            message = "This recording could not be processed. Try again or check that all local models are installed."
            if row and row.get("sinhala"):
                message = "Sinhala text is ready, but the voice could not be created. Please retry."
            elif row and row.get("sentence"):
                message = "Words are ready, but Sinhala processing could not finish. Please retry."
            update(id, stage="error", error=message)
        finally:
            (data / (id + ".csv")).unlink(missing_ok=True)

    @api.get("/recognitions")
    def history(user=Depends(require_user)):
        return [
            payload(row)
            for row in sorted(
                repo.find("jobs", user_id=user["id"]),
                key=lambda r: r["created"],
                reverse=True,
            )[:50]
        ]

    @api.post("/recognitions", status_code=202)
    async def recognize(file: UploadFile = File(), user=Depends(require_user)):
        from .pipeline import validate_csv

        if not (file.filename or "").lower().endswith(".csv"):
            raise HTTPException(422, "Choose a CSV motion recording.")
        raw = await file.read(8 * 1024 * 1024 + 1)
        await file.close()
        if len(raw) > 8 * 1024 * 1024:
            raise HTTPException(413, "Use a CSV smaller than 8 MB.")
        try:
            raw = validate_csv(raw)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        with job_lock:
            all_jobs = repo.find("jobs")
            waiting = [r for r in all_jobs if r["stage"] not in ("done", "error")]
            if any(r["user_id"] == user["id"] for r in waiting):
                raise HTTPException(409, "Your previous recording is still processing.")
            if len(waiting) >= 4:
                raise HTTPException(
                    429, "The local model is busy. Please try again shortly."
                )
            id = uuid.uuid4().hex
            (data / (id + ".csv")).write_bytes(raw)
            row = dict(
                id=id,
                user_id=user["id"],
                filename=Path(file.filename).name[:100],
                created=time.time(),
                stage="queued",
                words=[],
                audio_ready=False,
            )
            repo.save("jobs", row, insert=True)
            executor.submit(process, id)
        return payload(row)

    @api.get("/recognitions/{id}")
    def result(id: str, user=Depends(require_user)):
        return payload(owned(id, user))

    @api.post("/recognitions/{id}/retry", status_code=202)
    def retry(id: str, user=Depends(require_user)):
        nonlocal engine
        with job_lock:
            row = owned(id, user)
            if row["stage"] != "error" or not row.get("sentence", {}).get("text"):
                raise HTTPException(
                    409, "Choose the CSV again to retry motion recognition."
                )
            waiting = [
                j for j in repo.find("jobs") if j["stage"] not in ("done", "error")
            ]
            if any(j["user_id"] == user["id"] for j in waiting) or len(waiting) >= 4:
                raise HTTPException(429, "The local model is busy. Please wait.")
            update(
                id,
                stage="voice" if row.get("sinhala") else "translation",
                error=None,
                audio_ready=False,
            )

        def resume_job():
            nonlocal engine
            try:
                if engine is None:
                    from .pipeline import Pipeline

                    engine = Pipeline()
                engine.resume(
                    row, lambda **fields: update(id, **fields), data / (id + ".wav")
                )
            except Exception:
                logger.exception("Client speech retry failed: %s", id)
                update(
                    id,
                    stage="error",
                    error="Local Sinhala processing could not finish. Please retry when the PC has more free memory.",
                )

        executor.submit(resume_job)
        return payload(repo.get("jobs", id))

    @api.get("/recognitions/{id}/audio")
    def audio(id: str, user=Depends(require_user)):
        row = owned(id, user)
        path = data / (row["id"] + ".wav")
        if not row.get("audio_ready") or not path.is_file():
            raise HTTPException(404, "Voice output is not ready.")
        return FileResponse(
            path, media_type="audio/wav", headers={"Cache-Control": "no-store"}
        )

    @api.delete("/recognitions/{id}", status_code=204)
    def delete(id: str, user=Depends(require_user)):
        with job_lock:
            row = owned(id, user)
            if row["stage"] not in ("done", "error"):
                raise HTTPException(
                    409, "Wait until recognition finishes before removing it."
                )
            repo.delete("jobs", id)
            for ext in (".wav", ".csv"):
                (data / (id + ext)).unlink(missing_ok=True)

    @api.patch("/recognitions/{id}/sinhala", status_code=202)
    def correct(id: str, body: Correction, user=Depends(require_user)):
        text = body.text.strip()
        if not re.search(r"[\u0d80-\u0dff]", text):
            raise HTTPException(422, "Enter a Sinhala sentence.")
        with job_lock:
            row = owned(id, user)
            if row["stage"] not in ("done", "error") or not row.get("sinhala"):
                raise HTTPException(409, "Wait for a Sinhala translation first.")
            waiting = [
                j for j in repo.find("jobs") if j["stage"] not in ("done", "error")
            ]
            if any(j["user_id"] == user["id"] for j in waiting) or len(waiting) >= 4:
                raise HTTPException(
                    429,
                    "The local model is busy. Please wait before regenerating speech.",
                )
            update(
                id,
                stage="voice",
                machine_sinhala=row.get("machine_sinhala", row["sinhala"]),
                sinhala=text,
                edited=True,
                audio_ready=False,
                error=None,
            )
            (data / (id + ".wav")).unlink(missing_ok=True)

        def regenerate():
            try:
                from app.ml.sinhala_speech import synthesize_sinhala

                (data / (id + ".wav")).write_bytes(
                    synthesize_sinhala(text, row.get("expression", {}).get("label"))
                )
                update(id, stage="done", audio_ready=True)
            except Exception:
                logger.exception("Corrected speech failed")
                update(
                    id, stage="error", error="Voice generation failed. Please retry."
                )

        executor.submit(regenerate)
        return payload(repo.get("jobs", id))

    return api
