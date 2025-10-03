"""
Script for å eksportere surf data til ML-format (CSV/Pandas)
Dette scriptet viser hvordan du enkelt kan gjøre om database data til ML-klare format
"""
import pandas as pd
import sqlite3
from datetime import datetime
import numpy as np

def export_to_csv():
    """Eksporter surf sessions til CSV format"""
    # Koble til database
    conn = sqlite3.connect('data/surfespotvelger.db')
    
    # Hent alle sessions med spot info
    query = """
    SELECT 
        s.*,
        sp.name as spot_name,
        sp.latitude,
        sp.longitude,
        sp.orientation as spot_orientation
    FROM surf_sessions s
    JOIN surf_spots sp ON s.spot_id = sp.id
    ORDER BY s.date_time
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Lagre til CSV
    df.to_csv('ml_data/surf_sessions.csv', index=False)
    print(f"Eksportert {len(df)} sessions til ml_data/surf_sessions.csv")
    
    return df

def prepare_ml_features(df):
    """Forbered data for ML - håndter missing values og kategoriske variabler"""
    
    # Kopier dataframe
    ml_df = df.copy()
    
    # Håndter missing values
    numeric_cols = ['wave_height', 'wave_period', 'wave_direction', 'wind_speed', 
                   'wind_direction', 'air_temperature', 'water_temperature', 
                   'humidity', 'pressure', 'swell_component', 'surf_score']
    
    for col in numeric_cols:
        if col in ml_df.columns:
            ml_df[col] = ml_df[col].fillna(ml_df[col].median())
    
    # Kategoriske variabler til dummy variables
    categorical_cols = ['board_type', 'season', 'time_of_day', 'tide_trend']
    
    for col in categorical_cols:
        if col in ml_df.columns:
            dummies = pd.get_dummies(ml_df[col], prefix=col)
            ml_df = pd.concat([ml_df, dummies], axis=1)
            ml_df.drop(col, axis=1, inplace=True)
    
    # Boolean til 0/1
    boolean_cols = ['offshore_wind']
    for col in boolean_cols:
        if col in ml_df.columns:
            ml_df[col] = ml_df[col].astype(int)
    
    # Datetime features
    ml_df['date_time'] = pd.to_datetime(ml_df['date_time'])
    ml_df['hour'] = ml_df['date_time'].dt.hour
    ml_df['month'] = ml_df['date_time'].dt.month
    ml_df['day_of_year'] = ml_df['date_time'].dt.dayofyear
    
    # Fjern kolonner som ikke er nyttige for ML
    columns_to_drop = ['id', 'notes', 'data_sources', 'yr_api_timestamp', 
                      'created_at', 'updated_at', 'forecast_lead_time']
    
    for col in columns_to_drop:
        if col in ml_df.columns:
            ml_df.drop(col, axis=1, inplace=True)
    
    return ml_df

def create_target_variable(df):
    """Lag target variable for ML (rating som prediksjon)"""
    
    # Du kan velge hvilken target du vil predikere:
    # 1. Rating (1-5) - klassifisering
    # 2. Surf score (0-10) - regresjon
    # 3. Binary: bra/dårlig (rating >= 4) - klassifisering
    
    # Eksempel 1: Rating som target
    X = df.drop(['rating', 'date_time', 'spot_name'], axis=1)
    y_rating = df['rating']
    
    # Eksempel 2: Surf score som target
    if 'surf_score' in df.columns:
        X_score = df.drop(['surf_score', 'date_time', 'spot_name'], axis=1)
        y_score = df['surf_score']
    
    # Eksempel 3: Binary target (bra surf eller ikke)
    y_binary = (df['rating'] >= 4).astype(int)
    
    return X, y_rating, y_score, y_binary

def main():
    """Hovedfunksjon - eksporter og forbered data"""
    
    print("🏄‍♂️ Surf Data ML Export")
    print("=" * 40)
    
    # Eksporter data
    df = export_to_csv()
    
    print(f"\n📊 Dataset info:")
    print(f"   Antall økter: {len(df)}")
    print(f"   Kolonner: {list(df.columns)}")
    print(f"   Date range: {df['date_time'].min()} til {df['date_time'].max()}")
    
    # Forbered for ML
    ml_df = prepare_ml_features(df)
    
    # Lag target variables
    X, y_rating, y_score, y_binary = create_target_variable(ml_df)
    
    print(f"\n🤖 ML Features:")
    print(f"   Features: {X.shape[1]} kolonner")
    print(f"   Samples: {X.shape[0]} økter")
    print(f"   Target (rating): {y_rating.value_counts().to_dict()}")
    
    # Lagre ML-klare data
    import os
    os.makedirs('ml_data', exist_ok=True)
    
    # Lagre features og targets
    X.to_csv('ml_data/features.csv', index=False)
    y_rating.to_csv('ml_data/target_rating.csv', index=False, header=['rating'])
    
    if 'surf_score' in df.columns:
        y_score.to_csv('ml_data/target_surf_score.csv', index=False, header=['surf_score'])
    
    y_binary.to_csv('ml_data/target_binary.csv', index=False, header=['good_surf'])
    
    print(f"\n✅ ML data eksportert til ml_data/ mappen:")
    print(f"   - features.csv (alle features)")
    print(f"   - target_rating.csv (1-5 rating)")
    print(f"   - target_surf_score.csv (0-10 score)")
    print(f"   - target_binary.csv (bra/dårlig)")
    
    # Vis sample av data
    print(f"\n📋 Sample features:")
    print(X.head())
    
    return X, y_rating, y_score, y_binary

if __name__ == "__main__":
    X, y_rating, y_score, y_binary = main()


