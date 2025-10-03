"""
Stormglass API service for comprehensive surf data
Gratis tier: 10 calls/dag - perfekt for surf app!
"""
import requests
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import math

class StormglassService:
    """Service for å hente komplett surf data fra Stormglass API"""
    
    BASE_URL = "https://api.stormglass.io/v2/weather/point"
    
    def __init__(self, api_key: str = None):
        # Registrer deg på stormglass.io for gratis API key
        # Gratis tier: 10 calls/dag
        self.api_key = api_key or "81111e72-97c6-11f0-a246-0242ac130006-81111f1c-97c6-11f0-a246-0242ac130006"  # Bytt ut med din API key
        self.headers = {
            'Authorization': self.api_key
        }
    
    def get_surf_data(self, latitude: float, longitude: float, target_time: datetime) -> Optional[Dict[str, Any]]:
        """
        Hent alle surf-kritiske data fra Stormglass API
        
        Args:
            latitude: Breddegrad
            longitude: Lengdegrad
            target_time: Tidspunkt vi ønsker data for
            
        Returns:
            Dict med alle surf data eller None hvis feil
        """
        if self.api_key == "YOUR_API_KEY_HERE":
            print("⚠️  Stormglass API key ikke satt - bruker mock data")
            return self._get_mock_surf_data()
        
        try:
            # Konverter til timestamp
            timestamp = int(target_time.timestamp())
            
            # Stormglass API parametere
            params = {
                'lat': latitude,
                'lng': longitude,
                'params': ['waveHeight', 'wavePeriod', 'waveDirection', 'windSpeed', 'windDirection', 'tideHeight'],
                'source': 'sg',  # Stormglass data
                'start': timestamp,
                'end': timestamp
            }
            
            response = requests.get(self.BASE_URL, params=params, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            
            # Ekstraher surf data
            surf_data = self._extract_surf_data(data)
            
            return surf_data
            
        except Exception as e:
            print(f"Feil ved henting av Stormglass data: {e}")
            return self._get_mock_surf_data()
    
    def _extract_surf_data(self, stormglass_data: Dict) -> Dict[str, Any]:
        """Ekstraher surf-relevante data fra Stormglass response"""
        hours = stormglass_data.get('hours', [])
        
        if not hours:
            return {}
        
        # Ta første (og eneste) time
        hour_data = hours[0]
        
        # Debug: print available data
        print(f"Available Stormglass data: {list(hour_data.keys())}")
        for key, value in hour_data.items():
            if isinstance(value, dict):
                print(f"  {key}: {value}")
        
        # Ekstraher alle surf-kritiske parametere
        return {
            # Bølgedata (de viktigste!)
            'wave_height': hour_data.get('waveHeight', {}).get('sg', None),
            'wave_period': hour_data.get('wavePeriod', {}).get('sg', None),
            'wave_direction': hour_data.get('waveDirection', {}).get('sg', None),
            
            # Vinddata
            'wind_speed': hour_data.get('windSpeed', {}).get('sg', None),
            'wind_direction': hour_data.get('windDirection', {}).get('sg', None),
            
            # Tidevann
            'tide_height': hour_data.get('tideHeight', {}).get('sg', None),
            
            # Metadata
            'timestamp': hour_data.get('time'),
            'source': 'stormglass'
        }
    
    def _get_mock_surf_data(self) -> Dict[str, Any]:
        """Mock surf data for testing når API key ikke er satt"""
        return {
            # Bølgedata
            'wave_height': 1.2,
            'wave_period': 8.5,  # Dette får vi kun fra Stormglass!
            'wave_direction': 270,
            
            # Vind
            'wind_speed': 8.0,
            'wind_direction': 280,
            
            # Tidevann
            'tide_height': 1.5,
            
            # Metadata
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'source': 'stormglass_mock'
        }

def calculate_surf_score(wave_height: float, wave_period: float, wind_speed: float, 
                        wind_direction: float, spot_orientation: float) -> float:
    """
    Beregn surf score basert på alle faktorer
    
    Returns:
        Score fra 0-10 (10 = perfekt surf)
    """
    if None in [wave_height, wave_period, wind_speed, wind_direction, spot_orientation]:
        return 0.0
    
    score = 0.0
    
    # Bølgehøyde score (optimum 1-2 meter)
    if 0.8 <= wave_height <= 2.0:
        wave_height_score = 3.0
    elif 0.5 <= wave_height < 0.8:
        wave_height_score = 2.0
    elif 2.0 < wave_height <= 3.0:
        wave_height_score = 2.0
    else:
        wave_height_score = 0.5
    
    # Bølgeperiode score (optimum 8-15 sekunder)
    if 8 <= wave_period <= 15:
        wave_period_score = 3.0
    elif 6 <= wave_period < 8:
        wave_period_score = 2.0
    elif 15 < wave_period <= 20:
        wave_period_score = 2.0
    else:
        wave_period_score = 1.0
    
    # Vind score (offshore vind er best)
    is_offshore = calculate_wind_offshore(wind_direction, spot_orientation)
    if is_offshore and wind_speed <= 8:
        wind_score = 4.0
    elif not is_offshore and wind_speed <= 5:
        wind_score = 2.0
    elif wind_speed > 15:
        wind_score = 0.0
    else:
        wind_score = 1.0
    
    score = wave_height_score + wave_period_score + wind_score
    return min(score, 10.0)

def calculate_wind_offshore(wind_direction: float, spot_orientation: float) -> bool:
    """Beregn om vinden er offshore"""
    if wind_direction is None or spot_orientation is None:
        return False
    
    angle_diff = abs(wind_direction - spot_orientation)
    if angle_diff > 180:
        angle_diff = 360 - angle_diff
    
    return angle_diff <= 90

if __name__ == "__main__":
    # Test Stormglass service
    sg = StormglassService()
    
    test_time = datetime.now()
    
    print("Testing Stormglass API for surf data...")
    surf_data = sg.get_surf_data(58.8839, 5.5528, test_time)
    print(f"Surf data: {surf_data}")
    
    if surf_data and surf_data.get('source') != 'stormglass_mock':
        print("\n✅ Stormglass API fungerer! Du har nå:")
        print(f"   🌊 Bølgehøyde: {surf_data.get('wave_height')}m")
        print(f"   ⏱️  Bølgeperiode: {surf_data.get('wave_period')}s")
        print(f"   🧭 Bølgeretning: {surf_data.get('wave_direction')}°")
        print(f"   💨 Vind: {surf_data.get('wind_speed')}m/s fra {surf_data.get('wind_direction')}°")
        print(f"   🌊 Tidevann: {surf_data.get('tide_height')}m")
    else:
        print("\n⚠️  Bruker mock data - sett din API key for ekte data")
