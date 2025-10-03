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

try:
    from database import get_db, create_tables, SurfSession, SurfSpot
    from hybrid_surf_service import HybridSurfService, calculate_wind_offshore, calculate_swell_component, calculate_surf_score
    from surf_recommender import SurfRecommender
except ImportError:
    from .database import get_db, create_tables, SurfSession, SurfSpot
    from .hybrid_surf_service import HybridSurfService, calculate_wind_offshore, calculate_swell_component, calculate_surf_score
    from .surf_recommender import SurfRecommender

app = FastAPI(title="SurfeSpotVelger API", version="1.0.0")

# Mount static files for frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Initialize hybrid surf service
surf_service = HybridSurfService()

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
    wave_period: Optional[float]
    wave_direction: Optional[float]
    wind_speed: Optional[float]
    wind_direction: Optional[float]
    offshore_wind: Optional[bool]
    water_temperature: Optional[float]
    air_temperature: Optional[float]
    humidity: Optional[float]
    pressure: Optional[float]
    surf_score: Optional[float]
    data_sources: Optional[str]
    created_at: datetime

class SurfSpotResponse(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float
    orientation: float
    description: Optional[str]

class SurfSpotCreate(BaseModel):
    name: str
    latitude: float
    longitude: float
    orientation: float
    description: Optional[str] = ""

class SurfSpotUpdate(BaseModel):
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    orientation: Optional[float] = None
    description: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    create_tables()

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main frontend page"""
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/api/spots", response_model=List[SurfSpotResponse])
async def get_spots(db: Session = Depends(get_db)):
    """Hent alle surf spots"""
    spots = db.query(SurfSpot).all()
    return spots

@app.post("/api/spots", response_model=SurfSpotResponse)
async def create_spot(spot_data: SurfSpotCreate, db: Session = Depends(get_db)):
    """Opprett ny surf spot"""
    # Sjekk om spot med samme navn allerede eksisterer
    existing_spot = db.query(SurfSpot).filter(SurfSpot.name == spot_data.name).first()
    if existing_spot:
        raise HTTPException(status_code=400, detail=f"Spot med navn '{spot_data.name}' eksisterer allerede")
    
    # Opprett ny spot
    new_spot = SurfSpot(
        name=spot_data.name,
        latitude=spot_data.latitude,
        longitude=spot_data.longitude,
        orientation=spot_data.orientation,
        description=spot_data.description
    )
    
    db.add(new_spot)
    db.commit()
    db.refresh(new_spot)
    
    return new_spot

@app.get("/api/spots/{spot_id}", response_model=SurfSpotResponse)
async def get_spot(spot_id: int, db: Session = Depends(get_db)):
    """Hent en spesifikk surf spot"""
    spot = db.query(SurfSpot).filter(SurfSpot.id == spot_id).first()
    if not spot:
        raise HTTPException(status_code=404, detail="Spot ikke funnet")
    return spot

@app.put("/api/spots/{spot_id}", response_model=SurfSpotResponse)
async def update_spot(spot_id: int, spot_data: SurfSpotUpdate, db: Session = Depends(get_db)):
    """Oppdater en surf spot"""
    spot = db.query(SurfSpot).filter(SurfSpot.id == spot_id).first()
    if not spot:
        raise HTTPException(status_code=404, detail="Spot ikke funnet")
    
    # Oppdater kun felter som er oppgitt
    if spot_data.name is not None:
        # Sjekk om nytt navn allerede eksisterer (hvis det er endret)
        if spot_data.name != spot.name:
            existing_spot = db.query(SurfSpot).filter(SurfSpot.name == spot_data.name).first()
            if existing_spot:
                raise HTTPException(status_code=400, detail=f"Spot med navn '{spot_data.name}' eksisterer allerede")
        spot.name = spot_data.name
    
    if spot_data.latitude is not None:
        spot.latitude = spot_data.latitude
    if spot_data.longitude is not None:
        spot.longitude = spot_data.longitude
    if spot_data.orientation is not None:
        spot.orientation = spot_data.orientation
    if spot_data.description is not None:
        spot.description = spot_data.description
    
    db.commit()
    db.refresh(spot)
    return spot

@app.delete("/api/spots/{spot_id}")
async def delete_spot(spot_id: int, db: Session = Depends(get_db)):
    """Slett en surf spot"""
    spot = db.query(SurfSpot).filter(SurfSpot.id == spot_id).first()
    if not spot:
        raise HTTPException(status_code=404, detail="Spot ikke funnet")
    
    # Sjekk om spot har tilknyttede økter
    sessions_count = db.query(SurfSession).filter(SurfSession.spot_id == spot_id).count()
    if sessions_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Kan ikke slette spot som har {sessions_count} tilknyttede økter. Slett øktene først."
        )
    
    db.delete(spot)
    db.commit()
    return {"message": f"Spot '{spot.name}' slettet"}

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
    
    # Hent komplett surf data fra hybrid service
    surf_data = surf_service.get_complete_surf_data(
        spot.latitude,
        spot.longitude,
        session_data.date_time
    )
    
    if surf_data:
        # Værdata
        session.air_temperature = surf_data.get('air_temperature')
        session.wind_speed = surf_data.get('wind_speed')
        session.wind_direction = surf_data.get('wind_direction')
        session.wind_gust = surf_data.get('wind_gust')
        session.precipitation = surf_data.get('precipitation')
        session.humidity = surf_data.get('humidity')
        session.pressure = surf_data.get('pressure')
        
        # Bølgedata
        session.wave_height = surf_data.get('wave_height')
        session.wave_period = surf_data.get('wave_period')
        session.wave_direction = surf_data.get('wave_direction')
        session.water_temperature = surf_data.get('water_temperature')
        
        # Tidevann data
        session.tide_level = surf_data.get('tide_height')
        session.tide_trend = surf_data.get('tide_trend')
        
        # Metadata
        session.data_sources = ', '.join(surf_data.get('data_sources', []))
        session.yr_api_timestamp = datetime.utcnow()
        
        # Beregn offshore vind
        if surf_data.get('wind_direction') is not None:
            session.offshore_wind = calculate_wind_offshore(
                surf_data['wind_direction'], 
                spot.orientation
            )
        
        # Beregn swell component
        if surf_data.get('wave_direction') is not None and surf_data.get('wave_height') is not None:
            session.swell_component = calculate_swell_component(
                surf_data['wave_height'],
                surf_data['wave_direction'],
                spot.orientation
            )
            
            # Beregn vinkel-forskjell
            angle_diff = abs(surf_data['wave_direction'] - spot.orientation)
            if angle_diff > 180:
                angle_diff = 360 - angle_diff
            session.swell_angle_difference = angle_diff
        
        # Beregn surf score
        if all(surf_data.get(key) is not None for key in ['wave_height', 'wave_period', 'wind_speed', 'wind_direction']):
            session.surf_score = calculate_surf_score(
                surf_data['wave_height'],
                surf_data['wave_period'],
                surf_data['wind_speed'],
                surf_data['wind_direction'],
                spot.orientation
            )
    
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

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: int, db: Session = Depends(get_db)):
    """Slett en surf-økt"""
    session = db.query(SurfSession).filter(SurfSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session ikke funnet")
    
    db.delete(session)
    db.commit()
    return {"message": "Session slettet"}

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


# Surf Recommendation Endpoints
@app.get("/api/recommendations")
async def get_surf_recommendations(
    date: Optional[str] = None,
    max_spots: int = 5,
    db: Session = Depends(get_db)
):
    """
    Få surf spot anbefalinger for en gitt dato
    """
    try:
        # Parse dato eller bruk i dag
        if date:
            target_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
        else:
            target_date = datetime.now()
        
        # Lag recommender instans
        recommender = SurfRecommender()
        
        # Få anbefalinger
        recommendations = recommender.get_spot_recommendations(target_date, max_spots)
        
        # Lukk recommender
        recommender.close()
        
        return {
            "date": target_date.isoformat(),
            "recommendations": recommendations,
            "total_spots": len(recommendations)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feil ved henting av anbefalinger: {str(e)}")


@app.get("/api/recommendations/{spot_name}/performance")
async def get_spot_performance(spot_name: str, db: Session = Depends(get_db)):
    """
    Få historisk ytelse for en spesifikk surf spot
    """
    try:
        recommender = SurfRecommender()
        performance = recommender.get_historical_performance(spot_name)
        recommender.close()
        
        return performance
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feil ved henting av spot ytelse: {str(e)}")


@app.get("/api/recommendations/compare")
async def compare_spots(
    date: Optional[str] = None,
    spots: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Sammenlign flere surf spots for en gitt dato
    """
    try:
        # Parse dato
        if date:
            target_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
        else:
            target_date = datetime.now()
        
        # Parse spots (comma-separated)
        if spots:
            spot_names = [name.strip() for name in spots.split(',')]
        else:
            spot_names = None
        
        recommender = SurfRecommender()
        
        if spot_names:
            # Sammenlign spesifikke spots
            all_spots = db.query(SurfSpot).filter(SurfSpot.name.in_(spot_names)).all()
            if len(all_spots) != len(spot_names):
                missing = set(spot_names) - {spot.name for spot in all_spots}
                raise HTTPException(status_code=404, detail=f"Spots ikke funnet: {missing}")
            
            recommendations = []
            for spot in all_spots:
                conditions = recommender._simulate_surf_conditions(spot, target_date)
                surf_score = recommender._calculate_surf_score(conditions, spot)
                
                recommendations.append({
                    'spot_name': spot.name,
                    'coordinates': (spot.latitude, spot.longitude),
                    'surf_score': surf_score,
                    'surf_conditions': conditions,
                    'historical_performance': recommender.get_historical_performance(spot.name)
                })
        else:
            # Få alle anbefalinger
            recommendations = recommender.get_spot_recommendations(target_date, 10)
        
        recommender.close()
        
        return {
            "date": target_date.isoformat(),
            "comparison": recommendations,
            "total_spots": len(recommendations)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feil ved sammenligning av spots: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    import os
    # Change to project root directory
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    uvicorn.run(app, host="0.0.0.0", port=8000)
