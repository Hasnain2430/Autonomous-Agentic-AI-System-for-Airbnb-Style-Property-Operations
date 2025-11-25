"""
Weekly report generation for hosts.

Generates weekly reports with booking statistics, payment information, and guest counts.
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta, date
from database.models import Host, Property, Booking
from api.utils.logging import log_event, EventType


def generate_weekly_report(
    db: Session,
    host_id: int,
    week_start_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    Generate weekly report for a host.
    
    Args:
        db: Database session
        host_id: Host ID
        week_start_date: Start date of the week (defaults to last Monday)
    
    Returns:
        Dictionary with report data
    """
    # Default to last Monday if not provided
    if week_start_date is None:
        today = date.today()
        days_since_monday = (today.weekday()) % 7
        week_start_date = today - timedelta(days=days_since_monday + 7)  # Last Monday
    
    week_end_date = week_start_date + timedelta(days=6)  # Sunday
    
    # Get host
    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        return {"error": "Host not found"}
    
    # Get all properties for this host
    properties = db.query(Property).filter(Property.host_id == host_id).all()
    if not properties:
        return {"error": "No properties found for host"}
    
    property_ids = [p.id for p in properties]
    
    # Get bookings for the week
    bookings = db.query(Booking).filter(
        Booking.property_id.in_(property_ids),
        # Bookings that overlap with the week
        or_(
            and_(
                Booking.check_in_date <= week_end_date,
                Booking.check_out_date >= week_start_date
            ),
            # Or bookings created during the week
            and_(
                func.date(Booking.created_at) >= week_start_date,
                func.date(Booking.created_at) <= week_end_date
            )
        )
    ).all()
    
    # Calculate statistics
    total_bookings = len(bookings)
    confirmed_bookings = [b for b in bookings if b.booking_status == 'confirmed']
    pending_bookings = [b for b in bookings if b.booking_status == 'pending']
    cancelled_bookings = [b for b in bookings if b.booking_status == 'cancelled']
    
    # Payment statistics
    approved_payments = [b for b in confirmed_bookings if b.payment_status == 'approved']
    pending_payments = [b for b in bookings if b.payment_status == 'pending']
    rejected_payments = [b for b in bookings if b.payment_status == 'rejected']
    
    # Calculate revenue
    total_revenue = sum(
        (b.final_price or b.requested_price or 0) 
        for b in approved_payments
    )
    
    # Guest statistics
    total_guests = sum(b.number_of_guests for b in confirmed_bookings)
    total_nights = sum(b.number_of_nights for b in confirmed_bookings)
    
    # Property-wise breakdown
    property_stats = {}
    for prop in properties:
        prop_bookings = [b for b in bookings if b.property_id == prop.id]
        prop_confirmed = [b for b in prop_bookings if b.booking_status == 'confirmed']
        prop_revenue = sum(
            (b.final_price or b.requested_price or 0) 
            for b in prop_confirmed if b.payment_status == 'approved'
        )
        prop_guests = sum(b.number_of_guests for b in prop_confirmed)
        prop_nights = sum(b.number_of_nights for b in prop_confirmed)
        
        property_stats[prop.id] = {
            "property_name": prop.name,
            "total_bookings": len(prop_bookings),
            "confirmed_bookings": len(prop_confirmed),
            "revenue": prop_revenue,
            "guests": prop_guests,
            "nights": prop_nights
        }
    
    # Format report
    report = {
        "host_id": host_id,
        "host_name": host.name,
        "week_start": week_start_date.strftime('%Y-%m-%d'),
        "week_end": week_end_date.strftime('%Y-%m-%d'),
        "summary": {
            "total_bookings": total_bookings,
            "confirmed_bookings": len(confirmed_bookings),
            "pending_bookings": len(pending_bookings),
            "cancelled_bookings": len(cancelled_bookings),
            "total_revenue": total_revenue,
            "total_guests": total_guests,
            "total_nights": total_nights,
            "approved_payments": len(approved_payments),
            "pending_payments": len(pending_payments),
            "rejected_payments": len(rejected_payments)
        },
        "properties": property_stats,
        "bookings": [
            {
                "id": b.id,
                "property_name": b.property.name,
                "guest_name": b.guest_name or b.customer_name or f"Guest {b.guest_telegram_id}",
                "check_in": b.check_in_date.strftime('%Y-%m-%d'),
                "check_out": b.check_out_date.strftime('%Y-%m-%d'),
                "nights": b.number_of_nights,
                "guests": b.number_of_guests,
                "status": b.booking_status,
                "payment_status": b.payment_status,
                "amount": b.final_price or b.requested_price or 0
            }
            for b in bookings
        ]
    }
    
    return report


def format_report_message(report: Dict[str, Any]) -> str:
    """
    Format report data as a readable Telegram message.
    
    Args:
        report: Report dictionary from generate_weekly_report
    
    Returns:
        Formatted message string
    """
    if "error" in report:
        return f"❌ Error: {report['error']}"
    
    week_start = datetime.strptime(report["week_start"], "%Y-%m-%d").strftime("%B %d, %Y")
    week_end = datetime.strptime(report["week_end"], "%Y-%m-%d").strftime("%B %d, %Y")
    
    summary = report["summary"]
    
    message = f"📊 **Weekly Report**\n\n"
    message += f"**Period:** {week_start} - {week_end}\n"
    message += f"**Host:** {report['host_name']}\n\n"
    
    message += f"📈 **Summary:**\n"
    message += f"• Total Bookings: {summary['total_bookings']}\n"
    message += f"  ✓ Confirmed: {summary['confirmed_bookings']}\n"
    message += f"  ⏳ Pending: {summary['pending_bookings']}\n"
    message += f"  ❌ Cancelled: {summary['cancelled_bookings']}\n\n"
    
    message += f"💰 **Revenue:**\n"
    message += f"• Total Revenue: PKR {summary['total_revenue']:,.2f}\n"
    message += f"• Approved Payments: {summary['approved_payments']}\n"
    message += f"• Pending Payments: {summary['pending_payments']}\n"
    message += f"• Rejected Payments: {summary['rejected_payments']}\n\n"
    
    message += f"👥 **Guests:**\n"
    message += f"• Total Guests: {summary['total_guests']}\n"
    message += f"• Total Nights: {summary['total_nights']}\n\n"
    
    # Property-wise breakdown
    if report["properties"]:
        message += f"🏠 **By Property:**\n"
        for prop_id, stats in report["properties"].items():
            message += f"\n**{stats['property_name']}:**\n"
            message += f"• Bookings: {stats['total_bookings']} ({stats['confirmed_bookings']} confirmed)\n"
            message += f"• Revenue: PKR {stats['revenue']:,.2f}\n"
            message += f"• Guests: {stats['guests']}\n"
            message += f"• Nights: {stats['nights']}\n"
    
    # Recent bookings
    if report["bookings"]:
        message += f"\n📋 **Recent Bookings:**\n"
        for booking in report["bookings"][:10]:  # Show last 10
            status_emoji = "✅" if booking["status"] == "confirmed" else "⏳" if booking["status"] == "pending" else "❌"
            message += f"{status_emoji} {booking['guest_name']} - {booking['property_name']}\n"
            message += f"   {booking['check_in']} to {booking['check_out']} ({booking['nights']} nights, {booking['guests']} guests)\n"
            message += f"   Amount: PKR {booking['amount']:,.2f} ({booking['payment_status']})\n\n"
    
    return message


async def send_weekly_report_to_host(
    db: Session,
    host_id: int,
    week_start_date: Optional[date] = None
) -> bool:
    """
    Generate and send weekly report to host via Telegram.
    
    Args:
        db: Database session
        host_id: Host ID
        week_start_date: Start date of the week (defaults to last Monday)
    
    Returns:
        True if sent successfully
    """
    try:
        # Generate report
        report = generate_weekly_report(db, host_id, week_start_date)
        
        if "error" in report:
            print(f"Error generating report: {report['error']}")
            return False
        
        # Format message
        message = format_report_message(report)
        
        # Get host
        host = db.query(Host).filter(Host.id == host_id).first()
        if not host or not host.telegram_id:
            print(f"Host {host_id} not found or has no Telegram ID")
            return False
        
        # Send to host
        from api.telegram.base import get_bot_token, send_message
        bot_token = get_bot_token("host")
        if not bot_token:
            print("Host bot token not found")
            return False
        
        success = await send_message(
            bot_token=bot_token,
            chat_id=host.telegram_id,
            message=message
        )
        
        if success:
            # Log event
            log_event(
                db=db,
                event_type=EventType.HOST_ESCALATION_RECEIVED,  # Using existing event type
                agent_name="WeeklyReport",
                property_id=None,
                message=f"Weekly report sent to host {host_id}",
                metadata={
                    "host_id": host_id,
                    "week_start": report["week_start"],
                    "week_end": report["week_end"],
                    "total_bookings": report["summary"]["total_bookings"],
                    "total_revenue": report["summary"]["total_revenue"]
                }
            )
        
        return success
        
    except Exception as e:
        print(f"Error sending weekly report: {e}")
        import traceback
        traceback.print_exc()
        return False


async def send_weekly_reports_to_all_hosts(db: Session, week_start_date: Optional[date] = None) -> Dict[str, Any]:
    """
    Send weekly reports to all hosts.
    
    Args:
        db: Database session
        week_start_date: Start date of the week (defaults to last Monday)
    
    Returns:
        Dictionary with results
    """
    hosts = db.query(Host).all()
    results = {
        "total_hosts": len(hosts),
        "successful": 0,
        "failed": 0,
        "errors": []
    }
    
    for host in hosts:
        if host.telegram_id:  # Only send to hosts with Telegram IDs
            success = await send_weekly_report_to_host(db, host.id, week_start_date)
            if success:
                results["successful"] += 1
            else:
                results["failed"] += 1
                results["errors"].append(f"Host {host.id} ({host.name})")
    
    return results

