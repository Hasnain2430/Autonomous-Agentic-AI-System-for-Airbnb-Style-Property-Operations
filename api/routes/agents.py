"""
Agent endpoints.

These endpoints will be used by n8n to call agent functions.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from database.db import get_db
from agents.inquiry_booking_agent import InquiryBookingAgent  # Deprecated, kept for backward compatibility
from agents.inquiry_agent import InquiryAgent
from agents.booking_agent import BookingAgent
from api.utils.agent_router import determine_agent, update_agent_context
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
        # Determine which agent to use
        agent_type = determine_agent(
            db=db,
            guest_telegram_id=request.guest_telegram_id,
            property_id=request.property_id,
            message=request.message,
            conversation_history=request.conversation_history
        )
        
        # Initialize appropriate agent
        if agent_type == "booking":
            agent = BookingAgent()
            result = agent.handle_booking(
                db=db,
                message=request.message,
                property_id=request.property_id,
                guest_telegram_id=request.guest_telegram_id,
                conversation_history=request.conversation_history
            )
            update_agent_context(
                db=db,
                guest_telegram_id=request.guest_telegram_id,
                property_id=request.property_id,
                agent_name="booking",
                booking_intent=True
            )
        else:
            agent = InquiryAgent()
            result = agent.handle_inquiry(
                db=db,
                message=request.message,
                property_id=request.property_id,
                guest_telegram_id=request.guest_telegram_id,
                conversation_history=request.conversation_history
            )
            if result.get("action") == "transition_to_booking":
                update_agent_context(
                    db=db,
                    guest_telegram_id=request.guest_telegram_id,
                    property_id=request.property_id,
                    agent_name="booking",
                    booking_intent=True
                )
            else:
                update_agent_context(
                    db=db,
                    guest_telegram_id=request.guest_telegram_id,
                    property_id=request.property_id,
                    agent_name="inquiry",
                    booking_intent=False
                )
        
        # Log incoming request
        log_event(
            db=db,
            event_type=EventType.AGENT_DECISION,
            agent_name=agent.agent_name,
            message=f"Processing inquiry from guest {request.guest_telegram_id}",
            metadata={
                "guest_telegram_id": request.guest_telegram_id,
                "property_id": request.property_id,
                "message": request.message[:100],  # First 100 chars
                "agent_type": agent_type
            }
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
                agent_name="AgentRouter",
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
async def generate_weekly_report(
    host_id: Optional[int] = Query(None, description="Host ID (optional, sends to all if not provided)"),
    week_start_date: Optional[str] = Query(None, description="Week start date (YYYY-MM-DD, defaults to last Monday)"),
    db: Session = Depends(get_db)
):
    """
    Generate and send weekly summary report to host(s).
    
    Args:
        host_id: Optional host ID (if not provided, sends to all hosts)
        week_start_date: Optional week start date (YYYY-MM-DD, defaults to last Monday)
        db: Database session
    
    Returns:
        Success message with report details
    """
    from datetime import date
    from api.utils.weekly_reports import (
        generate_weekly_report,
        format_report_message,
        send_weekly_report_to_host,
        send_weekly_reports_to_all_hosts
    )
    
    week_start = None
    if week_start_date:
        try:
            week_start = datetime.strptime(week_start_date, "%Y-%m-%d").date()
        except ValueError:
            return {"error": "Invalid date format. Use YYYY-MM-DD"}
    
    if host_id:
        # Send to specific host
        report = generate_weekly_report(db, host_id, week_start)
        if "error" in report:
            return {"error": report["error"]}
        
        success = await send_weekly_report_to_host(db, host_id, week_start)
        if success:
            return {
                "status": "success",
                "message": f"Weekly report sent to host {host_id}",
                "report": {
                    "week_start": report["week_start"],
                    "week_end": report["week_end"],
                    "total_bookings": report["summary"]["total_bookings"],
                    "total_revenue": report["summary"]["total_revenue"]
                }
            }
        else:
            return {"error": "Failed to send report to host"}
    else:
        # Send to all hosts
        results = await send_weekly_reports_to_all_hosts(db, week_start)
        return {
            "status": "success",
            "message": f"Weekly reports sent to {results['successful']} hosts",
            "results": results
        }


@router.post("/agents/host-summary/monthly")
async def generate_monthly_report():
    """
    Generate monthly summary report.
    
    This endpoint will be implemented when we create the Host Summary Agent.
    """
    return {"message": "Agent not yet implemented", "status": "placeholder"}

