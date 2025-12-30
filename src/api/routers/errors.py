"""Error logging and analytics endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_errors():
    """List errors - TO BE IMPLEMENTED."""
    return {"message": "List errors endpoint - not yet implemented"}


@router.get("/summary")
async def get_error_summary():
    """Get error summary/analytics - TO BE IMPLEMENTED."""
    return {"message": "Get error summary endpoint - not yet implemented"}
