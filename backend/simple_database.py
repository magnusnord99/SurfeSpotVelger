"""
Enkel database implementasjon med SQLite (uten SQLAlchemy for Python 3.13 kompatibilitet)
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

DATABASE_PATH = "../data/surfespotvelger.db"

def get_connection():
    """Få database connection"""
    return sqlite3.connect(DATABASE_PATH)

def create_tables():
    """Opprett database tabeller"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Surf spots tabell
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS surf_spots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            orientation REAL NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Surf sessions tabell
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS surf_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            spot_id INTEGER NOT NULL,
            date_time TIMESTAMP NOT NULL,
            duration_minutes INTEGER,
            rating INTEGER NOT NULL,
            board_type TEXT,
            notes TEXT,
            
            -- Værdata
            wave_height REAL,
            wave_period REAL,
            wave_direction REAL,
            wind_speed REAL,
            wind_direction REAL,
            wind_gust REAL,
            air_temperature REAL,
            water_temperature REAL,
            precipitation REAL,
            
            -- Tidevann
            tide_level REAL,
            tide_trend TEXT,
            
            -- Avledede features
            offshore_wind INTEGER,
            swell_angle_difference REAL,
            swell_component REAL,
            season TEXT,
            weekday INTEGER,
            time_of_day TEXT,
            
            -- Metadata
            forecast_lead_time INTEGER,
            yr_api_timestamp TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (spot_id) REFERENCES surf_spots (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def setup_surf_spots():
    """Legg inn surf spots"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Sjekk om spots allerede finnes
    cursor.execute("SELECT COUNT(*) FROM surf_spots")
    if cursor.fetchone()[0] > 0:
        print("Surf spots finnes allerede")
        conn.close()
        return
    
    spots = [
        ("Bore", 58.8839, 5.5528, 270, "Populær beach break, funker på de fleste swell-retninger"),
        ("Orre", 58.8167, 5.4833, 285, "Eksponert beach break, trenger større swell"),
        ("Hellestø", 58.9333, 5.6167, 260, "Mer beskyttet, funker på mindre swell"),
        ("Sola Strand", 58.8667, 5.5833, 275, "Lang sandstrand med flere peaks"),
        ("Reve", 58.7167, 5.4333, 290, "Reef break, krever større swell og riktig tidevann"),
        ("Sirevåg", 58.7167, 5.4000, 300, "Beskyttet bay, funker på nordlige swell")
    ]
    
    cursor.executemany('''
        INSERT INTO surf_spots (name, latitude, longitude, orientation, description)
        VALUES (?, ?, ?, ?, ?)
    ''', spots)
    
    conn.commit()
    conn.close()
    print(f"Lagt til {len(spots)} surf spots")

def get_all_spots() -> List[Dict[str, Any]]:
    """Hent alle surf spots"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM surf_spots ORDER BY name")
    rows = cursor.fetchall()
    
    spots = []
    for row in rows:
        spots.append({
            'id': row[0],
            'name': row[1],
            'latitude': row[2],
            'longitude': row[3],
            'orientation': row[4],
            'description': row[5],
            'created_at': row[6]
        })
    
    conn.close()
    return spots

def get_spot_by_id(spot_id: int) -> Optional[Dict[str, Any]]:
    """Hent spot by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM surf_spots WHERE id = ?", (spot_id,))
    row = cursor.fetchone()
    
    if row:
        spot = {
            'id': row[0],
            'name': row[1],
            'latitude': row[2],
            'longitude': row[3],
            'orientation': row[4],
            'description': row[5],
            'created_at': row[6]
        }
        conn.close()
        return spot
    
    conn.close()
    return None

def create_surf_session(session_data: Dict[str, Any]) -> Dict[str, Any]:
    """Opprett ny surf session"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Insert session
    cursor.execute('''
        INSERT INTO surf_sessions (
            spot_id, date_time, duration_minutes, rating, board_type, notes,
            wave_height, wave_period, wave_direction, wind_speed, wind_direction,
            wind_gust, air_temperature, water_temperature, precipitation,
            offshore_wind, swell_angle_difference, swell_component,
            season, weekday, time_of_day, forecast_lead_time, yr_api_timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        session_data.get('spot_id'),
        session_data.get('date_time'),
        session_data.get('duration_minutes'),
        session_data.get('rating'),
        session_data.get('board_type'),
        session_data.get('notes'),
        session_data.get('wave_height'),
        session_data.get('wave_period'),
        session_data.get('wave_direction'),
        session_data.get('wind_speed'),
        session_data.get('wind_direction'),
        session_data.get('wind_gust'),
        session_data.get('air_temperature'),
        session_data.get('water_temperature'),
        session_data.get('precipitation'),
        session_data.get('offshore_wind'),
        session_data.get('swell_angle_difference'),
        session_data.get('swell_component'),
        session_data.get('season'),
        session_data.get('weekday'),
        session_data.get('time_of_day'),
        session_data.get('forecast_lead_time'),
        session_data.get('yr_api_timestamp')
    ))
    
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # Return created session
    return get_session_by_id(session_id)

def get_session_by_id(session_id: int) -> Optional[Dict[str, Any]]:
    """Hent session by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM surf_sessions WHERE id = ?", (session_id,))
    row = cursor.fetchone()
    
    if row:
        session = {
            'id': row[0],
            'spot_id': row[1],
            'date_time': row[2],
            'duration_minutes': row[3],
            'rating': row[4],
            'board_type': row[5],
            'notes': row[6],
            'wave_height': row[7],
            'wave_period': row[8],
            'wave_direction': row[9],
            'wind_speed': row[10],
            'wind_direction': row[11],
            'wind_gust': row[12],
            'air_temperature': row[13],
            'water_temperature': row[14],
            'precipitation': row[15],
            'tide_level': row[16],
            'tide_trend': row[17],
            'offshore_wind': bool(row[18]) if row[18] is not None else None,
            'swell_angle_difference': row[19],
            'swell_component': row[20],
            'season': row[21],
            'weekday': row[22],
            'time_of_day': row[23],
            'forecast_lead_time': row[24],
            'yr_api_timestamp': row[25],
            'created_at': row[26],
            'updated_at': row[27]
        }
        conn.close()
        return session
    
    conn.close()
    return None

def get_all_sessions() -> List[Dict[str, Any]]:
    """Hent alle sessions"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM surf_sessions ORDER BY date_time DESC")
    rows = cursor.fetchall()
    
    sessions = []
    for row in rows:
        sessions.append({
            'id': row[0],
            'spot_id': row[1],
            'date_time': row[2],
            'duration_minutes': row[3],
            'rating': row[4],
            'board_type': row[5],
            'notes': row[6],
            'wave_height': row[7],
            'wind_speed': row[10],
            'wind_direction': row[11],
            'offshore_wind': bool(row[18]) if row[18] is not None else None,
            'created_at': row[26]
        })
    
    conn.close()
    return sessions

if __name__ == "__main__":
    import os
    os.makedirs("../data", exist_ok=True)
    create_tables()
    setup_surf_spots()
    print("Database setup komplett!")
