from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import requests
from app.core.config import get_db
from app.models.user import User
from app.models.webhook import WebhookSubscription, WebhookDelivery
from app.auth.manager import get_current_active_user
from pydantic import BaseModel
from datetime import datetime
import uuid
from uuid import UUID
import hashlib
import hmac
import ipaddress
import socket
import logging
from urllib.parse import urlparse

from app.core.config import get_settings
from app.core.crypto import decrypt_secret, encrypt_secret
from app.guardrails.data_redaction import redact_text

router = APIRouter(tags=["webhook"])
logger = logging.getLogger(__name__)

# Pydantic models for request/response
class WebhookSubscriptionBase(BaseModel):
    url: str
    events: List[str]  # List of event types to subscribe to
    headers: Optional[dict] = None

class WebhookSubscriptionCreate(WebhookSubscriptionBase):
    secret: Optional[str] = None

class WebhookSubscriptionUpdate(WebhookSubscriptionBase):
    secret: Optional[str] = None

class WebhookSubscriptionResponse(WebhookSubscriptionBase):
    subscription_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class WebhookDeliveryResponse(BaseModel):
    delivery_id: UUID
    event_type: str
    status_code: Optional[int]
    error_message: Optional[str]
    attempted_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


def validate_webhook_url(url: str) -> None:
    """Reject non-HTTPS and addresses that can reach private infrastructure."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(status_code=400, detail="Webhook URL must be a public HTTPS URL")
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise HTTPException(status_code=400, detail="Webhook hostname cannot be resolved") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise HTTPException(status_code=400, detail="Webhook URL resolves to a non-public address")


def ensure_webhooks_enabled() -> None:
    if not get_settings().enable_external_webhooks:
        raise HTTPException(status_code=503, detail="External webhooks are disabled")

def send_webhook_notification(subscription_id: str, event_type: str, payload: dict):
    """
    Background function to send webhook notification.
    """
    from app.core.config import SessionLocal
    db = SessionLocal()
    try:
        subscription = db.query(WebhookSubscription).filter(
            WebhookSubscription.subscription_id == subscription_id,
            WebhookSubscription.is_active == True
        ).first()

        if not subscription:
            return

        # Create delivery record
        delivery = WebhookDelivery(
            subscription_id=subscription_id,
            event_type=event_type,
            payload=json.dumps(payload)
        )
        db.add(delivery)
        db.commit()

        if not get_settings().enable_external_webhooks:
            return
        validate_webhook_url(subscription.url)

        # Prepare headers
        headers = {'Content-Type': 'application/json'}
        if subscription.headers:
            try:
                custom_headers = json.loads(subscription.headers)
                blocked_headers = {'host', 'content-length', 'x-arthaos-signature'}
                headers.update({
                    str(key): str(value)
                    for key, value in custom_headers.items()
                    if str(key).lower() not in blocked_headers
                })
            except:
                pass  # Use default headers if parsing fails

        # Add signature if secret is provided
        body = json.dumps(payload, separators=(',', ':'), sort_keys=True).encode()
        if subscription.secret:
            secret = decrypt_secret(subscription.secret).encode()
            signature = hmac.new(secret, body, hashlib.sha256).hexdigest()
            headers['X-ArthaOS-Signature'] = f"sha256={signature}"

        # Send the webhook
        try:
            response = requests.post(
                subscription.url,
                data=body,
                headers=headers,
                timeout=10,
                allow_redirects=False,
            )

            # Update delivery with result
            delivery.status_code = response.status_code
            delivery.completed_at = datetime.utcnow()

            if not response.ok:
                delivery.error_message = f"HTTP {response.status_code}: {response.text[:200]}"
        except Exception as e:
            delivery.error_message = redact_text(str(e))[:200]
            delivery.completed_at = datetime.utcnow()

        db.commit()
    except Exception as e:
        # Log the error but don't raise as this is a background task
        logger.error("Error sending webhook: %s", redact_text(str(e)))
    finally:
        db.close()

@router.post("/subscriptions", response_model=WebhookSubscriptionResponse)
async def create_webhook_subscription(
    subscription: WebhookSubscriptionCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new webhook subscription.
    """
    ensure_webhooks_enabled()
    validate_webhook_url(subscription.url)
    db_subscription = WebhookSubscription(
        user_id=current_user.user_id,
        url=subscription.url,
        events=json.dumps(subscription.events),
        secret=encrypt_secret(subscription.secret) if subscription.secret else None,
        headers=json.dumps(subscription.headers) if subscription.headers else None
    )
    db.add(db_subscription)
    db.commit()
    db.refresh(db_subscription)
    return db_subscription

@router.get("/subscriptions", response_model=List[WebhookSubscriptionResponse])
async def get_webhook_subscriptions(
    active_only: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all webhook subscriptions for the current user.
    """
    query = db.query(WebhookSubscription).filter(
        WebhookSubscription.user_id == current_user.user_id
    )
    if active_only:
        query = query.filter(WebhookSubscription.is_active == True)
    subscriptions = query.all()
    return subscriptions

@router.get("/subscriptions/{subscription_id}", response_model=WebhookSubscriptionResponse)
async def get_webhook_subscription(
    subscription_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific webhook subscription by ID.
    """
    subscription = db.query(WebhookSubscription).filter(
        WebhookSubscription.subscription_id == subscription_id,
        WebhookSubscription.user_id == current_user.user_id
    ).first()
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    return subscription

@router.put("/subscriptions/{subscription_id}", response_model=WebhookSubscriptionResponse)
async def update_webhook_subscription(
    subscription_id: str,
    subscription_update: WebhookSubscriptionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing webhook subscription.
    """
    ensure_webhooks_enabled()
    validate_webhook_url(subscription_update.url)
    subscription = db.query(WebhookSubscription).filter(
        WebhookSubscription.subscription_id == subscription_id,
        WebhookSubscription.user_id == current_user.user_id
    ).first()
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )

    # Update fields
    subscription.url = subscription_update.url
    subscription.events = json.dumps(subscription_update.events)
    if subscription_update.secret is not None:
        subscription.secret = encrypt_secret(subscription_update.secret)
    if subscription_update.headers is not None:
        subscription.headers = json.dumps(subscription_update.headers)

    db.commit()
    db.refresh(subscription)
    return subscription

@router.delete("/subscriptions/{subscription_id}")
async def delete_webhook_subscription(
    subscription_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a webhook subscription.
    """
    subscription = db.query(WebhookSubscription).filter(
        WebhookSubscription.subscription_id == subscription_id,
        WebhookSubscription.user_id == current_user.user_id
    ).first()
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )

    db.delete(subscription)
    db.commit()
    return {"message": "Subscription deleted successfully"}

@router.get("/subscriptions/{subscription_id}/deliveries", response_model=List[WebhookDeliveryResponse])
async def get_webhook_deliveries(
    subscription_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get delivery history for a webhook subscription.
    """
    # Verify subscription belongs to user
    subscription = db.query(WebhookSubscription).filter(
        WebhookSubscription.subscription_id == subscription_id,
        WebhookSubscription.user_id == current_user.user_id
    ).first()
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )

    deliveries = db.query(WebhookDelivery).filter(
        WebhookDelivery.subscription_id == subscription_id
    ).order_by(WebhookDelivery.attempted_at.desc()).all()
    return deliveries

# Helper function to trigger webhooks (would be called from other parts of the app)
def trigger_webhooks(user_id: str, event_type: str, payload: dict, background_tasks: BackgroundTasks):
    """
    Trigger webhooks for a user based on an event.
    This function would be called from various parts of the application
    when significant events occur.
    """
    from app.core.config import SessionLocal
    db = SessionLocal()
    try:
        # Find all active subscriptions for this user that match the event type
        subscriptions = db.query(WebhookSubscription).filter(
            WebhookSubscription.user_id == user_id,
            WebhookSubscription.is_active == True
        ).all()

        for subscription in subscriptions:
            try:
                # Check if the subscription is interested in this event type
                events_list = json.loads(subscription.events)
                if event_type in events_list or "*" in events_list:
                    # Prepare payload with metadata
                    webhook_payload = {
                        "event_type": event_type,
                        "timestamp": datetime.utcnow().isoformat(),
                        "user_id": str(user_id),
                        "data": payload
                    }

                    # Send webhook in background
                    background_tasks.add_task(
                        send_webhook_notification,
                        str(subscription.subscription_id),
                        event_type,
                        webhook_payload
                    )
            except Exception as e:
                # Log error but continue processing other subscriptions
                logger.error(
                    "Error processing webhook subscription %s: %s",
                    subscription.subscription_id,
                    redact_text(str(e)),
                )
    finally:
        db.close()
