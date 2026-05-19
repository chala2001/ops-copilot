
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import with error handling
try:
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.interval import IntervalTrigger
except ImportError as e:
    logger.error(f"APScheduler not installed: {e}")
    print("❌ APScheduler not installed. Run: pip install apscheduler")
    sys.exit(1)

try:
    from core.ingest import run_ingestion
except ImportError as e:
    logger.error(f"Cannot import ingest module: {e}")
    print("❌ ingest.py not found or has errors")
    sys.exit(1)

def scheduled_ingest():
    '''Function called on each scheduled run with error handling.'''
    try:
        print(f'\n[Scheduler] Running ingestion at {datetime.now().strftime("%H:%M:%S")}')
        logger.info("Starting scheduled ingestion")
        
        run_ingestion()
        
        logger.info("Scheduled ingestion completed successfully")
        print('[Scheduler] Ingestion completed successfully')
    
    except KeyboardInterrupt:
        logger.info("Scheduler interrupted by user")
        raise  # Re-raise to stop scheduler
    
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        print(f'[Scheduler] ERROR: {e}')
        # Don't raise - continue scheduling

def main():
    '''Main scheduler function with complete error handling.'''
    try:
        # Create scheduler
        try:
            scheduler = BlockingScheduler()
            logger.info("Scheduler created")
        except Exception as e:
            logger.error(f"Failed to create scheduler: {e}")
            print(f"❌ Cannot create scheduler: {e}")
            sys.exit(1)

        # Schedule job
        try:
            scheduler.add_job(
                scheduled_ingest,
                trigger=IntervalTrigger(minutes=30),
                id='ingestion_job',
                name='Document ingestion',
                replace_existing=True
            )
            logger.info("Ingestion job scheduled (every 30 minutes)")
        except Exception as e:
            logger.error(f"Failed to schedule job: {e}")
            print(f"❌ Cannot schedule job: {e}")
            sys.exit(1)

        print('Scheduler started. Ingestion runs every 30 minutes.')
        print('Press Ctrl+C to stop.')
        logger.info("Scheduler started successfully")

        # Run once immediately on startup
        print('\n[Scheduler] Running initial ingestion...')
        try:
            scheduled_ingest()
        except Exception as e:
            logger.error(f"Initial ingestion failed: {e}")
            print(f"⚠️  Initial ingestion failed, but scheduler will continue: {e}")

        # Start scheduler
        try:
            scheduler.start()
        except KeyboardInterrupt:
            print('\n⚠️  Scheduler stopped by user.')
            logger.info("Scheduler stopped by user")
            try:
                scheduler.shutdown()
            except Exception:
                pass
            sys.exit(0)
        except Exception as e:
            logger.error(f"Scheduler execution error: {e}")
            print(f"❌ Scheduler error: {e}")
            try:
                scheduler.shutdown()
            except Exception:
                pass
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"Fatal error in scheduler main: {e}")
        print(f"❌ Fatal scheduler error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n⚠️  Scheduler interrupted')
        sys.exit(0)
    except Exception as e:
        logger.error(f"Scheduler crashed: {e}")
        print(f"❌ Scheduler crashed: {e}")
        sys.exit(1)