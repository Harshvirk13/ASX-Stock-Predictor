from flask import Flask, jsonify
from .predictor import predict_next_close
from .data_fetcher import ASX_STOCKS
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)
REQUEST_COUNT = Counter("prediction_requests_total", "Total prediction requests", ["ticker"])

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/predict/<ticker>")
def predict(ticker):
    if ticker not in ASX_STOCKS:
        return jsonify({"error": "Unsupported ticker"}), 400
    REQUEST_COUNT.labels(ticker=ticker).inc()
    result = predict_next_close(ticker)
    return jsonify(result)

@app.route("/stocks")
def stocks():
    return jsonify({"available": ASX_STOCKS})

@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}