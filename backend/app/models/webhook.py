from sqlalchemy import Column, DateTime, Boolean, String, Text, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from .base import Base, BaseModel
import uuid
from datetime import datetime
import json


class WebhookSubscription(Base, BaseModel):
    """Model for storing webhook subscriptions."""
    __tablename__ = "webhook_subscriptions"
    __table_args__ = {'schema': 'financial'}

    subscription_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("financial.users.user_id"), nullable=False)
    # The URL to send the webhook to
    url = Column(String(500), nullable=False)
    # The events this webhook is subscribed to (as a JSON list of strings)
    # Example: ["life_event:marriage", "market_condition:stock_drop_10pct"]
    events = Column(Text, nullable=False)  # JSON string of list of event types
    # Whether the webhook is active
    is_active = Column(Boolean, nullable=False, default=True)
    # Optional: a secret for signing the webhook payload (for verification by the receiver)
    secret = Column(String(255), nullable=True)
    # Headers to include in the webhook request (as JSON)
    headers = Column(Text, nullable=True)  # JSON string of headers
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user = relationship("User", back_populates="webhook_subscriptions")
    deliveries = relationship("WebhookDelivery", back_populates="subscription")


class WebhookDelivery(Base, BaseModel):
    """Model for logging webhook delivery attempts."""
    __tablename__ = "webhook_deliveries"
    __table_args__ = {'schema': 'financial'}

    delivery_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("financial.webhook_subscriptions.subscription_id"), nullable=False)
    # The event that triggered this delivery
    event_type = Column(String(100), nullable=False)
    # The payload sent (as JSON)
    payload = Column(Text, nullable=False)
    # The HTTP status code returned by the endpoint (if any)
    status_code = Column(Integer, nullable=True)
    # Any error message if the delivery failed
    error_message = Column(Text, nullable=True)
    # When the delivery was attempted
    attempted_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    # When the delivery was completed (if successful)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationship
    subscription = relationship("WebhookSubscription", back_populates="deliveries")