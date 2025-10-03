"""
Enkel FastAPI backend for testing av frontend (uten SQLAlchemy)
"""
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import List, Optional
import os

from simple_database import (
    create_tables, setup_surf_spots, get_all_spots, get_spot_by_id,
    create_surf_session, get_all_sessions, get_session_by_id
)
from openweather_service import OpenWeatherMarineService, KartverketTideService, calculate_wind_offshore, calculate_swell_component

app = FastAPI(title="SurfeSpotVelger API", version="1.0.0")

# Mount static files for frontend
app.mount("/static", StaticFiles(directory="../frontend"), name="static")

# Initialize weather services
weather_service = OpenWeatherMarineService()
tide_service = KartverketTideService()

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
    created_at: str

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
    os.makedirs("../data", exist_ok=True)
    create_tables()
    setup_surf_spots()

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main frontend page"""
    try:
        with open("../frontend/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Frontend ikke funnet</h1><p>Sjekk at frontend/index.html eksisterer</p>")

@app.get("/api/spots", response_model=List[SurfSpotResponse])
async def get_spots():
    """Hent alle surf spots"""
    spots = get_all_spots()
    return spots

@app.post("/api/sessions", response_model=SurfSessionResponse)
async def create_session(session_data: SurfSessionCreate):
    """
    Opprett ny surf-økt og hent automatisk værdata
    """
    # Hent spot info
    spot = get_spot_by_id(session_data.spot_id)
    if not spot:
        raise HTTPException(status_code=404, detail="Spot ikke funnet")
    
    # Opprett session data dict
    session_dict = {
        'spot_id': session_data.spot_id,
        'date_time': session_data.date_time.isoformat(),
        'duration_minutes': session_data.duration_minutes,
        'rating': session_data.rating,
        'board_type': session_data.board_type,
        'notes': session_data.notes
    }
    
    # Hent vær og bølgedata fra OpenWeatherMap
    try:
        weather_data = weather_service.get_weather_and_wave_data(
            spot['latitude'], 
            spot['longitude'], 
            session_data.date_time
        )
        
        if weather_data:
            session_dict.update({
                'air_temperature': weather_data.get('air_temperature'),
                'wind_speed': weather_data.get('wind_speed'),
                'wind_direction': weather_data.get('wind_direction'),
                'wind_gust': weather_data.get('wind_gust'),
                'precipitation': weather_data.get('precipitation'),
                'wave_height': weather_data.get('wave_height'),
                'wave_period': weather_data.get('wave_period'),
                'wave_direction': weather_data.get('wave_direction'),
                'forecast_lead_time': int(weather_data.get('lead_time_hours', 0)),
                'yr_api_timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            # Beregn offshore vind
            if weather_data.get('wind_direction') is not None:
                session_dict['offshore_wind'] = calculate_wind_offshore(
                    weather_data['wind_direction'], 
                    spot['orientation']
                )
            
            # Beregn swell component
            if weather_data.get('wave_direction') is not None and weather_data.get('wave_height') is not None:
                session_dict['swell_component'] = calculate_swell_component(
                    weather_data['wave_height'],
                    weather_data['wave_direction'],
                    spot['orientation']
                )
                
                # Beregn vinkel-forskjell
                angle_diff = abs(weather_data['wave_direction'] - spot['orientation'])
                if angle_diff > 180:
                    angle_diff = 360 - angle_diff
                session_dict['swell_angle_difference'] = angle_diff
                
    except Exception as e:
        print(f"Feil ved henting av værdata: {e}")
    
    # Hent tidevann
    try:
        tide_data = tide_service.get_tide_data(
            spot['latitude'],
            spot['longitude'], 
            session_data.date_time
        )
        
        if tide_data:
            session_dict.update({
                'tide_level': tide_data.get('tide_level'),
                'tide_trend': tide_data.get('tide_trend')
            })
            
    except Exception as e:
        print(f"Feil ved henting av tidevann: {e}")
    
    # Beregn avledede features
    session_dict.update({
        'season': _get_season(session_data.date_time),
        'weekday': session_data.date_time.weekday(),
        'time_of_day': _get_time_of_day(session_data.date_time)
    })
    
    # Lagre i database
    created_session = create_surf_session(session_dict)
    
    return created_session

@app.get("/api/sessions", response_model=List[SurfSessionResponse])
async def get_sessions():
    """Hent alle surf-økter"""
    sessions = get_all_sessions()
    return sessions

@app.get("/api/sessions/{session_id}", response_model=SurfSessionResponse)
async def get_session(session_id: int):
    """Hent en spesifikk surf-økt"""
    session = get_session_by_id(session_id)
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
