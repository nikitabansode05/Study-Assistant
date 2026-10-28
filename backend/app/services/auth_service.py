from pathlib import Path, PurePosixPath
import shutil
import uuid
import zipfile
from fastapi import Header, HTTPException
from app.helpers.auth import check_credentials, create_session, get_session,revoke_session
from app.config import CHAT_MODEL, EMBED_MODEL, OLLAMA_BASE_URL
from app.helpers.ollama_client import ollama_status
from app.schemas.tflrag_schemas import LoginRequest

class AuthService:

    def __init__(self,store):
        self.store = store
        print("Service object created")

    async def mentor_login(self,request: LoginRequest):
        if not await check_credentials(request.user_id, request.password):
            raise HTTPException(status_code=401, detail="Incorrect mentor user ID or password.")
        session = await create_session(request.user_id.strip().lower())
        return {"role": "mentor", "user_id": session["user_id"], "token": session["token"], "expires_at": session["expires_at"]}

    async def mentor_logout(self,authorization: str | None = Header(default=None)):
        session = await get_session(authorization)
        if session:
           await revoke_session(session["token"])
        return {"message": "Logged out", "role": "student"}

    async def current_role(self,authorization: str | None = Header(default=None)):
        session = await get_session(authorization)
        if not session:
            return {"role": "student", "authenticated": False}
        return {"role": "mentor", "authenticated": True, "user_id": session["user_id"]}

    async def health(self):
        return {
            "status": "ok",
            "chat_model": CHAT_MODEL,
            "embedding_model": EMBED_MODEL,
            "ollama_url": OLLAMA_BASE_URL,
            "indexed_documents": len(self.store.list_documents()),
            "ollama":await ollama_status(),
        }