from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import pandas as pd
import numpy as np
import joblib
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = FastAPI(title="Live Pest Detection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load model & scaler
model = joblib.load("model.pkl")
scaler = joblib.load("scaler.pkl")

HOURLY_URL = "https://power.larc.nasa.gov/api/temporal/hourly/point"
DAILY_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"


# --------------------------------------------------
# SAFE WEATHER FETCH (NEVER CRASHES)
# --------------------------------------------------

def fetch_weather_safe(lat, lon):
    try:
        end = datetime.utcnow()
        start = end - timedelta(days=5)

        params = {
            "parameters": "T2M,RH2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN",
            "community": "AG",
            "latitude": lat,
            "longitude": lon,
            "start": start.strftime("%Y%m%d"),
            "end": end.strftime("%Y%m%d"),
            "format": "JSON"
        }

        # Try hourly
        try:
            res = requests.get(HOURLY_URL, params=params, timeout=5)
            data = res.json().get("properties", {}).get("parameter", {})

            if data:
                df = pd.DataFrame({
                    "temperature": data.get("T2M", {}),
                    "humidity": data.get("RH2M", {}),
                    "rainfall": data.get("PRECTOTCORR", {}),
                    "solar_radiation": data.get("ALLSKY_SFC_SW_DWN", {})
                })

                df = df.replace(-999, np.nan).dropna()
                if not df.empty:
                    return df.tail(1).astype(float)

        except:
            pass

        # Try daily fallback
        res = requests.get(DAILY_URL, params=params, timeout=5)
        data = res.json().get("properties", {}).get("parameter", {})

        df = pd.DataFrame({
            "temperature": data.get("T2M", {}),
            "humidity": data.get("RH2M", {}),
            "rainfall": data.get("PRECTOTCORR", {}),
            "solar_radiation": data.get("ALLSKY_SFC_SW_DWN", {})
        })

        df = df.replace(-999, np.nan).dropna()

        if not df.empty:
            return df.tail(1).astype(float)

    except:
        pass

    # 🔥 FINAL FALLBACK (IF EVERYTHING FAILS)
    return pd.DataFrame([{
        "temperature": 25.0,
        "humidity": 60.0,
        "rainfall": 0.0,
        "solar_radiation": 200.0
    }])


# --------------------------------------------------
# SAFE LOCATION LOOKUP (OPTIONAL)
# --------------------------------------------------

def get_location_safe(lat, lon):
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {"lat": lat, "lon": lon, "format": "jsonv2"}
        headers = {"User-Agent": "pest-detection-app"}

        res = requests.get(url, params=params, headers=headers, timeout=3)
        data = res.json()

        return data.get("display_name", "Location Found")

    except:
        return "Location lookup unavailable"


# --------------------------------------------------
# MAIN PREDICTION ENDPOINT
# --------------------------------------------------

@app.get("/predict")
def predict_pest(lat: float, lon: float):

    # 1️⃣ Always fetch weather safely
    df = fetch_weather_safe(lat, lon)

    # 2️⃣ Ensure correct feature order
    features = ["temperature", "humidity", "rainfall", "solar_radiation"]

    for col in features:
        if col not in df.columns:
            df[col] = 0.0  # auto-fill missing

    X = df[features].values

    # 3️⃣ Safe scaling
    try:
        X_scaled = scaler.transform(X)
    except:
        X_scaled = X  # if scaler fails, use raw values

    # 4️⃣ Safe prediction
    try:
        prediction = model.predict(X_scaled)[0]

        if hasattr(model, "predict_proba"):
            confidence = float(model.predict_proba(X_scaled)[0][1])
        else:
            confidence = float(prediction)

    except:
        prediction = 0
        confidence = 0.5

    prediction = int(prediction)

    # 5️⃣ Risk level
    if confidence > 0.7:
        risk = "HIGH"
    elif confidence >= 0.4:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    # 6️⃣ Optional location lookup
    location_name = get_location_safe(lat, lon)

    return {
        "location": {
            "latitude": lat,
            "longitude": lon,
            "name": location_name
        },
        "pest_risk": prediction,
        "risk_level": risk,
        "confidence": round(confidence, 3),
        "weather_used": df.iloc[0].to_dict()
    }



@app.get("/")
def home():
    return {"message": "Live Pest Detection API running 🚀"}
