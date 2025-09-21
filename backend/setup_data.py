"""
Script for å sette opp initial data - surf spots i Stavanger-området
"""
from database import create_tables, SessionLocal, SurfSpot

def setup_surf_spots():
    """Legg inn kjente surf spots i Stavanger-området"""
    db = SessionLocal()
    
    # Sjekk om spots allerede eksisterer
    if db.query(SurfSpot).count() > 0:
        print("Surf spots finnes allerede i databasen")
        db.close()
        return
    
    spots = [
        {
            "name": "Bore",
            "latitude": 58.8839,
            "longitude": 5.5528,
            "orientation": 270,  # vest-orientert
            "description": "Populær beach break, funker på de fleste swell-retninger"
        },
        {
            "name": "Orre",
            "latitude": 58.8167,
            "longitude": 5.4833,
            "orientation": 285,  # vest-nordvest
            "description": "Eksponert beach break, trenger større swell"
        },
        {
            "name": "Hellestø",
            "latitude": 58.9333,
            "longitude": 5.6167,
            "orientation": 260,  # vest-sørvest
            "description": "Mer beskyttet, funker på mindre swell"
        },
        {
            "name": "Sola Strand",
            "latitude": 58.8667,
            "longitude": 5.5833,
            "orientation": 275,  # vest
            "description": "Lang sandstrand med flere peaks"
        },
        {
            "name": "Reve",
            "latitude": 58.7167,
            "longitude": 5.4333,
            "orientation": 290,  # vest-nordvest
            "description": "Reef break, krever større swell og riktig tidevann"
        },
        {
            "name": "Sirevåg",
            "latitude": 58.7167,
            "longitude": 5.4000,
            "orientation": 300,  # nordvest
            "description": "Beskyttet bay, funker på nordlige swell"
        }
    ]
    
    for spot_data in spots:
        spot = SurfSpot(**spot_data)
        db.add(spot)
    
    db.commit()
    db.close()
    print(f"Lagt til {len(spots)} surf spots i databasen")

if __name__ == "__main__":
    create_tables()
    setup_surf_spots()
    print("Database setup komplett!")
