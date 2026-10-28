from fastapi import Header
from app.services.doc_service import DocService
from fastapi import Depends, UploadFile, File, Header
from app.helpers.auth import require_mentor
from app.schemas.tflrag_schemas import RepositoryRequest

class DocController:
    def __init__(self,service:DocService):
        self.service=service
        
    async def list_documents(self):
        return await self.service.list_documents()

    async def upload_document(self,file: UploadFile = File(...), _mentor: dict = Depends(require_mentor)):
        return await self.service.upload_document(file,_mentor)

    async def import_github_repository(self,reporequest: RepositoryRequest, _mentor: dict = Depends(require_mentor)):
        return await self.service.import_github_repository(reporequest,_mentor)

    async def upload_repository_zip(self,file: UploadFile = File(...), _mentor: dict = Depends(require_mentor)):
        return await self.service.upload_repository_zip(file,_mentor)

    async def delete_document(self,document_id: str, _mentor: dict = Depends(require_mentor)):
        return await self.service.delete_document(document_id,_mentor)