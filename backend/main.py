"""
FastAPI backend for SurfeSpotVelger
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

from database import get_db, create_tables, SurfSession, SurfSpot
from weather_service import YRWeatherService, OceanForecastService, calculate_wind_offshore, calculate_swell_component

app = FastAPI(title="SurfeSpotVelger API", version="1.0.0")

# Mount static files for frontend
app.mount("/static", StaticFiles(directory="../frontend"), name="static")

# Initialize weather services
weather_service = YRWeatherService()
ocean_service = OceanForecastService()

# Pydantic models for API
class SurfSessionCreate(BaseModel):
    spot_id: int
    date_time: datetime
    duration_minutes: Optional[int] = None
    rating: int  # 1-5
    board_type: Optional[str] = None
    notes: Optional[str] = None

class SurfSessionResponse(BaseModel):
    id: int
    spot_id: int
    date_time: datetime
    rating: int
    board_type: Optional[str]
    notes: Optional[str]
    wave_height: Optional[float]
    wind_speed: Optional[float]
    wind_direction: Optional[float]
    offshore_wind: Optional[bool]
    created_at: datetime

class SurfSpotResponse(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float
    orientation: float
    description: Optional[str]

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    create_tables()

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main frontend page"""
    with open("../frontend/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/api/spots", response_model=List[SurfSpotResponse])
async def get_spots(db: Session = Depends(get_db)):
    """Hent alle surf spots"""
    spots = db.query(SurfSpot).all()
    return spots

@app.post("/api/sessions", response_model=SurfSessionResponse)
async def create_session(session_data: SurfSessionCreate, db: Session = Depends(get_db)):
    """
    Opprett ny surf-økt og hent automatisk værdata
    """
    # Hent spot info
    spot = db.query(SurfSpot).filter(SurfSpot.id == session_data.spot_id).first()
    if not spot:
        raise HTTPException(status_code=404, detail="Spot ikke funnet")
    
    # Opprett session
    session = SurfSession(
        spot_id=session_data.spot_id,
        date_time=session_data.date_time,
        duration_minutes=session_data.duration_minutes,
        rating=session_data.rating,
        board_type=session_data.board_type,
        notes=session_data.notes
    )
    
    # Hent værdata fra YR
    weather_data = weather_service.get_weather_data(
        spot.latitude, 
        spot.longitude, 
        session_data.date_time
    )
    
    if weather_data:
        session.air_temperature = weather_data.get('air_temperature')
        session.wind_speed = weather_data.get('wind_speed')
        session.wind_direction = weather_data.get('wind_direction')
        session.wind_gust = weather_data.get('wind_gust')
        session.precipitation = weather_data.get('precipitation')
        session.forecast_lead_time = int(weather_data.get('lead_time_hours', 0))
        session.yr_api_timestamp = datetime.utcnow()
        
        # Beregn offshore vind
        if weather_data.get('wind_direction') is not None:
            session.offshore_wind = calculate_wind_offshore(
                weather_data['wind_direction'], 
                spot.orientation
            )
    
    # Hent bølgedata
    wave_data = ocean_service.get_wave_data(
        spot.latitude,
        spot.longitude, 
        session_data.date_time
    )
    
    if wave_data:
        session.wave_height = wave_data.get('wave_height')
        session.wave_period = wave_data.get('wave_period') 
        session.wave_direction = wave_data.get('wave_direction')
        session.water_temperature = wave_data.get('water_temperature')
        
        # Beregn swell component
        if wave_data.get('wave_direction') is not None and wave_data.get('wave_height') is not None:
            session.swell_component = calculate_swell_component(
                wave_data['wave_height'],
                wave_data['wave_direction'],
                spot.orientation
            )
            
            # Beregn vinkel-forskjell
            angle_diff = abs(wave_data['wave_direction'] - spot.orientation)
            if angle_diff > 180:
                angle_diff = 360 - angle_diff
            session.swell_angle_difference = angle_diff
    
    # Beregn avledede features
    session.season = _get_season(session_data.date_time)
    session.weekday = session_data.date_time.weekday()
    session.time_of_day = _get_time_of_day(session_data.date_time)
    
    # Lagre i database
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return session

@app.get("/api/sessions", response_model=List[SurfSessionResponse])
async def get_sessions(db: Session = Depends(get_db)):
    """Hent alle surf-økter"""
    sessions = db.query(SurfSession).order_by(SurfSession.date_time.desc()).all()
    return sessions

@app.get("/api/sessions/{session_id}", response_model=SurfSessionResponse)
async def get_session(session_id: int, db: Session = Depends(get_db)):
    """Hent en spesifikk surf-økt"""
    session = db.query(SurfSession).filter(SurfSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session ikke funnet")
    return session

def _get_season(date: datetime) -> str:
    """Bestem årstid basert på dato"""
    month = date.month
    if month in [12, 1, 2]:
        return "winter"
    elif month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "summer"
    else:
        return "autumn"

def _get_time_of_day(date: datetime) -> str:
    """Bestem tid på dagen"""
    hour = date.hour
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 18:
        return "afternoon"
    else:
        return "evening"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
