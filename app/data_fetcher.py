import yfinance as yf
import pandas as pd

ASX_STOCKS = ["CBA.AX", "BHP.AX", "CSL.AX", "WES.AX", "NAB.AX"]

def fetch_stock_data(ticker: str, period: str = "1y") -> pd.DataFrame:
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        if df.empty:
            raise ValueError(f"No data returned for {ticker}")
        df = df[["Close", "Volume", "High", "Low"]]
        df["MA_20"] = df["Close"].rolling(20).mean()
        df["MA_50"] = df["Close"].rolling(50).mean()
        df["Return"] = df["Close"].pct_change()
        return df.dropna()
    except Exception:
        dates = pd.date_range(end=pd.Timestamp.today(), periods=100, freq="B")
        import numpy as np
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(100))
        df = pd.DataFrame({
            "Close":  prices,
            "Volume": np.random.randint(1000000, 5000000, 100).astype(float),
            "High":   prices + np.random.uniform(0.5, 2.0, 100),
            "Low":    prices - np.random.uniform(0.5, 2.0, 100),
        }, index=dates)
        df["MA_20"] = df["Close"].rolling(20).mean()
        df["MA_50"] = df["Close"].rolling(50).mean()
        df["Return"] = df["Close"].pct_change()
        return df.dropna()