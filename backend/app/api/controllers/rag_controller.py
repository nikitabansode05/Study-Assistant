from app.services.rag_service import RagService
from app.schemas.tflrag_schemas import ChatRequest

class RagController:
    def __init__(self, service:RagService):
        self.service=service
    
    async def ask_question(self,chatrequest: ChatRequest):
        return await self.service.ask_question(chatrequest)