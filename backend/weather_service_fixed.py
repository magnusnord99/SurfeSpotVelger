"""
Fikset versjon av weather service med timezone-håndtering
"""
import requests
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
import math

class YRWeatherService:
    """Service for å hente værdata fra YR API"""
    
    BASE_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
    
    def __init__(self):
        # YR krever User-Agent header
        self.headers = {
            'User-Agent': 'SurfeSpotVelger/1.0 (kontakt@example.com)'  # Bytt ut med din epost
        }
    
    def get_weather_data(self, latitude: float, longitude: float, target_time: datetime) -> Optional[Dict[str, Any]]:
        """
        Hent værdata for en bestemt posisjon og tid
        """
        try:
            # YR API parametere
            params = {
                'lat': latitude,
                'lon': longitude
            }
            
            response = requests.get(self.BASE_URL, params=params, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            
            # Finn nærmeste tidspunkt i forecast
            weather_data = self._extract_weather_for_time(data, target_time)
            
            return weather_data
            
        except Exception as e:
            print(f"Feil ved henting av værdata: {e}")
            return None
    
    def _extract_weather_for_time(self, yr_data: Dict, target_time: datetime) -> Dict[str, Any]:
        """
        Finn værdata som matcher nærmest target_time
        """
        timeseries = yr_data.get('properties', {}).get('timeseries', [])
        
        if not timeseries:
            return {}
        
        # Konverter target_time til UTC hvis den er naive
        if target_time.tzinfo is None:
            target_time_utc = target_time.replace(tzinfo=timezone.utc)
        else:
            target_time_utc = target_time.astimezone(timezone.utc)
        
        # Finn nærmeste tidspunkt
        best_match = None
        min_time_diff = float('inf')
        
        for entry in timeseries:
            try:
                entry_time = datetime.fromisoformat(entry['time'].replace('Z', '+00:00'))
                time_diff = abs((entry_time - target_time_utc).total_seconds())
                
                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    best_match = entry
            except Exception as e:
                print(f"Feil ved parsing av tid: {e}")
                continue
        
        if not best_match:
            return {}
        
        # Ekstraher relevante data
        instant_data = best_match.get('data', {}).get('instant', {}).get('details', {})
        
        # Hent også 1-time data hvis tilgjengelig (for nedbør)
        next_1h = best_match.get('data', {}).get('next_1_hours', {})
        precipitation = 0.0
        if next_1h:
            precipitation = next_1h.get('details', {}).get('precipitation_amount', 0.0)
        
        return {
            'air_temperature': instant_data.get('air_temperature'),
            'wind_speed': instant_data.get('wind_speed'), 
            'wind_direction': instant_data.get('wind_from_direction'),
            'wind_gust': instant_data.get('wind_speed_of_gust'),
            'precipitation': precipitation,
            'timestamp': best_match.get('time'),
            'lead_time_hours': min_time_diff / 3600  # hvor mange timer fra prognose til target_time
        }

class OceanForecastService:
    """Service for å hente bølgedata fra met.no oceanforecast"""
    
    BASE_URL = "https://api.met.no/weatherapi/oceanforecast/2.0/complete"
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'SurfeSpotVelger/1.0 (kontakt@example.com)'
        }
    
    def get_wave_data(self, latitude: float, longitude: float, target_time: datetime) -> Optional[Dict[str, Any]]:
        """
        Hent bølgedata for en bestemt posisjon og tid
        """
        try:
            params = {
                'lat': latitude,
                'lon': longitude
            }
            
            response = requests.get(self.BASE_URL, params=params, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            wave_data = self._extract_wave_for_time(data, target_time)
            
            return wave_data
            
        except Exception as e:
            print(f"Feil ved henting av bølgedata: {e}")
            return None
    
    def _extract_wave_for_time(self, ocean_data: Dict, target_time: datetime) -> Dict[str, Any]:
        """Ekstraher bølgedata for nærmeste tidspunkt"""
        timeseries = ocean_data.get('properties', {}).get('timeseries', [])
        
        if not timeseries:
            return {}
        
        # Konverter target_time til UTC hvis den er naive
        if target_time.tzinfo is None:
            target_time_utc = target_time.replace(tzinfo=timezone.utc)
        else:
            target_time_utc = target_time.astimezone(timezone.utc)
        
        # Finn nærmeste tidspunkt
        best_match = None
        min_time_diff = float('inf')
        
        for entry in timeseries:
            try:
                entry_time = datetime.fromisoformat(entry['time'].replace('Z', '+00:00'))
                time_diff = abs((entry_time - target_time_utc).total_seconds())
                
                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    best_match = entry
            except Exception as e:
                print(f"Feil ved parsing av bølge-tid: {e}")
                continue
        
        if not best_match:
            return {}
        
        instant_data = best_match.get('data', {}).get('instant', {}).get('details', {})
        
        # Debug: print tilgjengelige data
        print(f"Bølgedata tilgjengelig: {list(instant_data.keys())}")
        
        return {
            'wave_height': instant_data.get('sea_surface_wave_height'),  # Bruker riktig felt
            'wave_period': instant_data.get('sea_surface_wave_period_at_variance_spectral_density_maximum'),
            'wave_direction': instant_data.get('sea_surface_wave_from_direction'),
            'water_temperature': instant_data.get('sea_water_temperature'),
            'timestamp': best_match.get('time')
        }

def calculate_wind_offshore(wind_direction: float, spot_orientation: float) -> bool:
    """
    Beregn om vinden er offshore (fra land mot hav)
    """
    if wind_direction is None or spot_orientation is None:
        return False
    
    # Beregn vinkel-forskjell
    angle_diff = abs(wind_direction - spot_orientation)
    
    # Normaliser til 0-180 grader
    if angle_diff > 180:
        angle_diff = 360 - angle_diff
    
    # Offshore hvis vind kommer fra land-siden (innenfor ~90 grader)
    return angle_diff <= 90

def calculate_swell_component(wave_height: float, wave_direction: float, spot_orientation: float) -> float:
    """
    Beregn hvor mye av swellen som treffer spot-et direkte
    """
    if None in [wave_height, wave_direction, spot_orientation]:
        return 0.0
    
    angle_diff = abs(wave_direction - spot_orientation)
    if angle_diff > 180:
        angle_diff = 360 - angle_diff
    
    # Cosinus-komponent
    angle_rad = math.radians(angle_diff)
    return wave_height * math.cos(angle_rad)
