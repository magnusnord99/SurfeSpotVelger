"""
Hybrid surf service - kombinerer YR (gratis) + Stormglass (bølgeperiode)
Optimal løsning: gratis værdata + kritiske surf-data
"""
import requests
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import math

class HybridSurfService:
    """
    Kombinerer YR API (gratis) med Stormglass API (bølgeperiode)
    Optimal løsning for surf app
    """
    
    def __init__(self, stormglass_api_key: str = None):
        # YR API - gratis, ingen key nødvendig
        self.yr_headers = {
            'User-Agent': 'SurfeSpotVelger/1.0 (kontakt@example.com)'
        }
        self.yr_weather_url = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
        self.yr_ocean_url = "https://api.met.no/weatherapi/oceanforecast/2.0/complete"
        
        # Stormglass API - kun for bølgeperiode
        self.stormglass_api_key = stormglass_api_key or "81111e72-97c6-11f0-a246-0242ac130006-81111f1c-97c6-11f0-a246-0242ac130006"
        self.stormglass_url = "https://api.stormglass.io/v2/weather/point"
        self.stormglass_headers = {
            'Authorization': self.stormglass_api_key
        }
    
    def get_complete_surf_data(self, latitude: float, longitude: float, target_time: datetime) -> Dict[str, Any]:
        """
        Hent komplett surf data fra både YR og Stormglass
        
        Returns:
            Dict med alle surf-kritiske data
        """
        surf_data = {}
        
        # 1. Hent værdata fra YR (gratis)
        weather_data = self._get_yr_weather_data(latitude, longitude, target_time)
        if weather_data:
            surf_data.update(weather_data)
        
        # 2. Hent bølgedata fra YR (gratis)
        wave_data = self._get_yr_wave_data(latitude, longitude, target_time)
        if wave_data:
            surf_data.update(wave_data)
        
        # 3. Hent bølgeperiode fra Stormglass (kun hvis API key er satt)
        if self.stormglass_api_key != "YOUR_API_KEY_HERE":
            print("Kaller Stormglass API for bølgeperiode...")
            period_data = self._get_stormglass_period_data(latitude, longitude, target_time)
            if period_data:
                surf_data.update(period_data)
                print(f"Stormglass data mottatt: {period_data}")
            else:
                print("Ingen data fra Stormglass, bruker estimat")
                # Fallback: estimat basert på bølgehøyde
                surf_data['wave_period'] = self._estimate_wave_period(surf_data.get('wave_height'))
                surf_data['wave_period_source'] = 'estimated'
        else:
            print("Stormglass API key ikke satt, bruker estimat")
            # Fallback: estimat basert på bølgehøyde
            surf_data['wave_period'] = self._estimate_wave_period(surf_data.get('wave_height'))
            surf_data['wave_period_source'] = 'estimated'
        
        # 4. Legg til metadata
        surf_data['timestamp'] = target_time.isoformat()
        surf_data['data_sources'] = self._get_data_sources(surf_data)
        
        return surf_data
    
    def _get_yr_weather_data(self, latitude: float, longitude: float, target_time: datetime) -> Optional[Dict[str, Any]]:
        """Hent værdata fra YR API"""
        try:
            params = {'lat': latitude, 'lon': longitude}
            response = requests.get(self.yr_weather_url, params=params, headers=self.yr_headers)
            response.raise_for_status()
            
            data = response.json()
            return self._extract_yr_weather_for_time(data, target_time)
            
        except Exception as e:
            print(f"Feil ved henting av YR værdata: {e}")
            return None
    
    def _get_yr_wave_data(self, latitude: float, longitude: float, target_time: datetime) -> Optional[Dict[str, Any]]:
        """Hent bølgedata fra YR Ocean API"""
        try:
            params = {'lat': latitude, 'lon': longitude}
            response = requests.get(self.yr_ocean_url, params=params, headers=self.yr_headers)
            response.raise_for_status()
            
            data = response.json()
            return self._extract_yr_wave_for_time(data, target_time)
            
        except Exception as e:
            print(f"Feil ved henting av YR bølgedata: {e}")
            return None
    
    def _get_stormglass_period_data(self, latitude: float, longitude: float, target_time: datetime) -> Optional[Dict[str, Any]]:
        """Hent bølgeperiode og tidevann fra Stormglass API"""
        try:
            timestamp = int(target_time.timestamp())
            params = {
                'lat': latitude,
                'lng': longitude,
                'params': ['wavePeriod', 'waveHeight', 'tideHeight'],  # Inkluder tidevann
                'source': 'sg',
                'start': timestamp,
                'end': timestamp
            }
            
            response = requests.get(self.stormglass_url, params=params, headers=self.stormglass_headers)
            response.raise_for_status()
            
            data = response.json()
            return self._extract_stormglass_period(data)
            
        except Exception as e:
            print(f"Feil ved henting av Stormglass periode: {e}")
            return None
    
    def _extract_yr_weather_for_time(self, yr_data: Dict, target_time: datetime) -> Dict[str, Any]:
        """Ekstraher værdata fra YR response"""
        timeseries = yr_data.get('properties', {}).get('timeseries', [])
        
        if not timeseries:
            return {}
        
        # Finn nærmeste tidspunkt
        best_match = self._find_closest_time_entry(timeseries, target_time)
        if not best_match:
            return {}
        
        instant_data = best_match.get('data', {}).get('instant', {}).get('details', {})
        next_1h = best_match.get('data', {}).get('next_1_hours', {})
        
        return {
            'wind_speed': instant_data.get('wind_speed'),
            'wind_direction': instant_data.get('wind_from_direction'),
            'wind_gust': instant_data.get('wind_speed_of_gust'),
            'air_temperature': instant_data.get('air_temperature'),
            'humidity': instant_data.get('relative_humidity'),
            'pressure': instant_data.get('air_pressure_at_sea_level'),
            'precipitation': next_1h.get('details', {}).get('precipitation_amount', 0.0),
            'weather_source': 'yr'
        }
    
    def _extract_yr_wave_for_time(self, ocean_data: Dict, target_time: datetime) -> Dict[str, Any]:
        """Ekstraher bølgedata fra YR Ocean response"""
        timeseries = ocean_data.get('properties', {}).get('timeseries', [])
        
        if not timeseries:
            return {}
        
        best_match = self._find_closest_time_entry(timeseries, target_time)
        if not best_match:
            return {}
        
        instant_data = best_match.get('data', {}).get('instant', {}).get('details', {})
        
        return {
            'wave_height': instant_data.get('sea_surface_wave_height'),
            'wave_direction': instant_data.get('sea_surface_wave_from_direction'),
            'water_temperature': instant_data.get('sea_water_temperature'),
            'wave_source': 'yr'
        }
    
    def _extract_stormglass_period(self, stormglass_data: Dict) -> Dict[str, Any]:
        """Ekstraher bølgeperiode fra Stormglass response (hvis tilgjengelig)"""
        hours = stormglass_data.get('hours', [])
        
        if not hours:
            return {}
        
        hour_data = hours[0]
        
        # Debug: se hva som er tilgjengelig
        print(f"Stormglass tilgjengelige data: {list(hour_data.keys())}")
        
        wave_period = hour_data.get('wavePeriod', {}).get('sg', None)
        wave_height = hour_data.get('waveHeight', {}).get('sg', None)
        tide_height = hour_data.get('tideHeight', {}).get('sg', None)
        
        result = {}
        
        # Bølgeperiode
        if wave_period is not None:
            result['wave_period'] = wave_period
            result['wave_period_source'] = 'stormglass'
        else:
            # Fallback: estimat basert på bølgehøyde hvis tilgjengelig
            if wave_height is not None:
                result['wave_period'] = self._estimate_wave_period(wave_height)
                result['wave_period_source'] = 'estimated_from_stormglass_height'
        
        # Tidevann
        if tide_height is not None:
            result['tide_height'] = tide_height
            result['tide_source'] = 'stormglass'
            print(f"🌊 Stormglass tidevann: {tide_height}m")
        else:
            print("⚠️ Ingen tidevann data fra Stormglass")
        
        print(f"Stormglass data mottatt: {result}")
        return result
    
    def _find_closest_time_entry(self, timeseries: list, target_time: datetime) -> Optional[Dict]:
        """Finn nærmeste tidspunkt i timeseries"""
        if target_time.tzinfo is None:
            target_time_utc = target_time.replace(tzinfo=timezone.utc)
        else:
            target_time_utc = target_time.astimezone(timezone.utc)
        
        best_match = None
        min_time_diff = float('inf')
        
        for entry in timeseries:
            try:
                entry_time = datetime.fromisoformat(entry['time'].replace('Z', '+00:00'))
                time_diff = abs((entry_time - target_time_utc).total_seconds())
                
                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    best_match = entry
            except Exception:
                continue
        
        return best_match
    
    def _estimate_wave_period(self, wave_height: Optional[float]) -> Optional[float]:
        """Estimat bølgeperiode basert på bølgehøyde"""
        if wave_height is None:
            return None
        
        # Enkel estimering: større bølger har ofte lengre periode
        if wave_height < 0.5:
            return 6.0
        elif wave_height < 1.0:
            return 8.0
        elif wave_height < 1.5:
            return 10.0
        elif wave_height < 2.0:
            return 12.0
        else:
            return 14.0
    
    def _get_data_sources(self, surf_data: Dict) -> list:
        """List opp hvilke datakilder som ble brukt"""
        sources = []
        
        if surf_data.get('weather_source'):
            sources.append(surf_data['weather_source'])
        if surf_data.get('wave_source'):
            sources.append(surf_data['wave_source'])
        if surf_data.get('wave_period_source'):
            sources.append(surf_data['wave_period_source'])
        
        return sources

def calculate_surf_score(wave_height: float, wave_period: float, wind_speed: float, 
                        wind_direction: float, spot_orientation: float) -> float:
    """Beregn surf score basert på alle faktorer"""
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
    
    # Vind score
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

def calculate_swell_component(wave_height: float, wave_direction: float, spot_orientation: float) -> float:
    """Beregn hvor mye av swellen som treffer spot-et direkte"""
    if None in [wave_height, wave_direction, spot_orientation]:
        return 0.0
    
    angle_diff = abs(wave_direction - spot_orientation)
    if angle_diff > 180:
        angle_diff = 360 - angle_diff
    
    # Cosinus-komponent
    angle_rad = math.radians(angle_diff)
    return wave_height * math.cos(angle_rad)

if __name__ == "__main__":
    # Test hybrid service
    hybrid = HybridSurfService()
    
    test_time = datetime.now()
    
    print("Testing Hybrid Surf Service (YR + Stormglass)...")
    surf_data = hybrid.get_complete_surf_data(58.8839, 5.5528, test_time)
    
    print(f"\n🌊 Surf Data:")
    print(f"   Bølgehøyde: {surf_data.get('wave_height')}m (fra {surf_data.get('wave_source', 'unknown')})")
    print(f"   Bølgeperiode: {surf_data.get('wave_period')}s (fra {surf_data.get('wave_period_source', 'unknown')})")
    print(f"   Bølgeretning: {surf_data.get('wave_direction')}° (fra {surf_data.get('wave_source', 'unknown')})")
    print(f"   Vind: {surf_data.get('wind_speed')}m/s fra {surf_data.get('wind_direction')}° (fra {surf_data.get('weather_source', 'unknown')})")
    print(f"   Vannetemperatur: {surf_data.get('water_temperature')}°C")
    
    print(f"\n📊 Datakilder: {', '.join(surf_data.get('data_sources', []))}")
    
    # Test surf score
    if all(surf_data.get(key) is not None for key in ['wave_height', 'wave_period', 'wind_speed', 'wind_direction']):
        spot_orientation = 270  # Eksempel
        score = calculate_surf_score(
            surf_data['wave_height'], 
            surf_data['wave_period'],
            surf_data['wind_speed'],
            surf_data['wind_direction'],
            spot_orientation
        )
        print(f"\n🏄‍♂️ Surf Score: {score}/10")
