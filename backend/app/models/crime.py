from sqlalchemy import Column, Integer, Float, Text, DateTime, Boolean, Index, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from backend.app.database import Base

class CrimeRecord(Base):
    """
    Model representing incident records (e.g., FIRs or synthetic test fixtures).
    Includes a mandatory `is_development_data` flag to strictly separate
    synthetic test fixtures from future verified police records.
    """
    __tablename__ = "crime_records"

    id = Column(Integer, primary_key=True, index=True)
    fir_number = Column(Text, unique=True, index=True, nullable=False)
    crime_date = Column(DateTime, nullable=False, index=True)
    crime_type = Column(Text, nullable=False, index=True)
    severity_weight = Column(Float, nullable=False)     # 1.0 (Low) to 5.0 (High)
    time_of_day = Column(Text, nullable=False)         # 'Day', 'Dusk', 'Night', 'Late Night'
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    geometry = Column(Geometry("POINT", srid=4326))
    is_development_data = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_crime_records_date", "crime_date"),
        Index("idx_crime_records_type", "crime_type"),
        Index("idx_crime_records_dev", "is_development_data"),
    )


class RoadCrimeFeature(Base):
    """
    Road-level crime feature dataset created by spatially associating
    crime_records with nearby road segments using PostGIS.
    road_id directly maps to canonical roads.id.
    """
    __tablename__ = "road_crime_features"

    road_id = Column(Integer, ForeignKey("roads.id", ondelete="CASCADE"), primary_key=True)
    crime_count = Column(Integer, default=0, nullable=False)
    recent_crime_count = Column(Integer, default=0, nullable=False)    # Incidents in past 12 months
    crime_density = Column(Float, default=0.0, nullable=False)         # Crimes per kilometer of road length
    average_severity = Column(Float, default=0.0, nullable=False)      # Mean severity weight (1.0 to 5.0)
    night_crime_ratio = Column(Float, default=0.0, nullable=False)     # Fraction of incidents during dusk/night
    min_crime_distance = Column(Float, default=5000.0, nullable=False) # Meters to nearest crime point (default 5000m)
    is_development_data = Column(Boolean, default=True, nullable=False)# Explicit flag distinguishing dev/test from real
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    road = relationship("Road")

    __table_args__ = (
        Index("idx_road_crime_density", "crime_density"),
        Index("idx_road_crime_count", "crime_count"),
        Index("idx_road_crime_dev", "is_development_data"),
    )
