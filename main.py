from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal

app = FastAPI()

# Allow browser calls (safe defaults)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the frontend (make sure "static" folder exists or comment this out)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

# --- Simple MVP conversion logic ---
class ConvertRequest(BaseModel):
    code: str
    from_platform: Literal["sportybet", "bet9ja"]
    to_platform:   Literal["sportybet", "bet9ja"]

# A tiny demo dictionary to prove end-to-end flow.
SAMPLE_CODES = {
    # SportyBet -> slip structure (fake demo)
    "SP12345": {"legs": [
        {"home": "Arsenal", "away": "Chelsea", "market": "1X2", "pick": "HOME", "odds": 1.85},
        {"home": "Man Utd", "away": "Liverpool", "market": "GG", "pick": "YES", "odds": 1.70}
    ]},
    # Bet9ja -> slip structure (fake demo)
    "BJ99999": {"legs": [
        {"home": "Barcelona", "away": "Real Madrid", "market": "O/U 2.5", "pick": "OVER", "odds": 1.95}
    ]}
}

# Market name mapping
MARKET_MAP = {
    ("sportybet", "1X2"): "Match Result",
    ("sportybet", "GG"): "Both Teams To Score",
    ("sportybet", "O/U 2.5"): "Over/Under 2.5 Goals",
    ("bet9ja", "Match Result"): "1X2",
    ("bet9ja", "Both Teams To Score"): "GG",
    ("bet9ja", "Over/Under 2.5 Goals"): "O/U 2.5",
}

def fake_convert_slip(slip: dict, from_plat: str, to_plat: str) -> dict:
    legs_out = []
    for leg in slip.get("legs", []):
        market_in = leg.get("market", "")
        key = (from_plat, market_in)
        mapped_market = MARKET_MAP.get(key, market_in)
        legs_out.append({**leg, "market": mapped_market})
    return {"legs": legs_out}

def fake_generate_code(to_plat: str, source_code: str) -> str:
    prefix = "BJ" if to_plat == "bet9ja" else "SP"
    return f"{prefix}{abs(hash(source_code)) % 100000:05d}"

@app.post("/api/convert")
def convert(req: ConvertRequest):
    if req.from_platform == req.to_platform:
        return {
            "ok": False,
            "message": "From/To platforms are the same.",
            "converted_code": None,
            "preview": None
        }

    slip = SAMPLE_CODES.get(req.code)
    if not slip:
        return {
            "ok": False,
            "message": "Code not found in demo dataset. Try SP12345 or BJ99999.",
            "converted_code": None,
            "preview": None
        }

    preview = fake_convert_slip(slip, req.from_platform, req.to_platform)
    converted_code = fake_generate_code(req.to_platform, req.code)

    return {
        "ok": True,
        "message": "Converted (demo).",
        "converted_code": converted_code,
        "preview": preview
    }

@app.get("/api/health")
def health():
    return {"status": "ok"}
