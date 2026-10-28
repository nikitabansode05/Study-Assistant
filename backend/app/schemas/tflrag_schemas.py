from pydantic import BaseModel, Field, HttpUrl

class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    history: list[dict[str, str]] = Field(default_factory=list, max_length=12)

class RepositoryRequest(BaseModel):
    url: str = Field(min_length=8, max_length=500)

class Source(BaseModel):
    document: str
    page: int | None = None
    chunk_id: str
    excerpt: str

class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]

class LoginRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=200)

class LoginResponse(BaseModel):
    role: str
    user_id: str
    token: str
    expires_at: float

class ChatRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=4000,
    )
    history: list[dict[str, str]] = Field(
        default_factory=list,
        max_length=12,
    )
    student_id: str | None = Field(
        default=None,
        max_length=100,
    )
