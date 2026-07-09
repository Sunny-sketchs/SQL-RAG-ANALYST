from pydantic import BaseModel, field_validator


class AskRequest(BaseModel):
    query: str
    user_id: str = "anonymous"

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("query cannot be empty")
        if len(v) > 2000:
            raise ValueError("query too long (max 2000 characters)")
        return v


class AskResponse(BaseModel):
    answer: str
    route: str
    sources: list[dict] = []
    tokens_used: int = 0