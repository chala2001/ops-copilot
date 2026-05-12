# scheduler.py
# ── Automatic scheduled ingestion ───────────────────────
# Run as: python scheduler.py
# Keep running in background to auto-ingest every 30 minutes

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from ingest import run_ingestion

def scheduled_ingest():
    '''Function called on each scheduled run.'''
    print(f'\n[Scheduler] Running ingestion at {datetime.now().strftime("%H:%M:%S")}')
    try:
        run_ingestion()
        print('[Scheduler] Ingestion completed successfully')
    except Exception as e:
        print(f'[Scheduler] ERROR: {e}')

# Create the scheduler
scheduler = BlockingScheduler()

# Schedule: run every 30 minutes
# Change to minutes=5 for testing
scheduler.add_job(
    scheduled_ingest,
    trigger=IntervalTrigger(minutes=30),
    id='ingestion_job',
    name='Document ingestion',
    replace_existing=True
)

print('Scheduler started. Ingestion runs every 30 minutes.')
print('Press Ctrl+C to stop.')

# Run once immediately on startup
scheduled_ingest()

try:
    scheduler.start()
except KeyboardInterrupt:
    print('\nScheduler stopped.')
    scheduler.shutdown()