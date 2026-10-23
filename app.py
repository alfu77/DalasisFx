from flask import Flask, render_template, request, jsonify
import math
import logging
import database
from services.currency_service import (
    fetch_exchange_rates,
    convert_currency,
    get_currency_list,
    get_popular_rates,
    validate_currency_code
)
from config import DATABASE_PATH

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# Initialize database schema on startup
with app.app_context():
    database.init_db()

@app.route("/")
def index():
    """Render the main currency converter dashboard."""
    currencies = get_currency_list()
    return render_template("index.html", currencies=currencies)

@app.route("/api/currencies", methods=["GET"])
def api_currencies():
    """Return all supported currencies with symbols, names, and country flags."""
    return jsonify({
        "status": "success",
        "currencies": get_currency_list()
    })

@app.route("/api/convert", methods=["GET"])
def api_convert():
    """
    Convert an amount from one currency to another.
    Query parameters:
      - from: Currency code (e.g. USD)
      - to: Currency code (e.g. GMD)
      - amount: Numeric value to convert
    """
    from_curr = request.args.get("from", "USD").strip().upper()
    to_curr = request.args.get("to", "GMD").strip().upper()
    amount_str = request.args.get("amount", "1")

    if not validate_currency_code(from_curr) or not validate_currency_code(to_curr):
        return jsonify({
            "status": "error",
            "message": "Invalid currency code. Codes must be 3-letter alphabetic identifiers (e.g., USD, GMD)."
        }), 400

    try:
        amount = float(amount_str)
        if not math.isfinite(amount) or amount < 0:
            return jsonify({
                "status": "error",
                "message": "Amount must be a finite, non-negative number."
            }), 400
    except ValueError:
        return jsonify({
            "status": "error",
            "message": "Amount must be a valid number."
        }), 400

    try:
        conversion = convert_currency(from_curr, to_curr, amount)
        return jsonify({
            "status": "success",
            "data": conversion
        })
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception:
        app.logger.exception("Currency conversion failed")
        return jsonify({"status": "error", "message": "Conversion failed. Please try again later."}), 502

@app.route("/api/rates", methods=["GET"])
def api_rates():
    """
    Get live/cached exchange rates for a given base currency.
    Query parameters:
      - base: Base currency code (default: USD)
      - refresh: Optional boolean flag to force refresh
    """
    base = request.args.get("base", "USD").strip().upper()
    force_refresh = request.args.get("refresh", "false").lower() == "true"

    if not validate_currency_code(base):
        return jsonify({
            "status": "error",
            "message": "Invalid base currency code."
        }), 400

    try:
        rates_data = fetch_exchange_rates(base, force_refresh=force_refresh)
        return jsonify({
            "status": "success",
            "data": rates_data
        })
    except Exception:
        app.logger.exception("Exchange-rate retrieval failed")
        return jsonify({"status": "error", "message": "Unable to retrieve exchange rates. Please try again later."}), 502

@app.route("/api/popular", methods=["GET"])
def api_popular():
    """
    Get exchange rates for popular currency pairs (USD, GMD, EUR, GBP, CFA Franc, etc.).
    Query parameters:
      - base: Base currency (default: USD)
    """
    base = request.args.get("base", "USD").strip().upper()
    if not validate_currency_code(base):
        base = "USD"

    try:
        popular = get_popular_rates(base)
        return jsonify({
            "status": "success",
            "data": popular
        })
    except Exception:
        app.logger.exception("Popular-rate retrieval failed")
        return jsonify({"status": "error", "message": "Unable to retrieve popular rates. Please try again later."}), 502

@app.route("/api/history", methods=["GET"])
def api_history():
    """Retrieve recent user conversion lookups from SQLite."""
    limit = request.args.get("limit", 10)
    try:
        limit = min(max(int(limit), 1), 50)
    except ValueError:
        limit = 10

    records = database.get_recent_conversions(limit=limit)
    return jsonify({
        "status": "success",
        "conversions": records
    })

@app.route("/api/rate-history", methods=["GET"])
def api_rate_history():
    """Retrieve rate snapshot history for a given pair (e.g., USD -> GMD)."""
    base = request.args.get("from", "USD").strip().upper()
    target = request.args.get("to", "GMD").strip().upper()

    snapshots = database.get_historical_snapshots(base, target)
    return jsonify({
        "status": "success",
        "base": base,
        "target": target,
        "history": snapshots
    })

@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    """Force refresh cache for a base currency."""
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"status": "error", "message": "Request body must be a JSON object."}), 400
    base = payload.get("base", "USD")
    if not isinstance(base, str) or not validate_currency_code(base):
        return jsonify({"status": "error", "message": "Invalid base currency code."}), 400
    base = base.strip().upper()
    try:
        data = fetch_exchange_rates(base, force_refresh=True)
        return jsonify({
            "status": "success",
            "message": f"Exchange rates for {base} refreshed successfully.",
            "data": data
        })
    except Exception:
        app.logger.exception("Exchange-rate refresh failed")
        return jsonify({"status": "error", "message": "Unable to refresh exchange rates. Please try again later."}), 502

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"status": "error", "message": "Endpoint not found"}), 404
    return render_template("index.html", currencies=get_currency_list()), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(__import__("os").environ.get("PORT", "5000")), debug=False)
