from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# from app.api.routes.TFLrag_routes import router as TFLrag_routes
from .config import EXTRA_CORS_ORIGINS
from app.repositories.vector_store import TFLKnowledgeCore
# from app.services.TFLrag_service import TFLragService
from app.services.auth_service import AuthService
from app.services.doc_service import DocService
from app.services.rag_service import RagService

from app.api.routes.auth_router import router as auth_router
from app.api.routes.doc_router import router as doc_router
from app.api.routes.rag_router import router as rag_router

app = FastAPI(title="TFLCoMentor LocalRAG API", version="1.1.0")

allowed_origins = ["http://localhost:5173","http://127.0.0.1:5173","http://localhost:5174","http://127.0.0.1:5174","http://192.168.1.43:5173",*EXTRA_CORS_ORIGINS,]

# Vite moves to 5175, 5176, ... when 5173 is busy, and `vite preview` uses 4173.
# Allow any local port so the frontend never fails with a CORS error on a different port.
app.add_middleware(CORSMiddleware,allow_origins=allowed_origins,allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",allow_credentials=True,allow_methods=["*"],allow_headers=["*"],)

store = TFLKnowledgeCore()
# app.state.tflrag_service = TFLragService(store)
# app.state.auth_service = AuthService(store)
app.state.doc_service = DocService(store)
# app.state.rag_service = RagService(store)
# app.include_router(TFLrag_routes)
app.include_router(auth_router)
app.include_router(doc_router)
app.include_router(rag_router)
