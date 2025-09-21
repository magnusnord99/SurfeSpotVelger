"""
ML model training og prediksjoner for surf spot anbefaling
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.preprocessing import LabelEncoder
import pickle
import os
from datetime import datetime
from typing import Tuple, Optional, Dict, Any
import warnings
warnings.filterwarnings('ignore')

try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

from data_processor import SurfDataProcessor

class SurfModelTrainer:
    """Klasse for å trene og evaluere surf spot anbefalingsmodeller"""
    
    def __init__(self, data_processor: SurfDataProcessor):
        self.processor = data_processor
        self.model = None
        self.feature_names = None
        self.model_type = None
        self.label_encoder = None
        
    def train_model(self, model_type: str = 'xgboost', min_samples: int = 20) -> Dict[str, Any]:
        """
        Tren modell på tilgjengelig data
        
        Args:
            model_type: 'random_forest', 'gradient_boosting', eller 'xgboost'
            min_samples: Minimum antall samples for å trene modell
            
        Returns:
            Dict med treningsresultater
        """
        # Last data
        X, y = self.processor.prepare_ml_data()
        
        if len(X) < min_samples:
            return {
                'success': False,
                'message': f'Trenger minst {min_samples} økter for å trene modell. Har {len(X)} økter.',
                'samples': len(X)
            }
        
        # Konverter rating til kategorier for bedre klassifisering
        y_categorical = self._convert_ratings_to_categories(y)
        
        # Velg modell
        model = self._get_model(model_type)
        
        # Time-based split for validering
        tscv = TimeSeriesSplit(n_splits=min(5, len(X) // 10))
        
        # Cross-validation
        cv_scores = cross_val_score(model, X, y_categorical, cv=tscv, scoring='accuracy')
        
        # Tren på all data
        model.fit(X, y_categorical)
        
        # Lagre modell og metadata
        self.model = model
        self.feature_names = X.columns.tolist()
        self.model_type = model_type
        
        # Feature importance
        feature_importance = self._get_feature_importance(model, X.columns)
        
        results = {
            'success': True,
            'model_type': model_type,
            'samples': len(X),
            'features': len(X.columns),
            'cv_accuracy_mean': cv_scores.mean(),
            'cv_accuracy_std': cv_scores.std(),
            'feature_importance': feature_importance,
            'training_date': datetime.now().isoformat()
        }
        
        return results
    
    def _convert_ratings_to_categories(self, ratings: pd.Series) -> np.ndarray:
        """Konverter 1-5 rating til kategorier"""
        # Grupper ratings: 1-2 = 'poor', 3 = 'ok', 4-5 = 'good'
        categories = []
        for rating in ratings:
            if rating <= 2:
                categories.append('poor')
            elif rating == 3:
                categories.append('ok')
            else:
                categories.append('good')
        
        # Label encode
        if self.label_encoder is None:
            self.label_encoder = LabelEncoder()
            encoded = self.label_encoder.fit_transform(categories)
        else:
            encoded = self.label_encoder.transform(categories)
        
        return encoded
    
    def _get_model(self, model_type: str):
        """Få modell basert på type"""
        if model_type == 'random_forest':
            return RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42
            )
        elif model_type == 'gradient_boosting':
            return GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                random_state=42
            )
        elif model_type == 'xgboost' and HAS_XGBOOST:
            return xgb.XGBClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                random_state=42
            )
        else:
            # Fallback til random forest
            return RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
    
    def _get_feature_importance(self, model, feature_names) -> Dict[str, float]:
        """Få feature importance fra modell"""
        if hasattr(model, 'feature_importances_'):
            importance = model.feature_importances_
            return dict(zip(feature_names, importance.tolist()))
        return {}
    
    def predict_spot_ratings(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prediker rating for alle spots basert på værdata
        
        Args:
            weather_data: Dict med værdata for prediksjon
            
        Returns:
            Dict med prediksjoner per spot
        """
        if self.model is None:
            return {'error': 'Ingen modell trent ennå'}
        
        # Hent alle spots
        spots_df = pd.read_sql_query(
            "SELECT * FROM surf_spots", 
            self.processor.engine
        )
        
        predictions = {}
        
        for _, spot in spots_df.iterrows():
            # Lag feature vector for dette spot
            feature_vector = self._create_prediction_features(weather_data, spot)
            
            if feature_vector is not None:
                # Prediker
                prob = self.model.predict_proba([feature_vector])[0]
                pred_class = self.model.predict([feature_vector])[0]
                
                # Konverter tilbake til rating
                category = self.label_encoder.inverse_transform([pred_class])[0]
                
                predictions[spot['name']] = {
                    'predicted_category': category,
                    'probabilities': {
                        label: float(prob[i]) 
                        for i, label in enumerate(self.label_encoder.classes_)
                    },
                    'confidence': float(max(prob))
                }
        
        return predictions
    
    def _create_prediction_features(self, weather_data: Dict, spot: pd.Series) -> Optional[np.ndarray]:
        """Lag feature vector for prediksjon"""
        try:
            # Basis features fra weather_data
            features = {}
            
            # Direkte weather features
            features['wave_height'] = weather_data.get('wave_height', 0.5)
            features['wave_period'] = weather_data.get('wave_period', 8.0)
            features['wind_speed'] = weather_data.get('wind_speed', 5.0)
            features['air_temperature'] = weather_data.get('air_temperature', 12.0)
            features['wave_direction'] = weather_data.get('wave_direction', 270.0)
            features['wind_direction'] = weather_data.get('wind_direction', 270.0)
            
            # Beregn avledede features
            features['offshore_wind'] = self._calculate_offshore_wind(
                features['wind_direction'], spot['orientation']
            )
            
            features['swell_component'] = self._calculate_swell_component(
                features['wave_height'], features['wave_direction'], spot['orientation']
            )
            
            angle_diff = abs(features['wave_direction'] - spot['orientation'])
            if angle_diff > 180:
                angle_diff = 360 - angle_diff
            features['swell_angle_difference'] = angle_diff
            
            # Temporal features (fra current time)
            now = datetime.now()
            features['hour'] = now.hour
            features['month'] = now.month
            features['weekday'] = now.weekday()
            features['is_weekend'] = now.weekday() >= 5
            
            # Cycliske features
            features['season_sin'] = np.sin(2 * np.pi * now.month / 12)
            features['season_cos'] = np.cos(2 * np.pi * now.month / 12)
            features['hour_sin'] = np.sin(2 * np.pi * now.hour / 24)
            features['hour_cos'] = np.cos(2 * np.pi * now.hour / 24)
            features['weekday_sin'] = np.sin(2 * np.pi * now.weekday() / 7)
            features['weekday_cos'] = np.cos(2 * np.pi * now.weekday() / 7)
            
            # Spot features
            features['spot_sin'] = np.sin(np.radians(spot['orientation']))
            features['spot_cos'] = np.cos(np.radians(spot['orientation']))
            
            # Wind components
            features['wind_north'] = np.cos(np.radians(features['wind_direction'])) * features['wind_speed']
            features['wind_east'] = np.sin(np.radians(features['wind_direction'])) * features['wind_speed']
            
            # Wave components
            features['wave_north'] = np.cos(np.radians(features['wave_direction'])) * features['wave_height']
            features['wave_east'] = np.sin(np.radians(features['wave_direction'])) * features['wave_height']
            
            # Wave energy
            features['wave_energy'] = (features['wave_height'] ** 2) * features['wave_period']
            
            # Spot dummies
            for spot_name in ['Bore', 'Orre', 'Hellestø', 'Sola Strand', 'Reve', 'Sirevåg']:
                features[f'spot_{spot_name}'] = 1 if spot['name'] == spot_name else 0
            
            # Default values for missing historical features
            features['session_number'] = 100  # Assume some experience
            features['days_since_last_session'] = 7  # Week since last
            features['spot_rating_30d'] = 3.0  # Neutral
            features['sessions_last_30d'] = 2.0  # Some activity
            features['has_precipitation'] = 0
            
            # Konverter til array i riktig rekkefølge
            feature_vector = []
            for feature_name in self.feature_names:
                if feature_name in features:
                    feature_vector.append(features[feature_name])
                else:
                    # Default value for missing feature
                    feature_vector.append(0.0)
            
            return np.array(feature_vector)
            
        except Exception as e:
            print(f"Feil ved creating prediction features: {e}")
            return None
    
    def _calculate_offshore_wind(self, wind_direction: float, spot_orientation: float) -> bool:
        """Beregn om vind er offshore"""
        angle_diff = abs(wind_direction - spot_orientation)
        if angle_diff > 180:
            angle_diff = 360 - angle_diff
        return angle_diff <= 90
    
    def _calculate_swell_component(self, wave_height: float, wave_direction: float, spot_orientation: float) -> float:
        """Beregn swell component"""
        angle_diff = abs(wave_direction - spot_orientation)
        if angle_diff > 180:
            angle_diff = 360 - angle_diff
        return wave_height * np.cos(np.radians(angle_diff))
    
    def save_model(self, filepath: str = "../ml/trained_model.pkl"):
        """Lagre trent modell til fil"""
        if self.model is None:
            raise ValueError("Ingen modell å lagre")
        
        model_data = {
            'model': self.model,
            'feature_names': self.feature_names,
            'model_type': self.model_type,
            'label_encoder': self.label_encoder,
            'saved_at': datetime.now().isoformat()
        }
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
    
    def load_model(self, filepath: str = "../ml/trained_model.pkl") -> bool:
        """Last inn trent modell fra fil"""
        try:
            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)
            
            self.model = model_data['model']
            self.feature_names = model_data['feature_names']
            self.model_type = model_data['model_type']
            self.label_encoder = model_data['label_encoder']
            
            return True
        except Exception as e:
            print(f"Feil ved lasting av modell: {e}")
            return False

if __name__ == "__main__":
    # Test training
    processor = SurfDataProcessor()
    trainer = SurfModelTrainer(processor)
    
    print("Trener modell...")
    results = trainer.train_model()
    
    if results['success']:
        print(f"Modell trent med {results['samples']} samples")
        print(f"Cross-validation accuracy: {results['cv_accuracy_mean']:.3f} ± {results['cv_accuracy_std']:.3f}")
        
        # Lagre modell
        trainer.save_model()
        print("Modell lagret!")
        
        # Test prediksjon
        test_weather = {
            'wave_height': 1.2,
            'wave_period': 9.0,
            'wave_direction': 270,
            'wind_speed': 8.0,
            'wind_direction': 90,
            'air_temperature': 15.0
        }
        
        predictions = trainer.predict_spot_ratings(test_weather)
        print("\nTest prediksjoner:")
        for spot, pred in predictions.items():
            print(f"{spot}: {pred['predicted_category']} (confidence: {pred['confidence']:.3f})")
    
    else:
        print(f"Kunne ikke trene modell: {results['message']}")
