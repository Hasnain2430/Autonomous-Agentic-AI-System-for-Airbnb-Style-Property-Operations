"""
Agent endpoints.

These endpoints will be used by n8n to call agent functions.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from database.db import get_db
from agents.inquiry_booking_agent import InquiryBookingAgent
from api.utils.logging import log_event, EventType

router = APIRouter()


# Request/Response models
class AgentProcessRequest(BaseModel):
    """Request model for agent processing."""
    message: str
    guest_telegram_id: str
    property_id: int
    booking_id: Optional[int] = None
    conversation_history: Optional[List[Dict[str, str]]] = None
    context: Optional[Dict[str, Any]] = None


class AgentResponse(BaseModel):
    """Response model from agents."""
    response: str
    action: str  # e.g., 'reply', 'request_payment', 'escalate', etc.
    metadata: Optional[Dict[str, Any]] = None


@router.post("/agents/inquiry-booking/process", response_model=AgentResponse)
async def process_inquiry_booking(
    request: AgentProcessRequest,
    db: Session = Depends(get_db)
):
    """
    Process guest inquiry or booking request.
    
    This endpoint processes messages from guests and returns agent responses.
    """
    try:
        # Initialize agent
        agent = InquiryBookingAgent()
        
        # Log incoming request
        log_event(
            db=db,
            event_type=EventType.AGENT_DECISION,
            agent_name=agent.agent_name,
            message=f"Processing inquiry from guest {request.guest_telegram_id}",
            metadata={
                "guest_telegram_id": request.guest_telegram_id,
                "property_id": request.property_id,
                "message": request.message[:100]  # First 100 chars
            }
        )
        
        # Process message with agent
        result = agent.handle_inquiry(
            db=db,
            message=request.message,
            property_id=request.property_id,
            guest_telegram_id=request.guest_telegram_id,
            conversation_history=request.conversation_history
        )
        
        # Log agent response
        log_event(
            db=db,
            event_type=EventType.AGENT_RESPONSE,
            agent_name=agent.agent_name,
            message=f"Agent response generated",
            metadata={
                "action": result.get("action"),
                "property_id": request.property_id
            }
        )
        
        return AgentResponse(
            response=result.get("response", "I'm sorry, I couldn't process that."),
            action=result.get("action", "reply"),
            metadata=result.get("metadata", {})
        )
    
    except Exception as e:
        # Log error
        try:
            log_event(
                db=db,
                event_type=EventType.AGENT_ERROR,
                agent_name="InquiryBookingAgent",
                message=f"Error processing inquiry: {str(e)}",
                metadata={"error": str(e)}
            )
        except:
            pass  # Don't fail if logging fails
        
        raise HTTPException(
            status_code=500,
            detail=f"Error processing inquiry: {str(e)}"
        )


@router.post("/agents/issue-handling/process", response_model=AgentResponse)
async def process_issue(request: AgentProcessRequest):
    """
    Process guest issue during stay.
    
    This endpoint will be implemented when we create the Issue Handling Agent.
    """
    # Placeholder implementation
    return AgentResponse(
        response="Agent not yet implemented",
        action="reply",
        metadata={"status": "placeholder"}
    )


@router.post("/agents/cleaner-coordination/schedule")
async def schedule_cleaning():
    """
    Schedule cleaning task.
    
    This endpoint will be implemented when we create the Cleaner Coordination Agent.
    """
    return {"message": "Agent not yet implemented", "status": "placeholder"}


@router.post("/agents/cleaner-coordination/handle-request")
async def handle_cleaning_request():
    """
    Handle cleaning request during stay.
    
    This endpoint will be implemented when we create the Cleaner Coordination Agent.
    """
    return {"message": "Agent not yet implemented", "status": "placeholder"}


@router.post("/agents/host-summary/weekly")
async def generate_weekly_report():
    """
    Generate weekly summary report.
    
    This endpoint will be implemented when we create the Host Summary Agent.
    """
    return {"message": "Agent not yet implemented", "status": "placeholder"}


@router.post("/agents/host-summary/monthly")
async def generate_monthly_report():
    """
    Generate monthly summary report.
    
    This endpoint will be implemented when we create the Host Summary Agent.
    """
    return {"message": "Agent not yet implemented", "status": "placeholder"}

