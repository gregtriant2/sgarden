"""User profile, search, and administration endpoints."""

import hashlib
import os
import re
import subprocess
from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from database import users_collection
from security.jwt_handler import get_current_admin, get_current_user

router = APIRouter(prefix="/api/users", tags=["users"])

VALID_ROLES = {"user", "admin"}
REPORTS_DIR = os.path.abspath("./reports")

# Whitelisted diagnostic commands. Values are fixed argument lists run without
# a shell, so no user input can be interpreted as a command.
ALLOWED_COMMANDS = {
    "uptime": ["uptime"],
    "disk": ["df", "-h"],
    "memory": ["free", "-h"],
    "date": ["date"],
}


def user_to_response(user: dict) -> dict:
    """Convert a MongoDB user document to an API response (no password hash)."""
    return {
        "id": str(user["_id"]),
        "username": user.get("username"),
        "email": user.get("email"),
        "role": user.get("role"),
        "lastActiveAt": str(user.get("lastActiveAt", "")),
        "createdAt": str(user.get("createdAt", "")),
    }


@router.get("/profile/{user_id}")
async def get_user_profile(user_id: str, _current_user: dict = Depends(get_current_user)):
    """Get a user profile by id."""
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user_to_response(user)


@router.get("/details/{user_id}")
async def get_user_details(user_id: str, _current_user: dict = Depends(get_current_user)):
    """Get user details by id."""
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user_to_response(user)


@router.get("/search")
async def search_users(query: str):
    """Search users by username (substring, case-insensitive)."""
    # Escape the input so it is matched literally and cannot inject regex operators.
    pattern = re.escape(query)
    cursor = users_collection.find({"username": {"$regex": pattern, "$options": "i"}})
    return [user_to_response(user) async for user in cursor]


@router.post("/system/info")
async def get_system_info(request: dict, _current_user: dict = Depends(get_current_user)):
    """Run a whitelisted diagnostic command (no shell, no user-supplied arguments)."""
    command = request.get("command", "date")
    argv = ALLOWED_COMMANDS.get(command)
    if argv is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported command. Allowed: {', '.join(sorted(ALLOWED_COMMANDS))}",
        )

    try:
        result = subprocess.run(
            argv, shell=False, capture_output=True, text=True, timeout=10, check=False
        )
        return {"output": result.stdout, "error": result.stderr}
    except subprocess.SubprocessError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Command failed: {exc}",
        )


@router.get("/reports/download")
async def download_report(filename: str, _current_user: dict = Depends(get_current_user)):
    """Download a report file from the reports directory."""
    # Resolve against the reports directory and reject anything that escapes it.
    requested = os.path.abspath(os.path.join(REPORTS_DIR, filename))
    if os.path.commonpath([REPORTS_DIR, requested]) != REPORTS_DIR:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename")

    try:
        with open(requested, "r", encoding="utf-8") as handle:
            content = handle.read()
        return {"filename": filename, "content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")


@router.post("/hash")
async def hash_data(request: dict):
    """Hash the provided data with SHA-256."""
    data = request.get("data", "")
    digest = hashlib.sha256(data.encode()).hexdigest()
    return {"hash": digest, "algorithm": "SHA-256"}


@router.get("/advanced-search")
async def advanced_search(
    username: str = None,
    email: str = None,
    role: str = None,
    sort_by: str = None,
    order: str = None,
):
    """Search users by optional username/email substring and exact role."""
    query: dict = {}
    if username is not None:
        query["username"] = {"$regex": re.escape(username), "$options": "i"}
    if email is not None:
        query["email"] = {"$regex": re.escape(email), "$options": "i"}
    if role is not None:
        query["role"] = role

    cursor = users_collection.find(query)
    if sort_by:
        direction = -1 if (order and order.lower() == "desc") else 1
        cursor = cursor.sort(sort_by, direction)

    return [user_to_response(user) async for user in cursor]


@router.delete("/{user_id}")
async def delete_user(user_id: str, _admin: dict = Depends(get_current_admin)):
    """Delete a user (admin only)."""
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    result = await users_collection.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return {"message": "User deleted"}


@router.put("/{user_id}/role")
async def change_role(user_id: str, request: dict, _admin: dict = Depends(get_current_admin)):
    """Change a user's role (admin only)."""
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    new_role = request.get("role")
    if new_role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role must be one of: {', '.join(sorted(VALID_ROLES))}",
        )

    result = await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"role": new_role, "updatedAt": datetime.utcnow()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return {"message": "Role updated", "role": new_role}
