"""Pydantic schemas for family endpoints."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class FamilyCreate(BaseModel):
    """Schema for creating a family."""

    name: Optional[str] = Field(
        default=None,
        description="Family name",
        max_length=200,
    )


class FamilyUpdate(BaseModel):
    """Schema for updating a family."""

    name: Optional[str] = Field(
        default=None,
        description="Family name",
        max_length=200,
    )


class FamilyResponse(BaseModel):
    """Family response schema."""

    family_id: UUID = Field(..., description="Family identifier")
    owner_user_id: Optional[UUID] = Field(
        default=None,
        description="Family head user identifier",
    )
    name: Optional[str] = Field(default=None, description="Family name")
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")

    model_config = ConfigDict(from_attributes=True)


class FamilyMemberAddRequest(BaseModel):
    """Schema for adding a member to a family."""

    user_id: Optional[UUID] = Field(default=None, description="User identifier")
    username: Optional[str] = Field(
        default=None,
        description="Username",
        max_length=100,
    )
    email: Optional[EmailStr] = Field(default=None, description="User email address")


class FamilyOwnerTransferRequest(BaseModel):
    """Schema for transferring family ownership."""

    user_id: Optional[UUID] = Field(default=None, description="User identifier")
    username: Optional[str] = Field(
        default=None,
        description="Username",
        max_length=100,
    )
    email: Optional[EmailStr] = Field(default=None, description="User email address")


class FamilyMemberResponse(BaseModel):
    """Family member response schema."""

    user_id: UUID = Field(..., description="User identifier")
    username: str = Field(..., description="Username")
    email: EmailStr = Field(..., description="Email address")
    is_active: bool = Field(default=True, description="Whether user account is active")
    share_library_with_family: bool = Field(
        default=False,
        description="Whether the user shares their library with family members",
    )

    model_config = ConfigDict(from_attributes=True)


class FamilyDetailResponse(BaseModel):
    """Family details with members."""

    family: FamilyResponse = Field(..., description="Family details")
    owner: Optional[FamilyMemberResponse] = Field(
        default=None,
        description="Family head user details",
    )
    members: list[FamilyMemberResponse] = Field(
        default_factory=list,
        description="Family members",
    )
