from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
import numpy as np
from .data_fetcher import fetch_stock_data

def train_model(ticker: str):
    df = fetch_stock_data(ticker)
    features = ["MA_20", "MA_50", "Volume", "High", "Low", "Return"]
    X = df[features].values
    y = df["Close"].shift(-1).dropna().values
    X = X[:-1]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    return model, mae, preds[-1]

def predict_next_close(ticker: str) -> dict:
    model, mae, next_price = train_model(ticker)
    return {
        "ticker": ticker,
        "predicted_close": round(float(next_price), 2),
        "mae": round(mae, 4),
        "note": "Prediction based on available data"
    }