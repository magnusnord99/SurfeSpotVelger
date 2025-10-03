#!/usr/bin/env python3
"""
Basic setup script for SurfeSpotVelger (uten ML-dependencies)
"""
import sys
import os

# Legg til backend directory til Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.database import create_tables
from backend.setup_data import setup_surf_spots

def main():
    """Kjør basic setup"""
    print("🏄‍♂️ Setter opp SurfeSpotVelger (basic versjon)...")
    
    # Opprett data directory
    os.makedirs('data', exist_ok=True)
    
    print("📁 Oppretter database...")
    create_tables()
    
    print("🏖️  Legger til surf spots...")
    setup_surf_spots()
    
    print("✅ Setup komplett!")
    print("\nFor å starte applikasjonen:")
    print("1. source venv/bin/activate")
    print("2. cd backend")
    print("3. python3 main.py")
    print("4. Åpne http://localhost:8000 i nettleseren")
    
    print("\nTips:")
    print("- Baseline-anbefalinger fungerer uten ML-pakker")
    print("- Husk å oppdatere epost-adressen i weather_service.py")
    print("- Installer ML-pakker senere for avanserte features")

if __name__ == "__main__":
    main()
