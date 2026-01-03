from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.jobs.bulk_population import populate_all_stocks, retry_failed_tickers
from app.jobs.daily_sync import daily_delta_sync
from app.jobs.fundamentals_updater import update_fundamentals_daily, update_single_ticker_fundamentals
from typing import Dict, Any

router = APIRouter(prefix="/admin", tags=["admin"])

# ============================================
# ADMIN ENDPOINTS FOR MANUAL JOB TRIGGERS
# ============================================

@router.post("/populate-all-stocks")
async def trigger_bulk_population(background_tasks: BackgroundTasks, resume: bool = True) -> Dict[str, str]:
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
async def trigger_retry_failed(background_tasks: BackgroundTasks) -> Dict[str, str]:
    """Retry tickers that failed during bulk population"""
    background_tasks.add_task(retry_failed_tickers)
    
    return {
        "status": "started",
        "message": "Retry job started. Check logs for progress."
    }


@router.post("/daily-sync")
async def trigger_daily_sync(background_tasks: BackgroundTasks) -> Dict[str, str]:
    """Manually trigger daily delta sync"""
    background_tasks.add_task(daily_delta_sync)
    
    return {
        "status": "started",
        "message": "Daily delta sync started"
    }


@router.post("/update-fundamentals")
async def trigger_fundamentals_update(background_tasks: BackgroundTasks) -> Dict[str, str]:
    """Manually trigger fundamentals update (today's 1/7th segment)"""
    background_tasks.add_task(update_fundamentals_daily)
    
    return {
        "status": "started",
        "message": "Fundamentals update started for today's segment"
    }


@router.post("/update-fundamentals/{ticker}")
async def trigger_single_fundamentals_update(ticker: str) -> Dict[str, Any]:
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
