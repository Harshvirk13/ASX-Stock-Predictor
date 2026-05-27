import pytest
from app.data_fetcher import fetch_stock_data, ASX_STOCKS
from app.predictor import predict_next_close

def test_fetch_returns_dataframe():
    df = fetch_stock_data("CBA.AX", period="3mo")
    assert not df.empty
    assert "Close" in df.columns
    assert "MA_20" in df.columns

def test_all_tickers_valid():
    assert "CBA.AX" in ASX_STOCKS
    assert len(ASX_STOCKS) == 5

def test_predict_returns_dict():
    result = predict_next_close("CBA.AX")
    assert "predicted_close" in result
    assert "mae" in result
    assert result["predicted_close"] > 0

def test_mae_reasonable():
    result = predict_next_close("BHP.AX")
    assert result["mae"] < 50  # MAE under $50 for reasonable model