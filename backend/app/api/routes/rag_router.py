from fastapi import APIRouter, Request
from fastapi import Depends, UploadFile, File, Header
from app.helpers.auth import require_mentor
from app.schemas.tflrag_schemas import ChatRequest, LoginRequest, LoginResponse, RepositoryRequest
from app.api.controllers.rag_controller import RagController
from app.repositories.vector_store import TFLKnowledgeCore
from app.services.rag_service import RagService

router = APIRouter(prefix="", tags=["TFLRAG"])


def get_rag_controller()->RagController:
    repository=TFLKnowledgeCore()
    service=RagService(repository)
    return RagController(service)

@router.post("/chat")
async def ask_question(chatrequest: ChatRequest,controller:RagController = Depends(get_rag_controller)):
    return await controller.ask_question(chatrequest)