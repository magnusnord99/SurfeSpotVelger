"""
Data processing og feature engineering for ML-modellen
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from typing import Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

class SurfDataProcessor:
    """Klasse for å prosessere surf-data til ML-features"""
    
    def __init__(self, db_path: str = "../data/surfespotvelger.db"):
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}")
    
    def load_data(self) -> pd.DataFrame:
        """Last inn alle surf-økter fra database"""
        query = """
        SELECT 
            ss.*,
            sp.name as spot_name,
            sp.latitude,
            sp.longitude,
            sp.orientation as spot_orientation
        FROM surf_sessions ss
        LEFT JOIN surf_spots sp ON ss.spot_id = sp.id
        ORDER BY ss.date_time
        """
        
        df = pd.read_sql_query(query, self.engine)
        df['date_time'] = pd.to_datetime(df['date_time'])
        
        return df
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Lag alle ML-features fra rådata"""
        df = df.copy()
        
        # Temporal features
        df = self._add_temporal_features(df)
        
        # Weather features
        df = self._add_weather_features(df)
        
        # Wave features
        df = self._add_wave_features(df)
        
        # Spot features
        df = self._add_spot_features(df)
        
        # Historical features
        df = self._add_historical_features(df)
        
        return df
    
    def _add_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Legg til tidsbaserte features"""
        df['year'] = df['date_time'].dt.year
        df['month'] = df['date_time'].dt.month
        df['day_of_year'] = df['date_time'].dt.dayofyear
        df['hour'] = df['date_time'].dt.hour
        df['is_weekend'] = df['date_time'].dt.weekday >= 5
        
        # Sesong som numerisk (for cyclisk encoding)
        df['season_sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['season_cos'] = np.cos(2 * np.pi * df['month'] / 12)
        
        # Tid på dagen som cyclisk
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        
        # Ukedag som cyclisk
        df['weekday_sin'] = np.sin(2 * np.pi * df['weekday'] / 7)
        df['weekday_cos'] = np.cos(2 * np.pi * df['weekday'] / 7)
        
        return df
    
    def _add_weather_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Legg til værbaserte features"""
        # Vindstyrke kategorier
        df['wind_category'] = pd.cut(
            df['wind_speed'].fillna(0), 
            bins=[0, 3, 7, 12, float('inf')],
            labels=['light', 'moderate', 'strong', 'very_strong']
        )
        
        # Temperatur kategorier
        df['temp_category'] = pd.cut(
            df['air_temperature'].fillna(10),
            bins=[float('-inf'), 5, 15, 20, float('inf')],
            labels=['cold', 'cool', 'mild', 'warm']
        )
        
        # Nedbør binary
        df['has_precipitation'] = (df['precipitation'].fillna(0) > 0).astype(int)
        
        # Vind-komponenter (nord/øst)
        df['wind_north'] = np.cos(np.radians(df['wind_direction'].fillna(0))) * df['wind_speed'].fillna(0)
        df['wind_east'] = np.sin(np.radians(df['wind_direction'].fillna(0))) * df['wind_speed'].fillna(0)
        
        return df
    
    def _add_wave_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Legg til bølgebaserte features"""
        # Bølgehøyde kategorier
        df['wave_category'] = pd.cut(
            df['wave_height'].fillna(0),
            bins=[0, 0.5, 1.0, 1.5, 2.0, float('inf')],
            labels=['tiny', 'small', 'medium', 'large', 'huge']
        )
        
        # Periode kategorier
        df['period_category'] = pd.cut(
            df['wave_period'].fillna(8),
            bins=[0, 6, 8, 12, float('inf')],
            labels=['short', 'medium', 'long', 'very_long']
        )
        
        # Bølge energi (approksimering)
        df['wave_energy'] = (df['wave_height'].fillna(0) ** 2) * df['wave_period'].fillna(8)
        
        # Bølge-komponenter (nord/øst)
        df['wave_north'] = np.cos(np.radians(df['wave_direction'].fillna(270))) * df['wave_height'].fillna(0)
        df['wave_east'] = np.sin(np.radians(df['wave_direction'].fillna(270))) * df['wave_height'].fillna(0)
        
        return df
    
    def _add_spot_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Legg til spot-spesifikke features"""
        # One-hot encoding av spots
        spot_dummies = pd.get_dummies(df['spot_name'], prefix='spot')
        df = pd.concat([df, spot_dummies], axis=1)
        
        # Spot orientering som sin/cos
        df['spot_sin'] = np.sin(np.radians(df['spot_orientation'].fillna(270)))
        df['spot_cos'] = np.cos(np.radians(df['spot_orientation'].fillna(270)))
        
        return df
    
    def _add_historical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Legg til historiske features (rolling averages etc.)"""
        df = df.sort_values('date_time').reset_index(drop=True)
        
        # Rolling averages for hver spot
        for spot in df['spot_name'].unique():
            if pd.isna(spot):
                continue
                
            spot_mask = df['spot_name'] == spot
            spot_data = df[spot_mask].copy()
            
            # 30-dagers rolling average rating for dette spot
            df.loc[spot_mask, 'spot_rating_30d'] = (
                spot_data['rating']
                .rolling(window=5, min_periods=1)
                .mean()
                .shift(1)  # Unngå leakage
            )
            
            # Antall økter siste 30 dager
            df.loc[spot_mask, 'sessions_last_30d'] = (
                spot_data.index.to_series()
                .rolling(window=5, min_periods=1)
                .count()
                .shift(1)
            )
        
        # Global features
        df['session_number'] = range(1, len(df) + 1)  # Total erfaring
        df['days_since_last_session'] = df['date_time'].diff().dt.days.fillna(0)
        
        return df
    
    def prepare_ml_data(self, target_col: str = 'rating') -> Tuple[pd.DataFrame, pd.Series]:
        """
        Forbered data for ML-trening
        
        Returns:
            X: Features DataFrame
            y: Target Series
        """
        df = self.load_data()
        
        if len(df) == 0:
            raise ValueError("Ingen data funnet i database")
        
        # Opprett features
        df = self.create_features(df)
        
        # Velg feature-kolonner
        feature_cols = self._select_feature_columns(df)
        
        X = df[feature_cols].copy()
        y = df[target_col].copy()
        
        # Håndter missing values
        X = self._handle_missing_values(X)
        
        return X, y
    
    def _select_feature_columns(self, df: pd.DataFrame) -> list:
        """Velg hvilke kolonner som skal brukes som features"""
        # Numeriske features
        numeric_features = [
            'wave_height', 'wave_period', 'swell_component', 'swell_angle_difference',
            'wind_speed', 'wind_north', 'wind_east', 'air_temperature',
            'wave_energy', 'wave_north', 'wave_east',
            'hour', 'month', 'weekday',
            'season_sin', 'season_cos', 'hour_sin', 'hour_cos',
            'weekday_sin', 'weekday_cos', 'spot_sin', 'spot_cos',
            'session_number', 'days_since_last_session',
            'spot_rating_30d', 'sessions_last_30d'
        ]
        
        # Kategoriske features (binary)
        categorical_features = [
            'offshore_wind', 'is_weekend', 'has_precipitation'
        ]
        
        # Spot dummies
        spot_features = [col for col in df.columns if col.startswith('spot_')]
        
        # Kombinér alle features som finnes i datasettet
        all_features = numeric_features + categorical_features + spot_features
        available_features = [col for col in all_features if col in df.columns]
        
        return available_features
    
    def _handle_missing_values(self, X: pd.DataFrame) -> pd.DataFrame:
        """Håndter missing values i feature matrix"""
        X = X.copy()
        
        # Fill missing values med fornuftige defaults
        defaults = {
            'wave_height': 0.5,
            'wave_period': 8.0,
            'wind_speed': 5.0,
            'air_temperature': 12.0,
            'swell_component': 0.0,
            'swell_angle_difference': 90.0,
            'offshore_wind': False,
            'wave_energy': 4.0,
            'spot_rating_30d': 3.0,
            'sessions_last_30d': 1.0
        }
        
        for col in X.columns:
            if X[col].isnull().any():
                if col in defaults:
                    X[col] = X[col].fillna(defaults[col])
                elif X[col].dtype in ['int64', 'float64']:
                    X[col] = X[col].fillna(X[col].median())
                else:
                    X[col] = X[col].fillna(0)
        
        return X
    
    def get_data_summary(self) -> dict:
        """Få oversikt over datasettet"""
        df = self.load_data()
        
        summary = {
            'total_sessions': len(df),
            'date_range': {
                'start': df['date_time'].min().isoformat() if not df.empty else None,
                'end': df['date_time'].max().isoformat() if not df.empty else None
            },
            'spots': df['spot_name'].value_counts().to_dict(),
            'ratings': df['rating'].value_counts().sort_index().to_dict(),
            'missing_weather': {
                'wave_height': df['wave_height'].isnull().sum(),
                'wind_speed': df['wind_speed'].isnull().sum(),
                'air_temperature': df['air_temperature'].isnull().sum()
            }
        }
        
        return summary

if __name__ == "__main__":
    processor = SurfDataProcessor()
    summary = processor.get_data_summary()
    print("Data Summary:")
    print(f"Total sessions: {summary['total_sessions']}")
    print(f"Date range: {summary['date_range']}")
    print(f"Spots: {summary['spots']}")
    print(f"Ratings: {summary['ratings']}")
