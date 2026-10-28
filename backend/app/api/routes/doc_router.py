from fastapi import APIRouter, Request
from fastapi import Depends, UploadFile, File, Header
from app.helpers.auth import require_mentor
from app.schemas.tflrag_schemas import  RepositoryRequest
from app.api.controllers.doc_controller import DocController
from app.repositories.vector_store import TFLKnowledgeCore
from app.services.doc_service import DocService

router = APIRouter(prefix="", tags=["TFLRAG"])
    
def get_doc_controller()->DocController:
    repository=TFLKnowledgeCore()
    service=DocService(repository)
    return DocController(service)

@router.get("/documents")
async def list_documents(controller:DocController=Depends(get_doc_controller)):
    return await controller.list_documents()

@router.post("/documents/upload")
async def upload_document(file: UploadFile = File(...), _mentor: dict = Depends(require_mentor),controller:DocController=Depends(get_doc_controller)):
    return await controller.upload_document(file,_mentor)


@router.post("/repositories/import")
async def import_github_repository(reporequest: RepositoryRequest, _mentor: dict = Depends(require_mentor),controller:DocController=Depends(get_doc_controller)):
    return await controller.import_github_repository(reporequest,_mentor)

@router.post("/repositories/upload-zip")
async def upload_repository_zip(file: UploadFile = File(...), _mentor: dict = Depends(require_mentor),controller:DocController=Depends(get_doc_controller)):
    return await controller.upload_repository_zip(file,_mentor)

@router.delete("/documents/{document_id}")
async def delete_document(document_id: str, _mentor: dict = Depends(require_mentor),controller:DocController=Depends(get_doc_controller)):
    return await controller.delete_document(document_id,_mentor)