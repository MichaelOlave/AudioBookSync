"""Schemas for scheduled sync tasks."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SyncScheduleAction(str, Enum):
    """Allowed sync schedule actions."""

    METADATA_ONLY = "metadata_only"
    DOWNLOAD = "download"


class SyncScheduleCreate(BaseModel):
    """Request model for creating a sync schedule."""

    interval_minutes: int = Field(
        ...,
        ge=1,
        description="How often to check Audible and sync (in minutes)",
    )
    action: SyncScheduleAction = Field(
        default=SyncScheduleAction.METADATA_ONLY,
        description="Whether to only save metadata or also download missing books",
    )
    enabled: bool = Field(default=True, description="Whether the schedule is active")
    start_at: Optional[datetime] = Field(
        default=None,
        description="When to run the first check (UTC). Defaults to now + interval.",
    )


class SyncScheduleUpdate(BaseModel):
    """Request model for updating a sync schedule."""

    interval_minutes: Optional[int] = Field(
        default=None,
        ge=1,
        description="Updated interval in minutes",
    )
    action: Optional[SyncScheduleAction] = Field(
        default=None,
        description="Updated action for the schedule",
    )
    enabled: Optional[bool] = Field(
        default=None,
        description="Enable or disable the schedule",
    )
    start_at: Optional[datetime] = Field(
        default=None,
        description="When to run the next check (UTC).",
    )


class SyncScheduleResponse(BaseModel):
    """Response model for sync schedule details."""

    schedule_id: UUID = Field(description="Schedule UUID")
    user_id: UUID = Field(description="User UUID")
    interval_minutes: int = Field(description="Interval in minutes")
    action: SyncScheduleAction = Field(description="Scheduled action")
    enabled: bool = Field(description="Whether the schedule is active")
    last_run_at: Optional[datetime] = Field(
        default=None,
        description="When this schedule last ran",
    )
    next_run_at: datetime = Field(description="Next scheduled run time")
    created_at: datetime = Field(description="When this schedule was created")
    updated_at: datetime = Field(description="When this schedule was last updated")

    model_config = ConfigDict(from_attributes=True)


class SyncScheduleList(BaseModel):
    """Response model for a list of sync schedules."""

    items: List[SyncScheduleResponse] = Field(default_factory=list)
    total: int = Field(ge=0, description="Total schedules for the user")
