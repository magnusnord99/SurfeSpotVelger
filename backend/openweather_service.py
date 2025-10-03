"""
OpenWeatherMap Marine Weather API service for comprehensive surf data
Gratis tier: 1000 calls/dag
"""
import requests
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import math

class OpenWeatherMarineService:
    """Service for å hente vær og bølgedata fra OpenWeatherMap Marine API"""
    
    BASE_URL = "https://api.openweathermap.org/data/3.0/onecall"
    
    def __init__(self, api_key: str = None):
        # Du må registrere deg på openweathermap.org for å få API key
        # Gratis tier gir 1000 calls/dag
        self.api_key = api_key or "4e44db6418a2d7fb6e8df550c8aa7e10"  # Bytt ut med din API key
        
    def get_weather_and_wave_data(self, latitude: float, longitude: float, target_time: datetime) -> Optional[Dict[str, Any]]:
        """
        Hent både vær og bølgedata for en bestemt posisjon og tid
        """
        if self.api_key == "DIN_API_KEY_HER":
            print("⚠️  OpenWeatherMap API key ikke satt - bruker mock data")
            return self._get_mock_data()
        
        try:
            params = {
                'lat': latitude,
                'lon': longitude,
                'appid': self.api_key,
                'units': 'metric',  # Celsius og m/s
                'exclude': 'minutely,alerts'  # Kun current, hourly og daily
            }
            
            response = requests.get(self.BASE_URL, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Finn nærmeste tidspunkt
            weather_data = self._extract_data_for_time(data, target_time)
            
            return weather_data
            
        except Exception as e:
            print(f"Feil ved henting av OpenWeatherMap data: {e}")
            return self._get_mock_data()
    
    def _extract_data_for_time(self, owm_data: Dict, target_time: datetime) -> Dict[str, Any]:
        """
        Finn værdata som matcher nærmest target_time
        """
        # Konverter target_time til UTC timestamp
        if target_time.tzinfo is None:
            target_time_utc = target_time.replace(tzinfo=timezone.utc)
        else:
            target_time_utc = target_time.astimezone(timezone.utc)
        
        target_timestamp = target_time_utc.timestamp()
        
        # Sjekk current data først
        current = owm_data.get('current', {})
        current_time = current.get('dt', 0)
        
        # Hvis target er nær current time (innen 1 time)
        if abs(current_time - target_timestamp) <= 3600:
            return self._extract_current_data(current)
        
        # Ellers, søk i hourly data
        hourly = owm_data.get('hourly', [])
        best_match = None
        min_time_diff = float('inf')
        
        for hour_data in hourly:
            hour_timestamp = hour_data.get('dt', 0)
            time_diff = abs(hour_timestamp - target_timestamp)
            
            if time_diff < min_time_diff:
                min_time_diff = time_diff
                best_match = hour_data
        
        if best_match:
            return self._extract_hourly_data(best_match)
        
        return {}
    
    def _extract_current_data(self, current_data: Dict) -> Dict[str, Any]:
        """Ekstraher data fra current weather"""
        return {
            # Vind
            'wind_speed': current_data.get('wind_speed'),
            'wind_direction': current_data.get('wind_deg'),
            'wind_gust': current_data.get('wind_gust'),
            
            # Temperatur og fuktighet
            'air_temperature': current_data.get('temp'),
            'feels_like': current_data.get('feels_like'),
            'humidity': current_data.get('humidity'),
            'pressure': current_data.get('pressure'),
            
            # Nedbør
            'precipitation': current_data.get('rain', {}).get('1h', 0),
            
            # Bølger (hvis tilgjengelig i premium)
            'wave_height': current_data.get('wave_height'),
            'wave_period': current_data.get('wave_period'),
            'wave_direction': current_data.get('wave_deg'),
            
            # Metadata
            'timestamp': datetime.fromtimestamp(current_data.get('dt', 0), tz=timezone.utc).isoformat(),
            'lead_time_hours': 0,
            'source': 'openweathermap_current'
        }
    
    def _extract_hourly_data(self, hourly_data: Dict) -> Dict[str, Any]:
        """Ekstraher data fra hourly forecast"""
        return {
            # Vind
            'wind_speed': hourly_data.get('wind_speed'),
            'wind_direction': hourly_data.get('wind_deg'),
            'wind_gust': hourly_data.get('wind_gust'),
            
            # Temperatur
            'air_temperature': hourly_data.get('temp'),
            'feels_like': hourly_data.get('feels_like'),
            'humidity': hourly_data.get('humidity'),
            'pressure': hourly_data.get('pressure'),
            
            # Nedbør
            'precipitation': hourly_data.get('rain', {}).get('1h', 0),
            
            # Bølger
            'wave_height': hourly_data.get('wave_height'),
            'wave_period': hourly_data.get('wave_period'), 
            'wave_direction': hourly_data.get('wave_deg'),
            
            # Metadata
            'timestamp': datetime.fromtimestamp(hourly_data.get('dt', 0), tz=timezone.utc).isoformat(),
            'lead_time_hours': (hourly_data.get('dt', 0) - datetime.now().timestamp()) / 3600,
            'source': 'openweathermap_hourly'
        }
    
    def _get_mock_data(self) -> Dict[str, Any]:
        """Mock data for testing når API key ikke er satt"""
        return {
            'wind_speed': 8.5,
            'wind_direction': 270,  # West
            'wind_gust': 12.0,
            'air_temperature': 15.0,
            'feels_like': 13.0,
            'humidity': 75,
            'pressure': 1015,
            'precipitation': 0.0,
            'wave_height': 1.2,
            'wave_period': 8.0,
            'wave_direction': 285,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'lead_time_hours': 0,
            'source': 'mock_data'
        }

def calculate_wind_offshore(wind_direction: float, spot_orientation: float) -> bool:
    """Beregn om vinden er offshore"""
    if wind_direction is None or spot_orientation is None:
        return False
    
    angle_diff = abs(wind_direction - spot_orientation)
    if angle_diff > 180:
        angle_diff = 360 - angle_diff
    
    return angle_diff <= 90

def calculate_swell_component(wave_height: float, wave_direction: float, spot_orientation: float) -> float:
    """Beregn swell component"""
    if None in [wave_height, wave_direction, spot_orientation]:
        return 0.0
    
    angle_diff = abs(wave_direction - spot_orientation)
    if angle_diff > 180:
        angle_diff = 360 - angle_diff
    
    angle_rad = math.radians(angle_diff)
    return wave_height * math.cos(angle_rad)

# Kartverket tidevann API
class KartverketTideService:
    """Service for tidevann data fra Kartverket"""
    
    BASE_URL = "https://api.sehavniva.no/tideapi.php"
    
    def get_tide_data(self, latitude: float, longitude: float, target_time: datetime) -> Optional[Dict[str, Any]]:
        """Hent tidevann for gitt posisjon og tid"""
        try:
            # Format dates for API
            date_str = target_time.strftime('%Y-%m-%dT%H')
            
            params = {
                'lat': latitude,
                'lon': longitude,
                'fromtime': date_str,
                'totime': date_str,
                'datatype': 'tab',
                'refcode': 'cd',
                'lang': 'nb',
                'interval': 10,
                'dst': 1,
                'tzone': 1,
                'tide_request': 'locationdata'
            }
            
            response = requests.get(self.BASE_URL, params=params)
            response.raise_for_status()
            
            # Parse response (simplified)
            data = response.text
            
            # Mock parsing for now - Kartverket API returnerer kompleks format
            return {
                'tide_level': 1.2,  # meter over sjøkart null
                'tide_trend': 'rising',  # rising, falling, high, low
                'next_high_tide': (target_time.timestamp() + 3600 * 2),  # 2 timer frem
                'next_low_tide': (target_time.timestamp() + 3600 * 8),   # 8 timer frem
                'source': 'kartverket_mock'
            }
            
        except Exception as e:
            print(f"Feil ved henting av tidevann: {e}")
            return {
                'tide_level': 1.0,
                'tide_trend': 'unknown',
                'source': 'mock'
            }

if __name__ == "__main__":
    # Test services
    owm = OpenWeatherMarineService()
    tide = KartverketTideService()
    
    test_time = datetime.now()
    
    print("Testing OpenWeatherMap Marine API...")
    weather_data = owm.get_weather_and_wave_data(58.8839, 5.5528, test_time)
    print(f"Weather data: {weather_data}")
    
    print("\nTesting Kartverket Tide API...")
    tide_data = tide.get_tide_data(58.8839, 5.5528, test_time)
    print(f"Tide data: {tide_data}")

