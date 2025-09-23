from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class SendMessageRequest(BaseModel):
    user_id: str = Field(
        ..., description="Sender user ID", min_length=1, max_length=255
    )
    device_id: str = Field(
        ..., description="Sender device ID", min_length=1, max_length=255
    )
    room_id: str = Field(
        ..., description="Target room ID", min_length=1, max_length=255
    )
    content: str = Field(
        ..., description="Message content", min_length=1, max_length=4000
    )


class SendMessageResponse(BaseModel):
    message_id: int = Field(..., description="Generated message ID")
    status: str = Field(..., description="Send status")
    timestamp: datetime = Field(..., description="Message timestamp")


class SyncMessagesRequest(BaseModel):
    user_id: str = Field(..., description="Requesting user ID")
    device_id: str = Field(..., description="Requesting device ID")
    room_id: str = Field(..., description="Target room ID")
    last_message_id: int = Field(
        default=0, description="Last received message ID", ge=0
    )


class MessageData(BaseModel):
    message_id: int = Field(..., description="Message ID")
    user_id: str = Field(..., description="Sender user ID")
    room_id: str = Field(..., description="Room ID")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(..., description="Message timestamp")
    message_type: str = Field(default="text", description="Message type")


class SyncMessagesResponse(BaseModel):
    messages: List[MessageData] = Field(..., description="List of new messages")
    cur_max_message_id: int = Field(
        ..., description="Current max message ID for the device"
    )
    has_more: bool = Field(default=False, description="Whether there are more messages")


class PresenceData(BaseModel):
    user_id: str = Field(..., description="User ID")
    status: str = Field(..., description="Online status")
    last_seen: datetime = Field(..., description="Last seen timestamp")
    ws_server: Optional[str] = Field(None, description="Connected WebSocket server")


class HealthResponse(BaseModel):
    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(..., description="Response timestamp")


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    timestamp: datetime = Field(..., description="Error timestamp")


# Internal models for message processing
class MessageQueuePayload(BaseModel):
    """Message payload for RabbitMQ queue"""

    message_id: int
    user_id: str
    device_id: str
    room_id: str
    content: str
    message_type: str = "text"
    timestamp: str  # ISO format
    metadata: Optional[dict] = None
