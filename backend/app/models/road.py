from sqlalchemy import Column, Integer, BigInteger, Float, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from backend.app.database import Base

class Intersection(Base):
    __tablename__ = "intersections"

    id = Column(Integer, primary_key=True, index=True)
    osmid = Column(BigInteger, index=True, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    geometry = Column(Geometry("POINT", srid=4326))

class Road(Base):
    __tablename__ = "roads"

    id = Column(Integer, primary_key=True, index=True)
    osm_way_id = Column(Text)
    from_node = Column(BigInteger, index=True, nullable=False)
    to_node = Column(BigInteger, index=True, nullable=False)
    road_name = Column(Text)
    road_type = Column(Text, index=True)
    maxspeed = Column(Text)
    lanes = Column(Text)
    length = Column(Float, nullable=False)
    geometry = Column(Geometry("LINESTRING", srid=4326))
    created_at = Column(DateTime, server_default=func.now())

    feature = relationship("RoadFeature", back_populates="road", uselist=False)

class RoadFeature(Base):
    __tablename__ = "road_features"

    road_id = Column(Integer, ForeignKey("roads.id", ondelete="CASCADE"), primary_key=True)
    length = Column(Float)
    road_type = Column(Text)
    
    police_distance = Column(Float)
    hospital_distance = Column(Float)
    pharmacy_distance = Column(Float)
    
    police_count = Column(Integer, default=0)
    hospital_count = Column(Integer, default=0)
    pharmacy_count = Column(Integer, default=0)
    
    bus_stop_count = Column(Integer, default=0)
    restaurant_count = Column(Integer, default=0)
    cafe_count = Column(Integer, default=0)
    market_count = Column(Integer, default=0)
    bank_count = Column(Integer, default=0)
    fuel_station_count = Column(Integer, default=0)
    liquor_shop_count = Column(Integer, default=0)
    bar_count = Column(Integer, default=0)
    park_count = Column(Integer, default=0)
    
    commercial_density = Column(Float, default=0.0)
    crowd_score = Column(Float, default=0.0)
    isolation_score = Column(Float, default=0.0)
    lighting_score = Column(Float, default=0.0)
    connectivity_score = Column(Float, default=0.0)
    emergency_access_score = Column(Float, default=0.0)
    
    lighting_risk = Column(Float, default=0.0)
    crowd_risk = Column(Float, default=0.0)
    isolation_risk = Column(Float, default=0.0)
    liquor_risk = Column(Float, default=0.0)
    bar_risk = Column(Float, default=0.0)
    road_risk = Column(Float, default=0.0)
    emergency_bonus = Column(Float, default=0.0)
    
    final_safety_score = Column(Float, default=0.0, index=True)
    safety_level = Column(Text, index=True)

    road = relationship("Road", back_populates="feature")
