#!/usr/bin/env python3
"""
Setup script for SurfeSpotVelger
Dette scriptet setter opp databasen og initial data
"""
import sys
import os

# Legg til backend directory til Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.database import create_tables
from backend.setup_data import setup_surf_spots

def main():
    """Kjør full setup"""
    print("🏄‍♂️ Setter opp SurfeSpotVelger...")
    
    # Opprett data directory
    os.makedirs('data', exist_ok=True)
    os.makedirs('ml', exist_ok=True)
    
    print("📁 Oppretter database...")
    create_tables()
    
    print("🏖️  Legger til surf spots...")
    setup_surf_spots()
    
    print("✅ Setup komplett!")
    print("\nFor å starte applikasjonen:")
    print("1. cd backend")
    print("2. python main.py")
    print("3. Åpne http://localhost:8000 i nettleseren")
    
    print("\nTips:")
    print("- Logg minst 20-30 økter før du trener ML-modellen")
    print("- Baseline-anbefalinger fungerer fra dag 1")
    print("- Husk å oppdatere epost-adressen i weather_service.py")

if __name__ == "__main__":
    main()
