"""Family management endpoints."""

from fastapi import APIRouter, Depends, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.engine import get_db_session
from ...database.models.user import User
from ...database.services import user_service
from ..middleware.error_handler import (
    AuthorizationError,
    ConflictError,
    InternalServerError,
    ResourceNotFoundError,
    ValidationError,
    handle_route_errors,
)
from ..schemas.common import MessageResponse
from ..schemas.family import (
    FamilyCreate,
    FamilyDetailResponse,
    FamilyMemberAddRequest,
    FamilyMemberResponse,
    FamilyOwnerTransferRequest,
    FamilyResponse,
    FamilyUpdate,
)
from ..security.auth import get_current_user

router = APIRouter()


def _ensure_family_member(current_user: User, family_id: str) -> None:
    if not current_user.family_id or str(current_user.family_id) != family_id:
        raise AuthorizationError("Not authorized to access this family")


def _ensure_family_owner(current_user: User, family) -> None:
    _ensure_family_member(current_user, str(family.family_id))
    if family.owner_user_id and str(family.owner_user_id) != str(current_user.user_id):
        raise AuthorizationError("Only the family head can modify this family")


async def _resolve_user_target(
    db: AsyncSession,
    user_id: str | None,
    username: str | None,
    email: str | None,
) -> User:
    if user_id:
        user = await user_service.get_user_by_id(db, user_id)
    elif email:
        user = await user_service.get_user_by_email(db, email)
    elif username:
        user = await user_service.get_user_by_username(db, username)
    else:
        raise ValidationError("Provide user_id, email, or username")

    if not user:
        raise ResourceNotFoundError("User not found")
    return user


@router.post(
    "/",
    response_model=FamilyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create family",
    description="Create a new family and add the current user as a member",
    responses={
        201: {"description": "Family created successfully"},
        401: {"description": "Not authenticated"},
        409: {"description": "User already belongs to a family"},
    },
)
@handle_route_errors("create family")
async def create_family(
    payload: FamilyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> FamilyResponse:
    """Create a family and assign the current user to it."""
    if current_user.family_id:
        raise ConflictError("User already belongs to a family")

    family = await user_service.create_family(db, payload.name, current_user.user_id)
    if not family:
        raise InternalServerError("Failed to create family")

    updated_user = await user_service.update_user_family_settings(
        db,
        str(current_user.user_id),
        {"family_id": family.family_id},
    )
    if not updated_user:
        raise InternalServerError("Failed to assign user to family")

    await db.commit()
    await db.refresh(family)
    logger.info(f"Created family {family.family_id} for user {current_user.user_id}")
    return FamilyResponse.from_orm(family)


@router.get(
    "/me",
    response_model=FamilyDetailResponse,
    summary="Get current family",
    description="Get the current user's family details and members",
    responses={
        200: {"description": "Family retrieved successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Family not found"},
    },
)
@handle_route_errors("get current family")
async def get_current_family(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> FamilyDetailResponse:
    """Get the current user's family details."""
    if not current_user.family_id:
        raise ResourceNotFoundError("User is not in a family")

    family_id = str(current_user.family_id)
    family = await user_service.get_family_by_id(db, family_id)
    if not family:
        raise ResourceNotFoundError("Family not found")

    members = await user_service.get_family_members(db, family_id)
    owner_member = None
    if family.owner_user_id:
        for member in members:
            if str(member.user_id) == str(family.owner_user_id):
                owner_member = member
                break
    return FamilyDetailResponse(
        family=FamilyResponse.from_orm(family),
        owner=FamilyMemberResponse.from_orm(owner_member) if owner_member else None,
        members=[FamilyMemberResponse.from_orm(member) for member in members],
    )


@router.get(
    "/{family_id}",
    response_model=FamilyDetailResponse,
    summary="Get family",
    description="Get family details and members",
    responses={
        200: {"description": "Family retrieved successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this family"},
        404: {"description": "Family not found"},
    },
)
@handle_route_errors("get family")
async def get_family(
    family_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> FamilyDetailResponse:
    """Get family details for a specific family."""
    family = await user_service.get_family_by_id(db, family_id)
    if not family:
        raise ResourceNotFoundError("Family not found")
    _ensure_family_member(current_user, family_id)

    members = await user_service.get_family_members(db, family_id)
    owner_member = None
    if family.owner_user_id:
        for member in members:
            if str(member.user_id) == str(family.owner_user_id):
                owner_member = member
                break
    return FamilyDetailResponse(
        family=FamilyResponse.from_orm(family),
        owner=FamilyMemberResponse.from_orm(owner_member) if owner_member else None,
        members=[FamilyMemberResponse.from_orm(member) for member in members],
    )


@router.patch(
    "/{family_id}",
    response_model=FamilyResponse,
    summary="Update family",
    description="Update family details such as name",
    responses={
        200: {"description": "Family updated successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this family"},
        404: {"description": "Family not found"},
        422: {"description": "Invalid update payload"},
    },
)
@handle_route_errors("update family")
async def update_family(
    family_id: str,
    payload: FamilyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> FamilyResponse:
    """Update family details."""
    family = await user_service.get_family_by_id(db, family_id)
    if not family:
        raise ResourceNotFoundError("Family not found")
    _ensure_family_owner(current_user, family)

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise ValidationError("Provide at least one field to update")

    family = await user_service.update_family(db, family_id, updates)
    if not family:
        raise ResourceNotFoundError("Family not found")

    await db.commit()
    await db.refresh(family)
    return FamilyResponse.from_orm(family)


@router.post(
    "/{family_id}/members",
    response_model=FamilyMemberResponse,
    summary="Add family member",
    description="Add an existing user to the family",
    responses={
        200: {"description": "Member added successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this family"},
        404: {"description": "Family or user not found"},
        409: {"description": "User belongs to another family"},
        422: {"description": "Invalid request payload"},
    },
)
@handle_route_errors("add family member")
async def add_family_member(
    family_id: str,
    payload: FamilyMemberAddRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> FamilyMemberResponse:
    """Add a member to the family."""
    family = await user_service.get_family_by_id(db, family_id)
    if not family:
        raise ResourceNotFoundError("Family not found")
    _ensure_family_owner(current_user, family)

    target_user = await _resolve_user_target(
        db,
        str(payload.user_id) if payload.user_id else None,
        payload.username,
        payload.email,
    )

    if target_user.family_id and str(target_user.family_id) != family_id:
        raise ConflictError("User already belongs to another family")

    if not target_user.family_id:
        updated_user = await user_service.update_user_family_settings(
            db,
            str(target_user.user_id),
            {"family_id": family_id},
        )
        if not updated_user:
            raise InternalServerError("Failed to add family member")
        await db.commit()
        await db.refresh(updated_user)
        target_user = updated_user

    return FamilyMemberResponse.from_orm(target_user)


@router.patch(
    "/{family_id}/owner",
    response_model=FamilyResponse,
    summary="Transfer family ownership",
    description="Transfer family head role to another member",
    responses={
        200: {"description": "Family ownership transferred successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this family"},
        404: {"description": "Family or user not found"},
        422: {"description": "Invalid request payload"},
    },
)
@handle_route_errors("transfer family ownership")
async def transfer_family_ownership(
    family_id: str,
    payload: FamilyOwnerTransferRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> FamilyResponse:
    """Transfer family ownership to another existing member."""
    family = await user_service.get_family_by_id(db, family_id)
    if not family:
        raise ResourceNotFoundError("Family not found")
    _ensure_family_owner(current_user, family)

    target_user = await _resolve_user_target(
        db,
        str(payload.user_id) if payload.user_id else None,
        payload.username,
        payload.email,
    )

    if not target_user.family_id or str(target_user.family_id) != family_id:
        raise ValidationError("New family head must be a member of the family")

    if family.owner_user_id and str(family.owner_user_id) == str(target_user.user_id):
        return FamilyResponse.from_orm(family)

    family = await user_service.update_family(
        db,
        family_id,
        {"owner_user_id": target_user.user_id},
    )
    if not family:
        raise InternalServerError("Failed to transfer family ownership")

    await db.commit()
    await db.refresh(family)
    return FamilyResponse.from_orm(family)


@router.delete(
    "/{family_id}",
    response_model=MessageResponse,
    summary="Delete family",
    description="Delete the family and remove all members",
    responses={
        200: {"description": "Family deleted successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this family"},
        404: {"description": "Family not found"},
    },
)
@handle_route_errors("delete family")
async def delete_family(
    family_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """Delete a family."""
    family = await user_service.get_family_by_id(db, family_id)
    if not family:
        raise ResourceNotFoundError("Family not found")
    _ensure_family_owner(current_user, family)

    success = await user_service.delete_family(db, family_id)
    if not success:
        raise InternalServerError("Failed to delete family")

    await db.commit()
    return MessageResponse(message="Family deleted successfully", success=True)


@router.delete(
    "/{family_id}/members/{member_id}",
    response_model=MessageResponse,
    summary="Remove family member",
    description="Remove a member from the family",
    responses={
        200: {"description": "Member removed successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this family"},
        404: {"description": "Family or user not found"},
    },
)
@handle_route_errors("remove family member")
async def remove_family_member(
    family_id: str,
    member_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """Remove a member from the family."""
    family = await user_service.get_family_by_id(db, family_id)
    if not family:
        raise ResourceNotFoundError("Family not found")
    _ensure_family_owner(current_user, family)

    if family.owner_user_id and str(family.owner_user_id) == member_id:
        raise ValidationError("Family head cannot be removed")

    member = await user_service.get_user_by_id(db, member_id)
    if not member or not member.family_id or str(member.family_id) != family_id:
        raise ResourceNotFoundError("User not found in family")

    updated_user = await user_service.update_user_family_settings(
        db,
        str(member.user_id),
        {"family_id": None},
    )
    if not updated_user:
        raise InternalServerError("Failed to remove family member")

    await db.commit()
    return MessageResponse(
        message="Family member removed successfully",
        success=True,
    )
