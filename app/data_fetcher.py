import yfinance as yf
import pandas as pd

ASX_STOCKS = ["CBA.AX", "BHP.AX", "CSL.AX", "WES.AX", "NAB.AX"]

def fetch_stock_data(ticker: str, period: str = "1y") -> pd.DataFrame:
    stock = yf.Ticker(ticker)
    df = stock.history(period=period)
    df = df[["Close", "Volume", "High", "Low"]]
    df["MA_20"] = df["Close"].rolling(20).mean()
    df["MA_50"] = df["Close"].rolling(50).mean()
    df["Return"] = df["Close"].pct_change()
    return df.dropna()