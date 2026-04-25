"""Team workspace management — organizations, roles, shared conversations."""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from database import TeamRepository, TeamMemberRepository
from routes.deps import require_authentication
from security import log_audit_event
from security.auth import User

logger = logging.getLogger("routes.teams")

router = APIRouter()


class CreateTeamRequest(BaseModel):
    name: str
    description: str = ""


@router.post("/teams")
async def create_team(
    body: CreateTeamRequest,
    user: User = Depends(require_authentication),
):
    """Create a new team workspace."""
    team = await TeamRepository.create(
        name=body.name,
        description=body.description,
        created_by=user.id,
    )
    if not team:
        raise HTTPException(status_code=500, detail="Failed to create team")

    log_audit_event("team_create", user.username, "team_created",
                     resource=f"team:{team.id}", success=True)

    return {"id": str(team.id), "name": body.name, "role": "admin"}


@router.get("/teams")
async def list_teams(user: User = Depends(require_authentication)):
    """List all teams the user belongs to."""
    teams = await TeamRepository.get_by_user(user.id)

    result = []
    for team in teams:
        team_id = str(team.id)
        members = await TeamMemberRepository.get_members(team_id)
        user_member = next((m for m in members if str(m.user_id) == user.id), None)
        result.append({
            "id": team_id,
            "name": team.name,
            "role": user_member.role if user_member else "member",
            "member_count": len(members),
        })

    return {"teams": result}


@router.get("/teams/{team_id}")
async def get_team(team_id: str, user: User = Depends(require_authentication)):
    """Get team details."""
    team = await TeamRepository.get_by_id(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    members = await TeamMemberRepository.get_members(team_id)
    is_member = any(str(m.user_id) == user.id for m in members)
    if not is_member:
        raise HTTPException(status_code=403, detail="Not a team member")

    member_list = []
    for m in members:
        member_list.append({
            "user_id": str(m.user_id),
            "role": m.role,
            "joined_at": str(m.joined_at) if m.joined_at else None,
        })

    return {
        "id": team_id,
        "name": team.name,
        "description": team.description,
        "members": member_list,
        "member_count": len(members),
        "created_at": str(team.created_at) if team.created_at else None,
    }


@router.post("/teams/{team_id}/invite")
async def invite_to_team(
    team_id: str,
    username: str = Query(...),
    role: str = Query("member"),
    user: User = Depends(require_authentication),
):
    """Invite a user to the team."""
    team = await TeamRepository.get_by_id(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    members = await TeamMemberRepository.get_members(team_id)
    inviter = next((m for m in members if str(m.user_id) == user.id), None)
    if not inviter or inviter.role not in ("admin", "owner"):
        raise HTTPException(status_code=403, detail="Only admins can invite")

    if role not in ("member", "admin"):
        raise HTTPException(status_code=400, detail="Role must be 'member' or 'admin'")

    # Check if already a member
    if any(str(m.user_id) == username for m in members):
        raise HTTPException(status_code=400, detail="User is already a member")

    # Add member (uses username as user_id placeholder — production would resolve to real user ID)
    member = await TeamMemberRepository.add(team_id, username, role=role)
    if not member:
        raise HTTPException(status_code=500, detail="Failed to add team member")

    log_audit_event("team_invite", user.username, "team_member_invited",
                     resource=f"team:{team_id}", success=True)

    return {"status": "invited", "username": username, "role": role}


@router.delete("/teams/{team_id}/members/{username}")
async def remove_from_team(
    team_id: str,
    username: str,
    user: User = Depends(require_authentication),
):
    """Remove a member from the team."""
    members = await TeamMemberRepository.get_members(team_id)
    remover = next((m for m in members if str(m.user_id) == user.id), None)
    if not remover or remover.role not in ("admin", "owner"):
        raise HTTPException(status_code=403, detail="Only admins can remove members")

    removed = await TeamMemberRepository.remove(team_id, username)

    return {"status": "removed" if removed else "not_found", "username": username}


@router.get("/teams/{team_id}/search")
async def search_team_conversations(
    team_id: str,
    query: str = Query(...),
    limit: int = Query(20),
    user: User = Depends(require_authentication),
):
    """Search across all team conversations."""
    is_member = await TeamMemberRepository.is_member(team_id, user.id)
    if not is_member:
        raise HTTPException(status_code=403, detail="Not a team member")

    return {
        "results": [],
        "query": query,
        "team_id": team_id,
        "message": "Team search requires database backend (PostgreSQL)",
    }