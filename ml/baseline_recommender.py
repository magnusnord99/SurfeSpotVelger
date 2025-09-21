"""
Baseline regel-basert anbefaling system for cold start
Dette systemet kan brukes før vi har nok data til ML-modell
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any
from datetime import datetime

class BaselineRecommender:
    """
    Regel-basert anbefaler som bruker surfing-kunnskap
    """
    
    def __init__(self):
        # Spot-spesifikke preferences (basert på kjent kunnskap om Stavanger-spots)
        self.spot_preferences = {
            'Bore': {
                'optimal_wave_height': (0.8, 2.0),
                'optimal_wave_direction': (240, 300),  # SW til NW
                'optimal_wind_direction': (60, 120),   # NE til SE (offshore)
                'max_wind_speed': 12,
                'description': 'Populær beach break'
            },
            'Orre': {
                'optimal_wave_height': (1.0, 3.0),
                'optimal_wave_direction': (250, 310),  # WSW til NW
                'optimal_wind_direction': (70, 130),   # ENE til SE
                'max_wind_speed': 15,
                'description': 'Eksponert, trenger større swell'
            },
            'Hellestø': {
                'optimal_wave_height': (0.5, 1.8),
                'optimal_wave_direction': (220, 290),  # SW til W
                'optimal_wind_direction': (40, 100),   # NE til E
                'max_wind_speed': 10,
                'description': 'Beskyttet, fungerer på mindre swell'
            },
            'Sola Strand': {
                'optimal_wave_height': (0.6, 2.2),
                'optimal_wave_direction': (240, 300),  # SW til NW
                'optimal_wind_direction': (50, 110),   # NE til ESE
                'max_wind_speed': 12,
                'description': 'Lang strand, flere peaks'
            },
            'Reve': {
                'optimal_wave_height': (1.2, 4.0),
                'optimal_wave_direction': (260, 320),  # W til NW
                'optimal_wind_direction': (80, 140),   # E til SE
                'max_wind_speed': 18,
                'description': 'Reef break, trenger større swell'
            },
            'Sirevåg': {
                'optimal_wave_height': (0.8, 2.5),
                'optimal_wave_direction': (280, 340),  # W til N
                'optimal_wind_direction': (90, 150),   # E til SSE
                'max_wind_speed': 14,
                'description': 'Beskyttet bay'
            }
        }
        
        # Generelle regler
        self.rules = {
            'min_wave_height': 0.3,
            'max_wave_height': 5.0,
            'ideal_wind_speed': 8.0,
            'max_wind_speed_general': 20.0,
            'ideal_period_range': (7, 14),
            'temperature_bonus_threshold': 15.0  # Bonus for varme dager
        }
    
    def get_recommendations(self, weather_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Få anbefalinger basert på værdata
        
        Args:
            weather_data: Dict med værdata
            
        Returns:
            List med anbefalinger sortert etter score
        """
        recommendations = []
        
        for spot_name, preferences in self.spot_preferences.items():
            score = self._calculate_spot_score(weather_data, spot_name, preferences)
            
            recommendation = {
                'spot': spot_name,
                'score': score,
                'rating_prediction': self._score_to_rating(score),
                'explanation': self._generate_explanation(weather_data, spot_name, preferences, score),
                'conditions_summary': self._summarize_conditions(weather_data, preferences)
            }
            
            recommendations.append(recommendation)
        
        # Sorter etter score
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        
        return recommendations
    
    def _calculate_spot_score(self, weather: Dict, spot_name: str, prefs: Dict) -> float:
        """Beregn score for et spot basert på værdata"""
        score = 0.0
        max_score = 100.0
        
        # Wave height score (30% av total)
        wave_height = weather.get('wave_height', 0.5)
        wave_score = self._score_wave_height(wave_height, prefs['optimal_wave_height'])
        score += wave_score * 0.30
        
        # Wave direction score (25% av total)
        wave_direction = weather.get('wave_direction', 270)
        direction_score = self._score_wave_direction(wave_direction, prefs['optimal_wave_direction'])
        score += direction_score * 0.25
        
        # Wind score (25% av total)
        wind_speed = weather.get('wind_speed', 5.0)
        wind_direction = weather.get('wind_direction', 90)
        wind_score = self._score_wind(wind_speed, wind_direction, prefs)
        score += wind_score * 0.25
        
        # Period score (10% av total)
        wave_period = weather.get('wave_period', 8.0)
        period_score = self._score_period(wave_period)
        score += period_score * 0.10
        
        # Temperature bonus (5% av total)
        temperature = weather.get('air_temperature', 12.0)
        temp_score = self._score_temperature(temperature)
        score += temp_score * 0.05
        
        # Time of day bonus (5% av total)
        time_score = self._score_time_of_day()
        score += time_score * 0.05
        
        return min(score, max_score)
    
    def _score_wave_height(self, height: float, optimal_range: tuple) -> float:
        """Score wave height (0-100)"""
        min_height, max_height = optimal_range
        
        if height < self.rules['min_wave_height']:
            return 0.0  # Too small
        
        if height > self.rules['max_wave_height']:
            return 10.0  # Too big, dangerous
        
        if min_height <= height <= max_height:
            return 100.0  # Perfect
        
        # Gradual falloff outside optimal range
        if height < min_height:
            return max(0, 70 * (height / min_height))
        else:  # height > max_height
            excess = height - max_height
            return max(20, 100 - (excess * 30))
    
    def _score_wave_direction(self, direction: float, optimal_range: tuple) -> float:
        """Score wave direction (0-100)"""
        min_dir, max_dir = optimal_range
        
        # Handle wraparound (e.g., 350-30 degrees)
        if max_dir < min_dir:
            if direction >= min_dir or direction <= max_dir:
                return 100.0
            # Calculate distance to nearest edge
            dist_to_min = min(abs(direction - min_dir), 360 - abs(direction - min_dir))
            dist_to_max = min(abs(direction - max_dir), 360 - abs(direction - max_dir))
            min_distance = min(dist_to_min, dist_to_max)
        else:
            if min_dir <= direction <= max_dir:
                return 100.0
            min_distance = min(abs(direction - min_dir), abs(direction - max_dir))
        
        # Gradual falloff with distance
        return max(0, 100 - (min_distance * 2))
    
    def _score_wind(self, speed: float, direction: float, prefs: Dict) -> float:
        """Score wind conditions (0-100)"""
        # Wind speed component
        if speed > prefs['max_wind_speed']:
            speed_score = max(0, 50 - (speed - prefs['max_wind_speed']) * 10)
        else:
            speed_score = min(100, 100 - abs(speed - self.rules['ideal_wind_speed']) * 5)
        
        # Wind direction component (offshore is better)
        optimal_wind_range = prefs['optimal_wind_direction']
        direction_score = self._score_wave_direction(direction, optimal_wind_range)
        
        # Combine (speed is more important than direction for wind)
        return speed_score * 0.7 + direction_score * 0.3
    
    def _score_period(self, period: float) -> float:
        """Score wave period (0-100)"""
        min_period, max_period = self.rules['ideal_period_range']
        
        if min_period <= period <= max_period:
            return 100.0
        
        if period < min_period:
            return max(30, 100 - (min_period - period) * 15)
        else:
            return max(60, 100 - (period - max_period) * 10)
    
    def _score_temperature(self, temperature: float) -> float:
        """Score temperature (bonus for warm days)"""
        if temperature >= self.rules['temperature_bonus_threshold']:
            return 100.0
        return max(0, temperature * 5)  # Gradual increase
    
    def _score_time_of_day(self) -> float:
        """Score current time (morning sessions are often better)"""
        hour = datetime.now().hour
        
        if 6 <= hour <= 9:  # Early morning
            return 100.0
        elif 10 <= hour <= 16:  # Day time
            return 70.0
        elif 17 <= hour <= 19:  # Evening
            return 85.0
        else:  # Night/very early
            return 30.0
    
    def _score_to_rating(self, score: float) -> str:
        """Konverter score til rating kategori"""
        if score >= 80:
            return 'Excellent'
        elif score >= 65:
            return 'Good'
        elif score >= 50:
            return 'Fair'
        elif score >= 35:
            return 'Poor'
        else:
            return 'Very Poor'
    
    def _generate_explanation(self, weather: Dict, spot: str, prefs: Dict, score: float) -> str:
        """Generer forklaring for anbefalingen"""
        explanations = []
        
        # Wave height
        wave_height = weather.get('wave_height', 0.5)
        min_h, max_h = prefs['optimal_wave_height']
        if min_h <= wave_height <= max_h:
            explanations.append(f"Perfect wave size ({wave_height:.1f}m)")
        elif wave_height < min_h:
            explanations.append(f"Waves a bit small ({wave_height:.1f}m)")
        else:
            explanations.append(f"Waves quite big ({wave_height:.1f}m)")
        
        # Wind
        wind_speed = weather.get('wind_speed', 5.0)
        wind_direction = weather.get('wind_direction', 90)
        
        # Check if wind is offshore
        optimal_wind = prefs['optimal_wind_direction']
        is_offshore = optimal_wind[0] <= wind_direction <= optimal_wind[1]
        
        if is_offshore and wind_speed <= 10:
            explanations.append("Great offshore winds")
        elif is_offshore:
            explanations.append("Offshore but strong winds")
        elif wind_speed <= 5:
            explanations.append("Light onshore winds")
        else:
            explanations.append("Strong onshore winds")
        
        # Period
        period = weather.get('wave_period', 8.0)
        if period >= 10:
            explanations.append("Long period swell")
        elif period >= 7:
            explanations.append("Good period")
        else:
            explanations.append("Short period waves")
        
        return " • ".join(explanations)
    
    def _summarize_conditions(self, weather: Dict, prefs: Dict) -> Dict[str, str]:
        """Lag sammendrag av forholdene"""
        return {
            'waves': f"{weather.get('wave_height', 0.5):.1f}m @ {weather.get('wave_period', 8.0):.0f}s",
            'wind': f"{weather.get('wind_speed', 5.0):.0f} m/s from {weather.get('wind_direction', 90):.0f}°",
            'temp': f"{weather.get('air_temperature', 12.0):.0f}°C"
        }

# Convenience function
def get_baseline_recommendations(weather_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Få baseline anbefalinger for gitt værdata
    
    Args:
        weather_data: Dict med værdata
        
    Returns:
        List med anbefalinger
    """
    recommender = BaselineRecommender()
    return recommender.get_recommendations(weather_data)

if __name__ == "__main__":
    # Test baseline recommender
    test_weather = {
        'wave_height': 1.2,
        'wave_period': 9.0,
        'wave_direction': 270,  # West
        'wind_speed': 8.0,
        'wind_direction': 90,   # East (offshore for west-facing spots)
        'air_temperature': 15.0
    }
    
    recommendations = get_baseline_recommendations(test_weather)
    
    print("Baseline Recommendations:")
    print("=" * 50)
    
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec['spot']} - {rec['rating_prediction']} (Score: {rec['score']:.1f})")
        print(f"   {rec['explanation']}")
        print(f"   Conditions: {rec['conditions_summary']['waves']}, {rec['conditions_summary']['wind']}")
        print()
