"""
Announcements endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List
from datetime import datetime
from bson import ObjectId

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
def get_announcements() -> List[Dict[str, Any]]:
    """
    Get all active announcements (within their date range)
    """
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    announcements = []
    for announcement in announcements_collection.find():
        # Check if announcement is active
        start_date = announcement.get("start_date")
        expiration_date = announcement.get("expiration_date")
        
        # If start_date is set, check if we're past it
        if start_date and current_date < start_date:
            continue
            
        # Check if we're before expiration
        if current_date <= expiration_date:
            announcements.append({
                "id": str(announcement["_id"]),
                "message": announcement["message"],
                "start_date": announcement.get("start_date"),
                "expiration_date": announcement["expiration_date"],
                "created_by": announcement.get("created_by")
            })
    
    return announcements


@router.get("/all", response_model=List[Dict[str, Any]])
def get_all_announcements(teacher_username: str = Query(...)) -> List[Dict[str, Any]]:
    """
    Get all announcements (active and inactive) - requires teacher authentication
    """
    # Check teacher authentication
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Authentication required")
    
    announcements = []
    for announcement in announcements_collection.find().sort("expiration_date", -1):
        announcements.append({
            "id": str(announcement["_id"]),
            "message": announcement["message"],
            "start_date": announcement.get("start_date"),
            "expiration_date": announcement["expiration_date"],
            "created_by": announcement.get("created_by")
        })
    
    return announcements


@router.post("", response_model=Dict[str, Any])
@router.post("/", response_model=Dict[str, Any])
def create_announcement(
    message: str,
    expiration_date: str,
    teacher_username: str = Query(...),
    start_date: str = Query(None)
) -> Dict[str, Any]:
    """
    Create a new announcement - requires teacher authentication
    
    - message: The announcement message
    - expiration_date: Required expiration date (YYYY-MM-DD format)
    - start_date: Optional start date (YYYY-MM-DD format)
    - teacher_username: Username of the authenticated teacher
    """
    # Check teacher authentication
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Authentication required")
    
    # Validate dates
    try:
        datetime.strptime(expiration_date, "%Y-%m-%d")
        if start_date:
            datetime.strptime(start_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Create announcement document
    announcement_doc = {
        "message": message,
        "expiration_date": expiration_date,
        "created_by": teacher_username
    }
    
    if start_date:
        announcement_doc["start_date"] = start_date
    
    # Insert into database
    result = announcements_collection.insert_one(announcement_doc)
    
    return {
        "id": str(result.inserted_id),
        "message": message,
        "start_date": start_date,
        "expiration_date": expiration_date,
        "created_by": teacher_username
    }


@router.put("/{announcement_id}", response_model=Dict[str, Any])
def update_announcement(
    announcement_id: str,
    message: str,
    expiration_date: str,
    teacher_username: str = Query(...),
    start_date: str = Query(None)
) -> Dict[str, Any]:
    """
    Update an existing announcement - requires teacher authentication
    """
    # Check teacher authentication
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Authentication required")
    
    # Validate announcement exists
    try:
        obj_id = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(
            status_code=400, detail="Invalid announcement ID")
    
    announcement = announcements_collection.find_one({"_id": obj_id})
    if not announcement:
        raise HTTPException(
            status_code=404, detail="Announcement not found")
    
    # Validate dates
    try:
        datetime.strptime(expiration_date, "%Y-%m-%d")
        if start_date:
            datetime.strptime(start_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Update announcement
    update_doc = {
        "message": message,
        "expiration_date": expiration_date
    }
    
    if start_date:
        update_doc["start_date"] = start_date
    else:
        # Remove start_date if not provided
        announcements_collection.update_one(
            {"_id": obj_id},
            {"$unset": {"start_date": ""}}
        )
    
    result = announcements_collection.update_one(
        {"_id": obj_id},
        {"$set": update_doc}
    )
    
    if result.modified_count == 0 and result.matched_count == 0:
        raise HTTPException(
            status_code=500, detail="Failed to update announcement")
    
    return {
        "id": announcement_id,
        "message": message,
        "start_date": start_date,
        "expiration_date": expiration_date,
        "created_by": announcement.get("created_by")
    }


@router.delete("/{announcement_id}")
def delete_announcement(
    announcement_id: str,
    teacher_username: str = Query(...)
) -> Dict[str, str]:
    """
    Delete an announcement - requires teacher authentication
    """
    # Check teacher authentication
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Authentication required")
    
    # Validate announcement exists
    try:
        obj_id = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(
            status_code=400, detail="Invalid announcement ID")
    
    # Delete announcement
    result = announcements_collection.delete_one({"_id": obj_id})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404, detail="Announcement not found")
    
    return {"message": "Announcement deleted successfully"}
