import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = os.environ.get("DATABASE_PATH", str(BASE_DIR / "currency_data.db"))

# Free and reliable open exchange rate endpoint supporting GMD, EUR, GBP, USD and 160+ currencies
API_BASE_URL = os.environ.get("API_BASE_URL", "https://open.er-api.com/v6/latest")

# Cache expiration in seconds (default 3600 = 1 hour)
CACHE_DURATION_SECONDS = int(os.environ.get("CACHE_DURATION_SECONDS", 3600))

# Popular currencies with a focus on The Gambia & international trade
POPULAR_CURRENCIES = [
    {"code": "GMD", "name": "Gambian Dalasi", "symbol": "D", "flag": "🇬🇲"},
    {"code": "USD", "name": "US Dollar", "symbol": "$", "flag": "🇺🇸"},
    {"code": "EUR", "name": "Euro", "symbol": "€", "flag": "🇪🇺"},
    {"code": "GBP", "name": "British Pound", "symbol": "£", "flag": "🇬🇧"},
    {"code": "XOF", "name": "Senegalese CFA Franc (CFA)", "symbol": "CFA", "flag": "🇸🇳"},
    {"code": "NGN", "name": "Nigerian Naira", "symbol": "₦", "flag": "🇳🇬"},
    {"code": "GNF", "name": "Guinean Franc", "symbol": "FG", "flag": "🇬🇳"},
    {"code": "SLE", "name": "Sierra Leonean Leone", "symbol": "Le", "flag": "🇸🇱"},
    {"code": "GHS", "name": "Ghanaian Cedi", "symbol": "GH₵", "flag": "🇬🇭"},
    {"code": "MAD", "name": "Moroccan Dirham", "symbol": "DH", "flag": "🇲🇦"},
    {"code": "CAD", "name": "Canadian Dollar", "symbol": "CA$", "flag": "🇨🇦"},
    {"code": "CNY", "name": "Chinese Yuan", "symbol": "¥", "flag": "🇨🇳"},
    {"code": "CHF", "name": "Swiss Franc", "symbol": "CHF", "flag": "🇨🇭"},
    {"code": "TRY", "name": "Turkish Lira", "symbol": "₺", "flag": "🇹🇷"},
    {"code": "AED", "name": "UAE Dirham", "symbol": "AED", "flag": "🇦🇪"},
    {"code": "SAR", "name": "Saudi Riyal", "symbol": "SR", "flag": "🇸🇦"},
    {"code": "JPY", "name": "Japanese Yen", "symbol": "¥", "flag": "🇯🇵"},
    {"code": "INR", "name": "Indian Rupee", "symbol": "₹", "flag": "🇮🇳"},
    {"code": "AUD", "name": "Australian Dollar", "symbol": "A$", "flag": "🇦🇺"},
]

ALL_CURRENCY_METADATA = {item["code"]: item for item in POPULAR_CURRENCIES}
