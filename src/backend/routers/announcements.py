"""
Announcements endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
from datetime import datetime, date
from pydantic import BaseModel, Field

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


class AnnouncementCreate(BaseModel):
    """Model for creating a new announcement"""
    message: str = Field(..., min_length=1, max_length=500)
    start_date: str | None = None
    expiration_date: str = Field(..., description="Required expiration date in YYYY-MM-DD format")
    

class AnnouncementUpdate(BaseModel):
    """Model for updating an announcement"""
    message: str | None = Field(None, min_length=1, max_length=500)
    start_date: str | None = None
    expiration_date: str | None = Field(None, description="Expiration date in YYYY-MM-DD format")


def verify_authenticated_user(username: str) -> Dict[str, Any]:
    """Verify that the user is authenticated"""
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return teacher


def is_announcement_active(announcement: Dict[str, Any]) -> bool:
    """Check if an announcement is currently active based on dates"""
    today = date.today().isoformat()
    
    # Check expiration date
    if announcement.get("expiration_date", "") < today:
        return False
    
    # Check start date if present
    start_date = announcement.get("start_date")
    if start_date and start_date > today:
        return False
    
    return True


@router.get("/current")
def get_current_announcements() -> List[Dict[str, Any]]:
    """Get all currently active announcements (public endpoint)"""
    all_announcements = announcements_collection.find({})
    
    # Filter active announcements
    active_announcements = [
        {
            "_id": ann["_id"],
            "message": ann["message"],
            "start_date": ann.get("start_date"),
            "expiration_date": ann["expiration_date"]
        }
        for ann in all_announcements
        if is_announcement_active(ann)
    ]
    
    return active_announcements


@router.get("")
def get_all_announcements(username: str) -> List[Dict[str, Any]]:
    """Get all announcements (requires authentication)"""
    # Verify user is authenticated
    verify_authenticated_user(username)
    
    # Return all announcements
    announcements = announcements_collection.find({})
    return announcements


@router.post("")
def create_announcement(announcement: AnnouncementCreate, username: str) -> Dict[str, Any]:
    """Create a new announcement (requires authentication)"""
    # Verify user is authenticated
    verify_authenticated_user(username)
    
    # Validate date format for expiration_date
    try:
        datetime.fromisoformat(announcement.expiration_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid expiration_date format. Use YYYY-MM-DD")
    
    # Validate start_date format if provided
    if announcement.start_date:
        try:
            datetime.fromisoformat(announcement.start_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
    
    # Generate unique ID
    import uuid
    announcement_id = f"announcement-{uuid.uuid4()}"
    
    # Create announcement document
    announcement_doc = {
        "_id": announcement_id,
        "message": announcement.message,
        "start_date": announcement.start_date,
        "expiration_date": announcement.expiration_date,
        "created_by": username,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    
    # Insert into database
    announcements_collection.insert_one(announcement_doc)
    
    return announcement_doc


@router.put("/{announcement_id}")
def update_announcement(
    announcement_id: str,
    announcement: AnnouncementUpdate,
    username: str
) -> Dict[str, Any]:
    """Update an existing announcement (requires authentication)"""
    # Verify user is authenticated
    verify_authenticated_user(username)
    
    # Check if announcement exists
    existing = announcements_collection.find_one({"_id": announcement_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Build update document
    update_fields = {}
    if announcement.message is not None:
        update_fields["message"] = announcement.message
    if announcement.start_date is not None:
        try:
            datetime.fromisoformat(announcement.start_date)
            update_fields["start_date"] = announcement.start_date
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
    if announcement.expiration_date is not None:
        try:
            datetime.fromisoformat(announcement.expiration_date)
            update_fields["expiration_date"] = announcement.expiration_date
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid expiration_date format. Use YYYY-MM-DD")
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    # Update announcement
    announcements_collection.update_one(
        {"_id": announcement_id},
        {"$set": update_fields}
    )
    
    # Return updated announcement
    updated = announcements_collection.find_one({"_id": announcement_id})
    return updated


@router.delete("/{announcement_id}")
def delete_announcement(announcement_id: str, username: str) -> Dict[str, str]:
    """Delete an announcement (requires authentication)"""
    # Verify user is authenticated
    verify_authenticated_user(username)
    
    # Check if announcement exists
    existing = announcements_collection.find_one({"_id": announcement_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Delete announcement
    announcements_collection.data.pop(announcement_id, None)
    
    return {"status": "success", "message": "Announcement deleted"}
