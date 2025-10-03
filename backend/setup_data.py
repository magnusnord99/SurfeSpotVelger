"""
Script for å sette opp initial data - surf spots i Stavanger-området
"""
from database import create_tables, SessionLocal, SurfSpot

def setup_surf_spots():
    """Legg inn kjente surf spots i Stavanger-området"""
    db = SessionLocal()
    
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
        },
        {
            "name": "Sele",
            "latitude": 58.7333,
            "longitude": 5.4500,
            "orientation": 280,  # vest-nordvest
            "description": "Reef break, krever riktig swell og tidevann"
        },
        {
            "name": "Kvassheim",
            "latitude": 58.7833,
            "longitude": 5.5167,
            "orientation": 270,  # vest
            "description": "Beach break, funker på de fleste forhold"
        },
        {
            "name": "Point Perfect",
            "latitude": 58.8000,
            "longitude": 5.5000,
            "orientation": 275,  # vest
            "description": "Point break, krever spesifikke forhold"
        }
    ]
    
    # Sjekk om spots allerede eksisterer
    existing_spots = db.query(SurfSpot).all()
    if existing_spots:
        print(f"Surf spots finnes allerede i databasen ({len(existing_spots)} spots)")
        # Sjekk om nye spots må legges til
        existing_names = [spot.name for spot in existing_spots]
        new_spots = [spot for spot in spots if spot["name"] not in existing_names]
        
        if new_spots:
            print(f"Legger til {len(new_spots)} nye spots: {[spot['name'] for spot in new_spots]}")
            for spot_data in new_spots:
                spot = SurfSpot(**spot_data)
                db.add(spot)
            db.commit()
        else:
            print("Alle spots finnes allerede")
    else:
        # Legg til alle spots hvis databasen er tom
        for spot_data in spots:
            spot = SurfSpot(**spot_data)
            db.add(spot)
        db.commit()
        print(f"Lagt til {len(spots)} surf spots i databasen")
    
    db.close()

if __name__ == "__main__":
    create_tables()
    setup_surf_spots()
    print("Database setup komplett!")
