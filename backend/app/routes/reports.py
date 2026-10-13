from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional

from backend.app.database import get_db
from backend.app.models.report import UserReport
from backend.app.models.user import User
from backend.app.schemas.report import ReportCreate, ReportOut
from backend.app.utils.security import get_current_user, get_optional_current_user

router = APIRouter(prefix="/reports", tags=["Safety Reports"])

@router.post("", response_model=ReportOut)
def create_report(
    payload: ReportCreate,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit a user safety incident/hazard report.
    Treated as community-sourced feedback with 'pending' status for moderation.
    """
    valid_severities = ["Low", "Medium", "High", "Critical"]
    severity = payload.severity.capitalize() if payload.severity.capitalize() in valid_severities else "Medium"

    report = UserReport(
        user_id=current_user.id if current_user else None,
        report_type=payload.report_type.strip(),
        description=payload.description.strip() if payload.description else "",
        severity=severity,
        status="pending",
        latitude=payload.latitude,
        longitude=payload.longitude,
        geometry=f"POINT({payload.longitude} {payload.latitude})"
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return ReportOut.model_validate(report)

@router.get("", response_model=List[ReportOut])
def get_reports(
    status: Optional[str] = Query(None, description="Filter by status ('pending', 'reviewed', 'resolved')"),
    report_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Retrieve safety reports for community awareness and moderation.
    """
    query = db.query(UserReport)
    if status:
        query = query.filter(UserReport.status == status.lower())
    if report_type:
        query = query.filter(UserReport.report_type.ilike(f"%{report_type}%"))
    reports = query.order_by(UserReport.created_at.desc()).limit(limit).all()
    return [ReportOut.model_validate(r) for r in reports]
