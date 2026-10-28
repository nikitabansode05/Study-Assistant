from fastapi import APIRouter, Request
from app.api.controllers.auth_controller import AuthController
from app.services.auth_service import AuthService
from app.repositories.vector_store import TFLKnowledgeCore
from fastapi import Depends, UploadFile, File, Header
from app.helpers.auth import require_mentor
from app.schemas.tflrag_schemas import ChatRequest, LoginRequest, LoginResponse, RepositoryRequest

router = APIRouter(prefix="", tags=["TFLRAG"])

def get_auth_controller(request:Request) -> AuthController:
    repository = TFLKnowledgeCore()
    service = AuthService(repository)
    return AuthController(service)
# ----------------------------------------------------------------------------- auth
@router.post("/auth/login", response_model=LoginResponse)
async def mentor_login(loginrequest: LoginRequest,controller:AuthController=Depends(get_auth_controller)):
    return await controller.mentor_login(loginrequest)

@router.post("/auth/logout")
async def mentor_logout(authorization: str | None = Header(default=None),controller:AuthController=Depends(get_auth_controller)):
    return await controller.mentor_logout(authorization)

@router.get("/auth/me")
async def current_role(authorization: str | None = Header(default=None),controller:AuthController=Depends(get_auth_controller)):
    return await controller.current_role(authorization)

@router.get("/health")
async def health(controller:AuthController=Depends(get_auth_controller)):
    return await controller.health()
   