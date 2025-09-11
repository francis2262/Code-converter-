from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal
import httpx
import re

app = FastAPI()

# Allow browser calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the frontend
app.mount("/", StaticFiles(directory="static", html=True), name="static")

# ---- Request schema ----
class ConvertRequest(BaseModel):
    code: str
    from_platform: Literal["sportybet", "bet9ja"]
    to_platform: Literal["sportybet", "bet9ja"]

# ---- Demo dataset ----
SAMPLE_CODES = {
    "BJ99999": {"legs": [
        {"home": "Barcelona", "away": "Real Madrid", "market": "O/U 2.5", "pick": "OVER", "odds": 1.95}
    ]}
}

# ---- Market mapping ----
MARKET_MAP = {
    ("sportybet", "1X2"): "Match Result",
    ("sportybet", "GG"): "Both Teams To Score",
    ("sportybet", "O/U 2.5"): "Over/Under 2.5 Goals",
    ("bet9ja", "Match Result"): "1X2",
    ("bet9ja", "Both Teams To Score"): "GG",
    ("bet9ja", "Over/Under 2.5 Goals"): "O/U 2.5",
}

# ---- SportyBet Fetch ----
async def fetch_sportybet_slip(code: str) -> dict:
    url = f"https://www.sportybet.com/ng/m/sporty/booking?bookingCode={code}"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, timeout=15.0)
        if r.status_code != 200:
            return None
        text = r.text

        # Very rough parsing (for MVP)
        matches = re.findall(r'>(.*?) vs (.*?)<', text)
        slip = {"legs": []}
        for home, away in matches:
            slip["legs"].append({
                "home": home.strip(),
                "away": away.strip(),
                "market": "Unknown",
                "pick": "?",
                "odds": None
            })
        return slip if slip["legs"] else None

# ---- Conversion logic ----
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
async def convert(req: ConvertRequest):
    if req.from_platform == req.to_platform:
        return {"ok": False, "message": "From/To platforms are the same.", "converted_code": None, "preview": None}

    slip = None
    if req.from_platform == "sportybet":
        slip = await fetch_sportybet_slip(req.code)
    elif req.code in SAMPLE_CODES:
        slip = SAMPLE_CODES[req.code]

    if not slip:
        return {"ok": False, "message": "Code not found or could not fetch.", "converted_code": None, "preview": None}

    preview = fake_convert_slip(slip, req.from_platform, req.to_platform)
    converted_code = fake_generate_code(req.to_platform, req.code)

    return {"ok": True, "message": "Converted (with fetch).", "converted_code": converted_code, "preview": preview}

@app.get("/api/health")
def health():
    return {"status": "ok"}
