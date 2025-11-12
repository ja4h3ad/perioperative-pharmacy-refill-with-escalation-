class RefillResponse(BaseModel):
    conversation_id: str
    status: str
    message: str
    order_id: str | None = None
    escalation_id: str | None = None

