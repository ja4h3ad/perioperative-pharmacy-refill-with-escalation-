# app/main.py
'''future main app file with notional references to files that don't exist LOL '''

# app/main.py
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import uuid
import logging

from app.state_machine import process_refill_request
from app.agents.ehr_agent import EHRAgent
from app.observability.tracing import init_telemetry
from app.pydantic_requests import refill_request as RefillRequest
from app.pydantic_responses import refill_response as RefillResponse

app = FastAPI(title="Perioperative Refill Agent")

# Initialize OpenTelemetry
init_telemetry()

#initalize logger
logger = logging.getLogger(__name__)





@app.post("/api/v1/refill", response_model=RefillResponse)
async def process_refill(request: RefillRequest, background_tasks: BackgroundTasks):
    """Process refill request asynchronously"""
    conversation_id = request.session_id or str(uuid.uuid4())

    try:
        # Process through state machine
        result = await process_refill_request(conversation_id, request.user_message)

        # Schedule async notification (non-blocking)
        if result.get('current_step') == 'dispensed':
            background_tasks.add_task(
                send_notification,
                request.pa_id,
                result
            )

        return RefillResponse(
            conversation_id=conversation_id,
            status=result['current_step'],
            message=_format_user_message(result),
            order_id=result.get('order_id'),
            escalation_id=result.get('escalation_context', {}).get('escalation_id')
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/refill/{conversation_id}/stream")
async def stream_refill_processing(conversation_id: str):
    """Server-sent events for real-time updates"""

    async def event_generator():
        # Simulate streaming state updates
        async for state in process_refill_with_streaming(conversation_id):
            yield f"data: {state}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/health")
async def health_check():
    """Async health check with dependency checks"""
    async with EHRAgent() as ehr_agent:
        try:
            # Quick EHR connectivity check
            await asyncio.wait_for(
                ehr_agent.fetch_patient_data("TEST-001"),
                timeout=1.0
            )
            ehr_status = "healthy"
        except:
            ehr_status = "degraded"

    return {
        "status": "ok",
        "dependencies": {
            "ehr": ehr_status
        }
    }


async def send_notification(pa_id: str, result: dict):
    """Background task for notifications"""
    await asyncio.sleep(0.1)  # Simulate SMS/email API
    logger.info(f"Notification sent to PA {pa_id}: {result['current_step']}")


def _format_user_message(result: dict) -> str:
    """Format response message for user"""
    if result['current_step'] == 'dispensed':
        return f"✅ Refill processed. Order ID: {result.get('order_id')}"
    elif result['current_step'] == 'escalated':
        return f"⚠️  Requires physician approval. Escalation ID: {result['escalation_context']['escalation_id']}"
    else:
        return "Processing your request..."


async def process_refill_with_streaming(conversation_id: str):
    """Yield state updates for SSE streaming"""
    # Stub for streaming implementation
    yield '{"step": "intent_classified"}'
    await asyncio.sleep(0.5)
    yield '{"step": "safety_checked"}'


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)