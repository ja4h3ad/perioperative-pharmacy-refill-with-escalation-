class RefillRequest(BaseModel):
    user_message: str
    pa_id: str
    session_id: str | None = None