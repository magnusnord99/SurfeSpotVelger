from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class SurfSpot(Base):
    """Surf spots i Stavanger-området"""
    __tablename__ = "surf_spots"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)  # f.eks "Bore", "Orre", "Hellestø"
    latitude = Column(Float)
    longitude = Column(Float)
    orientation = Column(Float)  # spot-orientering i grader (for swell-beregning)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class SurfSession(Base):
    """Hver surf-økt med rating og værdata"""
    __tablename__ = "surf_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Bruker-input
    spot_id = Column(Integer, index=True)  # referanse til SurfSpot
    date_time = Column(DateTime, index=True)  # når økta startet
    duration_minutes = Column(Integer, nullable=True)  # lengde på økt
    rating = Column(Integer)  # 1-5 hvor bra det var
    board_type = Column(String, nullable=True)  # "longboard", "shortboard", etc
    notes = Column(Text, nullable=True)  # fritekst-notater
    
    # Værdata fra YR (hentet automatisk)
    wave_height = Column(Float, nullable=True)  # signifikant bølgehøyde (m)
    wave_period = Column(Float, nullable=True)  # peak periode (s)
    wave_direction = Column(Float, nullable=True)  # bølgeretning (grader)
    wind_speed = Column(Float, nullable=True)  # vindstyrke (m/s)
    wind_direction = Column(Float, nullable=True)  # vindretning (grader)
    wind_gust = Column(Float, nullable=True)  # vindkast (m/s)
    air_temperature = Column(Float, nullable=True)  # lufttemperatur (C)
    water_temperature = Column(Float, nullable=True)  # vanntemperatur (C)
    precipitation = Column(Float, nullable=True)  # nedbør (mm)
    humidity = Column(Float, nullable=True)  # luftfuktighet (%)
    pressure = Column(Float, nullable=True)  # lufttrykk (hPa)
    
    # Tidevann
    tide_level = Column(Float, nullable=True)  # tidevannsnivå (m)
    tide_trend = Column(String, nullable=True)  # "rising", "falling", "high", "low"
    
    # Avledede features (beregnes automatisk)
    offshore_wind = Column(Boolean, nullable=True)  # True hvis vind er offshore
    swell_angle_difference = Column(Float, nullable=True)  # forskjell mellom swell og spot-orientering
    swell_component = Column(Float, nullable=True)  # bølgehøyde * cos(vinkel-diff)
    season = Column(String, nullable=True)  # "winter", "spring", "summer", "autumn"
    weekday = Column(Integer, nullable=True)  # 0=mandag, 6=søndag
    time_of_day = Column(String, nullable=True)  # "morning", "afternoon", "evening"
    
    # Metadata
    forecast_lead_time = Column(Integer, nullable=True)  # hvor mange timer før økta ble varselet hentet
    yr_api_timestamp = Column(DateTime, nullable=True)  # når værdata ble hentet fra YR
    data_sources = Column(String, nullable=True)  # hvilke APIer som ble brukt (yr, stormglass, etc)
    surf_score = Column(Float, nullable=True)  # beregnet surf score 0-10
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Database setup
DATABASE_URL = "sqlite:///./data/surfespotvelger.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """Opprett alle tabeller i databasen"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency for å få database-session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
