from sqlalchemy import Column, Integer, BigInteger, Float, Text
from geoalchemy2 import Geometry
from backend.app.database import Base

class POI(Base):
    __tablename__ = "pois"

    id = Column(Integer, primary_key=True, index=True)
    osm_id = Column(BigInteger, index=True)
    name = Column(Text)
    category = Column(Text, nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    geometry = Column(Geometry("POINT", srid=4326))
