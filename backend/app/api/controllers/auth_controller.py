from fastapi import Header
from app.schemas.tflrag_schemas import LoginRequest
from app.services.auth_service import AuthService

class AuthController:

    def __init__(self, service:AuthService):
        self.service = service
            
    async def mentor_login(self,loginrequest: LoginRequest):
        return await self.service.mentor_login(loginrequest)

    async def mentor_logout(self,authorization: str | None = Header(default=None)):
        return await self.service.mentor_logout(authorization)

    async def current_role(self,authorization: str | None = Header(default=None)):
        return await self.service.current_role(authorization)

    async def health(self):
        return await self.service.health()
    