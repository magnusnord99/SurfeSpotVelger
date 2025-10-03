"""
Surf Spot Recommender System
Spot-basert anbefalingssystem for surf spots
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
try:
    from database import SurfSpot, SurfSession, SessionLocal
except ImportError:
    from .database import SurfSpot, SurfSession, SessionLocal
import math


class SurfRecommender:
    """Spot-basert surf anbefalingssystem"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def get_spot_recommendations(self, target_date: datetime, max_spots: int = 5) -> List[Dict[str, Any]]:
        """
        Få surf spot anbefalinger for en gitt dato
        
        Args:
            target_date: Dato for anbefaling
            max_spots: Maksimalt antall spots å returnere
            
        Returns:
            Liste med anbefalte spots sortert etter kvalitet
        """
        spots = self.db.query(SurfSpot).all()
        recommendations = []
        
        for spot in spots:
            # Simuler surf-forhold for denne spot
            surf_conditions = self._simulate_surf_conditions(spot, target_date)
            
            # Beregn surf score
            surf_score = self._calculate_surf_score(surf_conditions, spot)
            
            # Legg til i anbefalinger
            recommendations.append({
                'spot_name': spot.name,
                'coordinates': (spot.latitude, spot.longitude),
                'orientation': spot.orientation,
                'description': spot.description,
                'surf_score': surf_score,
                'surf_conditions': surf_conditions,
                'recommendation_reason': self._get_recommendation_reason(surf_conditions, surf_score)
            })
        
        # Sorter etter surf score (høyest først)
        recommendations.sort(key=lambda x: x['surf_score'], reverse=True)
        
        return recommendations[:max_spots]
    
    def _simulate_surf_conditions(self, spot: SurfSpot, target_date: datetime) -> Dict[str, Any]:
        """
        Simuler surf-forhold for en spot på en gitt dato
        Dette er en forenklet versjon - i produksjon ville du hentet ekte værdata
        """
        # Simuler realistiske surf-forhold basert på dato og spot
        day_of_year = target_date.timetuple().tm_yday
        
        # Simuler sesongvariasjon (bedre surf på høst/vinter)
        seasonal_factor = 0.7 + 0.3 * math.sin((day_of_year - 80) * 2 * math.pi / 365)
        
        # Simuler spot-spesifikke forhold
        spot_factor = self._get_spot_factor(spot)
        
        # Simuler realistiske verdier
        wave_height = max(0.5, min(3.0, 1.5 * seasonal_factor * spot_factor + 
                                 0.3 * math.sin(day_of_year * 0.1)))
        
        wave_period = max(4.0, min(15.0, 8.0 + 2.0 * math.sin(day_of_year * 0.05)))
        
        # Vind (bedre med offshore vind)
        wind_speed = max(2.0, min(15.0, 8.0 + 3.0 * math.sin(day_of_year * 0.08)))
        wind_direction = (spot.orientation + 180 + 30 * math.sin(day_of_year * 0.03)) % 360
        
        # Beregn offshore vind
        offshore_wind = self._is_offshore_wind(wind_direction, spot.orientation)
        
        return {
            'wave_height': round(wave_height, 1),
            'wave_period': round(wave_period, 1),
            'wave_direction': round((spot.orientation + 20 * math.sin(day_of_year * 0.02)) % 360),
            'wind_speed': round(wind_speed, 1),
            'wind_direction': round(wind_direction),
            'offshore_wind': offshore_wind,
            'air_temperature': max(5, 15 + 10 * math.sin((day_of_year - 80) * 2 * math.pi / 365)),
            'tide_height': 0.5 + 0.3 * math.sin(day_of_year * 0.1),
            'seasonal_factor': round(seasonal_factor, 2)
        }
    
    def _get_spot_factor(self, spot: SurfSpot) -> float:
        """Få spot-spesifikk faktor basert på beskrivelse"""
        description = spot.description.lower()
        
        if 'beach break' in description:
            return 1.2  # Beach breaks er mer pålitelige
        elif 'reef break' in description:
            return 0.8  # Reef breaks krever spesifikke forhold
        elif 'point break' in description:
            return 0.9  # Point breaks krever spesifikke forhold
        elif 'beskyttet' in description:
            return 1.1  # Beskyttede spots fungerer oftere
        else:
            return 1.0  # Standard
    
    def _calculate_surf_score(self, conditions: Dict[str, Any], spot: SurfSpot) -> float:
        """
        Beregn surf score basert på forhold og spot-egenskaper
        Score 1-10 (10 = perfekt surf)
        """
        score = 5.0  # Start med middels score
        
        # Bølgehøyde (optimalt 1-2m)
        wave_height = conditions['wave_height']
        if 1.0 <= wave_height <= 2.0:
            score += 2.0
        elif 0.8 <= wave_height <= 2.5:
            score += 1.0
        elif wave_height < 0.5:
            score -= 2.0
        elif wave_height > 3.0:
            score -= 1.0
        
        # Bølgeperiode (optimalt 8-12s)
        wave_period = conditions['wave_period']
        if 8.0 <= wave_period <= 12.0:
            score += 1.5
        elif 6.0 <= wave_period <= 14.0:
            score += 0.5
        elif wave_period < 5.0:
            score -= 1.0
        
        # Offshore vind (stor bonus)
        if conditions['offshore_wind']:
            score += 2.0
        else:
            # Onshore vind - sjekk styrke
            wind_speed = conditions['wind_speed']
            if wind_speed > 10:
                score -= 1.5
            elif wind_speed > 7:
                score -= 0.5
        
        # Vindstyrke (optimalt 3-8 m/s)
        wind_speed = conditions['wind_speed']
        if 3.0 <= wind_speed <= 8.0:
            score += 0.5
        elif wind_speed > 12.0:
            score -= 1.0
        
        # Spot-spesifikke justeringer
        spot_factor = self._get_spot_factor(spot)
        score *= spot_factor
        
        # Sesongfaktor
        score *= conditions['seasonal_factor']
        
        # Begrens score til 1-10
        return max(1.0, min(10.0, round(score, 1)))
    
    def _is_offshore_wind(self, wind_direction: float, spot_orientation: float) -> bool:
        """Sjekk om vind er offshore for denne spot"""
        # Offshore vind er motsatt retning av spot orientation
        offshore_direction = (spot_orientation + 180) % 360
        
        # Toleranse på ±45 grader
        diff = abs(wind_direction - offshore_direction)
        if diff > 180:
            diff = 360 - diff
        
        return diff <= 45
    
    def _get_recommendation_reason(self, conditions: Dict[str, Any], surf_score: float) -> str:
        """Generer forklaring for anbefalingen"""
        reasons = []
        
        if conditions['offshore_wind']:
            reasons.append("Offshore vind")
        
        if 1.0 <= conditions['wave_height'] <= 2.0:
            reasons.append("Perfekt bølgehøyde")
        
        if 8.0 <= conditions['wave_period'] <= 12.0:
            reasons.append("Lang bølgeperiode")
        
        if surf_score >= 8.0:
            reasons.append("Utmerket surf-forhold")
        elif surf_score >= 6.0:
            reasons.append("Gode surf-forhold")
        elif surf_score >= 4.0:
            reasons.append("OK surf-forhold")
        else:
            reasons.append("Begrensede surf-forhold")
        
        return ", ".join(reasons[:3])  # Max 3 grunner
    
    def get_historical_performance(self, spot_name: str) -> Dict[str, Any]:
        """
        Analyser historisk ytelse for en spot basert på loggde økter
        """
        sessions = self.db.query(SurfSession).join(SurfSpot).filter(
            SurfSpot.name == spot_name
        ).all()
        
        if not sessions:
            return {
                'spot_name': spot_name,
                'total_sessions': 0,
                'average_rating': 0,
                'average_surf_score': 0,
                'success_rate': 0
            }
        
        ratings = [s.rating for s in sessions if s.rating is not None]
        surf_scores = [s.surf_score for s in sessions if s.surf_score is not None]
        
        # Beregn suksessrate (rating >= 4)
        successful_sessions = len([r for r in ratings if r >= 4])
        
        return {
            'spot_name': spot_name,
            'total_sessions': len(sessions),
            'average_rating': round(sum(ratings) / len(ratings), 1) if ratings else 0,
            'average_surf_score': round(sum(surf_scores) / len(surf_scores), 1) if surf_scores else 0,
            'success_rate': round(successful_sessions / len(sessions) * 100, 1) if sessions else 0
        }
    
    def close(self):
        """Lukk database tilkobling"""
        self.db.close()


# Global instans
recommender = SurfRecommender()
