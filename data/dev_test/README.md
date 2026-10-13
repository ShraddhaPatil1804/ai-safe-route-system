# Development & Test Crime Dataset (SYNTHETIC FIXTURES)

## CRITICAL NOTICE & DISCLAIMER

> [!WARNING]
> **THIS DIRECTORY CONTAINS PURELY SYNTHETIC DEVELOPMENT / TEST DATA.**
> It is generated solely to build, verify, and test the machine learning infrastructure, PostGIS spatial mapping pipelines, feature extractors, and Random Forest classification models for the Nashik city area.
> 
> - **IT IS NOT REAL CRIME DATA.**
> - **IT DOES NOT REPRESENT REAL POLICE / FIR RECORDS.**
> - **NO REAL-WORLD CRIME ACCURACY IS CLAIMED OR IMPLIED.**

---

## Future Real FIR Integration Instructions

When official, verified FIR or crime statistics are obtained from authorized sources (such as Nashik City Police or State Crime Records Bureau):

1. **Format Required**:
   A CSV or SQL dump with columns:
   - `fir_number` (String, unique identifier)
   - `crime_date` (ISO timestamp `YYYY-MM-DD HH:MM:SS`)
   - `crime_type` (e.g., Harassment, Eve Teasing, Theft, Assault, Stalking, Snatching)
   - `severity_weight` (Numeric 1.0 to 5.0 derived from IPC sections)
   - `time_of_day` ('Day', 'Dusk', 'Night', 'Late Night')
   - `latitude` (Float between 19.85 and 20.15 for Nashik)
   - `longitude` (Float between 73.65 and 73.95 for Nashik)

2. **Ingestion**:
   Run `scripts/05_download_crime.py --source /path/to/real_firs.csv --production`.
   This will set `is_development_data = FALSE` on all imported records.

3. **Re-training**:
   Run:
   ```bash
   python scripts/06_feature_engineering.py
   python scripts/07_train_model.py
   python scripts/08_predict.py
   ```
   The Random Forest model will then be retrained on genuine historical data without needing any code changes to the backend or router.
