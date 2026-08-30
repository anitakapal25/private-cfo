import threading
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.config import SessionLocal
from app.models.investment_platform import InvestmentPlatformConnection
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

def sync_all_investment_connections():
    """
    Background task to sync all active investment platform connections.
    In a real implementation, this would fetch data from each platform and update the user's financial data.
    For MVP, we simulate a successful sync by updating the timestamp and status.
    """
    db: Session = SessionLocal()
    try:
        # Query all active connections
        connections = db.query(InvestmentPlatformConnection).filter(
            InvestmentPlatformConnection.is_active == True
        ).all()

        logger.info(f"Starting background sync for {len(connections)} investment platform connections")

        for connection in connections:
            try:
                # Simulate sync process
                # In a real implementation, we would:
                # 1. Decrypt credentials
                # 2. Call the platform's API to fetch holdings/transactions
                # 3. Update the user's financial data (assets, etc.)
                # 4. Handle errors appropriately

                # For MVP, we just update the sync timestamp and status
                connection.last_synced_at = datetime.utcnow()
                connection.sync_status = "success"
                connection.last_error_message = None

                logger.info(f"Synced connection {connection.connection_id} for platform {connection.platform_name}")
            except Exception as e:
                logger.error(f"Error syncing connection {connection.connection_id}: {str(e)}")
                connection.last_synced_at = datetime.utcnow()
                connection.sync_status = "failed"
                connection.last_error_message = str(e)

        db.commit()
        logger.info("Background sync completed")
    except Exception as e:
        logger.error(f"Error in background sync task: {str(e)}")
        db.rollback()
    finally:
        db.close()

def start_background_sync(interval_seconds: int = 3600) -> Tuple[threading.Thread, threading.Event]:
    """
    Start a background thread that runs the sync task at the specified interval.
    :param interval_seconds: Interval between sync runs in seconds (default: 1 hour)
    """
    stop_event = threading.Event()

    def run_periodically():
        while not stop_event.is_set():
            sync_all_investment_connections()
            stop_event.wait(interval_seconds)

    thread = threading.Thread(target=run_periodically, daemon=True)
    thread.start()
    logger.info(f"Background sync thread started with interval {interval_seconds} seconds")
    return thread, stop_event
