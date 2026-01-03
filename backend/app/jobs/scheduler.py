from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.jobs.daily_sync import daily_delta_sync
from app.jobs.fundamentals_updater import update_fundamentals_daily

scheduler = AsyncIOScheduler()

# ============================================
# SCHEDULED JOBS
# ============================================

@scheduler.scheduled_job('cron', hour=21, minute=0, timezone='America/New_York')
def scheduled_daily_sync():
    """
    Runs at 9:00 PM ET every night
    Updates OHLCV data (delta sync)
    """
    print("⏰ Triggering daily delta sync...")
    daily_delta_sync()


@scheduler.scheduled_job('cron', hour=22, minute=0, timezone='America/New_York')
def scheduled_fundamentals_update():
    """
    Runs at 10:00 PM ET every night
    Updates 1/7th of fundamentals
    """
    print("⏰ Triggering fundamentals update...")
    update_fundamentals_daily()


def start_scheduler():
    """Start the APScheduler"""
    scheduler.start()
    print("✓ Scheduler initialized")
    print("   Daily delta sync: 9:00 PM ET")
    print("   Fundamentals update: 10:00 PM ET (1/7th daily)")
