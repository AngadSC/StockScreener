from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.jobs.bulk_population import populate_all_stocks, retry_failed_tickers
from app.jobs.daily_sync import daily_delta_sync
from app.jobs.fundamentals_updater import update_fundamentals_daily, update_single_ticker_fundamentals
from app.jobs.stock_loader import update_all_stocks_batch
from app.database.connection import get_db
from app.database.models import User
from app.services.auth import get_current_admin_user
from app.services import email as email_service
from typing import Dict, Any, Optional

router = APIRouter(prefix="/admin", tags=["admin"])

# ============================================
# ADMIN ENDPOINTS FOR MANUAL JOB TRIGGERS
# ============================================

@router.post("/populate-all-stocks")
async def trigger_bulk_population(
    background_tasks: BackgroundTasks,
    resume: bool = True,
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, str]:
    """
    Trigger bulk population of all US stocks (5 years history)
    
    This is a LONG-RUNNING job (2-3 hours)
    Runs in background
    
    Args:
        resume: Resume from last checkpoint if True
    """
    background_tasks.add_task(populate_all_stocks, resume=resume)
    
    return {
        "status": "started",
        "message": f"Bulk population job started (resume={resume}). This will take 2-3 hours. Monitor logs for progress.",
        "estimated_duration": "2-3 hours"
    }


@router.post("/retry-failed-tickers")
async def trigger_retry_failed(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, str]:
    """Retry tickers that failed during bulk population"""
    background_tasks.add_task(retry_failed_tickers)
    
    return {
        "status": "started",
        "message": "Retry job started. Check logs for progress."
    }


@router.post("/daily-sync")
async def trigger_daily_sync(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, str]:
    """Manually trigger daily delta sync"""
    background_tasks.add_task(daily_delta_sync)
    
    return {
        "status": "started",
        "message": "Daily delta sync started"
    }


@router.post("/update-fundamentals")
async def trigger_fundamentals_update(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, str]:
    """Manually trigger fundamentals update (today's 1/7th segment)"""
    background_tasks.add_task(update_fundamentals_daily)
    
    return {
        "status": "started",
        "message": "Fundamentals update started for today's segment"
    }


@router.post("/update-fundamentals/{ticker}")
async def trigger_single_fundamentals_update(
    ticker: str,
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """Update fundamentals for a single ticker (on-demand)"""
    success = update_single_ticker_fundamentals(ticker)

    if success:
        return {
            "status": "success",
            "ticker": ticker.upper(),
            "message": f"Fundamentals updated for {ticker.upper()}"
        }
    else:
        raise HTTPException(status_code=404, detail=f"Failed to update {ticker}")


@router.post("/batch-update")
async def trigger_batch_update(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, str]:
    """
    Manually trigger batch update of all active stocks

    This updates:
    - Fundamentals using YahooQuery (50 tickers per API call)
    - Historical prices using YFinance (100 tickers per API call)

    Note: This is the same job that runs nightly at 9 PM ET,
    but can be triggered manually by admin at any time.
    """
    background_tasks.add_task(update_all_stocks_batch, manual_trigger=True)

    return {
        "status": "started",
        "message": "Batch update job started. Check logs for progress.",
        "details": {
            "fundamentals_provider": "yahooquery",
            "fundamentals_batch_size": 50,
            "prices_provider": "yfinance",
            "prices_batch_size": 100
        }
    }


# ============================================
# EMAIL DELIVERABILITY TEST
# ============================================

class EmailTestRequest(BaseModel):
    to: Optional[EmailStr] = None       # defaults to the admin's own address
    category: Optional[str] = "product_updates"


@router.post("/email/test")
def send_test_email(
    body: Optional[EmailTestRequest] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Send a sample email using the base template to verify deliverability
    end-to-end (Resend + domain SPF/DKIM). Bypasses per-category preference
    gating but still respects EMAIL_ENABLED. Sends to `to` or, by default, the
    requesting admin's own email address.
    """
    payload = body or EmailTestRequest()
    result = email_service.send_test_email(
        db,
        current_user,
        to_email=payload.to,
        category=payload.category or "product_updates",
    )
    return {
        "recipient": payload.to or current_user.email,
        "result": result,
    }
