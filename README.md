# SurfeSpotVelger

En personlig surfing spot-anbefaler som lærer dine preferanser basert på værforhold og tidligere opplevelser.

## Konsept

Applikasjonen lar deg:
1. Logge surf-økter med rating og spot
2. Automatisk hente værdata fra YR API for hver økt
3. Bygge opp et personlig datasett over tid
4. Trene en ML-modell som kan anbefale beste spot basert på værvarsel

## Prosjektstruktur

```
/
├── backend/          # FastAPI backend
├── frontend/         # Web interface
├── data/            # Database og datafiles
├── ml/              # Machine learning pipeline
├── notebooks/       # Jupyter notebooks for analyse
└── docs/            # Dokumentasjon
```

## Kom i gang

### Forutsetninger
- Python 3.8+ installert
- Git installert

### Installasjon

1. **Klon repository:**
   ```bash
   git clone [repository-url]
   cd SurfeSpotVelger
   ```

2. **Installer avhengigheter:**
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Sett opp database:**
   ```bash
   python3 setup.py
   ```

4. **Oppdater API-konfigurasjon:**
   - Rediger `backend/weather_service.py`
   - Bytt ut epost-adressen på linje 18 med din egen

5. **Start applikasjonen:**
   ```bash
   cd backend
   python3 main.py
   ```

6. **Åpne i nettleser:**
   - Gå til `http://localhost:8000`
   - Start logging surf-økter!

### Bruk

1. **Logg surf-økter** - Hver økt får automatisk værdata fra YR
2. **Få anbefalinger** - Baseline-systemet fungerer fra dag 1
3. **Tren ML-modell** - Etter 20+ økter kan du trene personlig modell
4. **Analyser data** - Bruk Jupyter notebook i `notebooks/analysis.ipynb`

## Teknologi

- **Backend**: FastAPI, SQLAlchemy, Requests
- **Frontend**: HTML/CSS/JavaScript
- **Database**: SQLite
- **ML**: scikit-learn, pandas, numpy
- **Værdata**: YR API (met.no)
