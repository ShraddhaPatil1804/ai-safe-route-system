from sqlalchemy import Column, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from backend.app.database import Base, pg_engine

class UserReport(Base):
    __tablename__ = "user_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    report_type = Column(Text, nullable=False)
    description = Column(Text)
    severity = Column(Text, nullable=False)
    status = Column(Text, default="pending")
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # Use native PostGIS Geometry when PostgreSQL is active, or WKT Text in SQLite fallback mode
    if pg_engine is not None:
        geometry = Column(Geometry("POINT", srid=4326))
    else:
        geometry = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User")
