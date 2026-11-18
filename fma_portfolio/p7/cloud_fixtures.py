"""P8 hosted-only upcoming fixtures through an explicitly configured API.

This is presentation-only. It does not read Private research data, odds,
Current Data SQLite, model internals, or any owner-local fixture file.
"""
from __future__ import annotations

from datetime import datetime
import json
import os
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
import unicodedata

from fma_portfolio.eligibility import load_policy

COMPETITIONS = {"E0": "PL", "D1": "BL1", "SP1": "PD", "I1": "SA", "F1": "FL1"}
TIMEZONES = {"E0": "Europe/London", "D1": "Europe/Berlin", "SP1": "Europe/Madrid",
             "I1": "Europe/Rome", "F1": "Europe/Paris"}
API_BASE = "https://api.football-data.org/v4/competitions"
MAX_BODY_BYTES = 2_000_000

# API team-name variants that differ from the validated public model roster.
# We never use fuzzy matches or silently substitute a different club.
ALIASES = {
    "E0": {
        "manchester city": "Man City", "manchester united": "Man United",
        "tottenham hotspur": "Tottenham", "nottingham forest": "Nott'm Forest",
        "brighton hove albion": "Brighton", "brighton and hove albion": "Brighton",
        "newcastle united": "Newcastle", "leeds united": "Leeds",
        "afc bournemouth": "Bournemouth", "ipswich town": "Ipswich",
        "hull city": "Hull", "coventry city": "Coventry",
    },
    "D1": {"fc bayern munchen": "Bayern Munich", "bayern munchen": "Bayern Munich",
           "borussia dortmund": "Dortmund", "bayer leverkusen": "Leverkusen",
           "borussia monchengladbach": "M'gladbach", "vfb stuttgart": "Stuttgart",
           "eintracht frankfurt": "Ein Frankfurt", "fc augsburg": "Augsburg",
           "sc freiburg": "Freiburg", "sv werder bremen": "Werder Bremen",
           "tsg 1899 hoffenheim": "Hoffenheim", "tsg hoffenheim": "Hoffenheim",
           "rb leipzig": "RB Leipzig", "fc schalke 04": "Schalke 04",
           "fc koln": "FC Koln", "1 fc koln": "FC Koln", "1 fc koeln": "FC Koln",
           "1 fsv mainz 05": "Mainz", "union berlin": "Union Berlin",
           "hamburger sv": "Hamburg", "sc paderborn 07": "Paderborn",
           "sv elversberg": "Elversberg"},
    "SP1": {"real betis balompie": "Betis", "real betis": "Betis",
            "real sociedad": "Sociedad", "atletico de madrid": "Ath Madrid",
            "atletico madrid": "Ath Madrid", "athletic club": "Ath Bilbao",
            "athletic bilbao": "Ath Bilbao", "rc celta de vigo": "Celta",
            "celta de vigo": "Celta", "rayo vallecano": "Vallecano",
            "deportivo alaves": "Alaves", "rcd espanyol": "Espanol",
            "villarreal cf": "Villarreal", "valencia cf": "Valencia",
            "real madrid cf": "Real Madrid", "fc barcelona": "Barcelona",
            "ca osasuna": "Osasuna", "getafe cf": "Getafe",
            "sevilla fc": "Sevilla", "elche cf": "Elche",
            "real racing club": "Santander", "racing santander": "Santander",
            "rc deportivo": "La Coruna", "malaga cf": "Malaga"},
    "I1": {"inter milan": "Inter", "fc internazionale milano": "Inter",
           "internazionale": "Inter", "ac milan": "Milan", "ssc napoli": "Napoli",
           "as roma": "Roma", "ss lazio": "Lazio", "ac monza": "Monza",
           "atalanta bc": "Atalanta", "acf fiorentina": "Fiorentina",
           "udinese calcio": "Udinese", "us lecce": "Lecce",
           "us sassuolo calcio": "Sassuolo", "torino fc": "Torino",
           "venezia fc": "Venezia", "frosinone calcio": "Frosinone",
           "juventus fc": "Juventus"},
    "F1": {"paris saint germain": "Paris SG", "paris saint germain fc": "Paris SG",
           "olympique de marseille": "Marseille", "olympique lyonnais": "Lyon",
           "as monaco": "Monaco", "losc lille": "Lille",
           "rc lens": "Lens", "ogc nice": "Nice", "stade rennais": "Rennes",
           "stade brestois 29": "Brest", "toulouse fc": "Toulouse",
           "rc strasbourg": "Strasbourg", "racing club de strasbourg": "Strasbourg",
           "angers sco": "Angers", "le havre ac": "Le Havre",
           "estac troyes": "Troyes", "aj auxerre": "Auxerre",
           "fc lorient": "Lorient", "paris fc": "Paris FC"},
}

class FixtureFeedUnavailable(RuntimeError):
    """Safe, public-facing refusal; no token, URL payload or hidden traceback."""


def _norm(value: str) -> str:
    val = unicodedata.normalize("NFKD", value.casefold())
    return "".join(c for c in val if c.isalnum() and not unicodedata.combining(c))


def configured_token() -> str:
    token = os.environ.get("FMA_FIXTURE_API_TOKEN", "").strip()
    if not token:
        try:
            import streamlit as st
            token = str(st.secrets.get("FMA_FIXTURE_API_TOKEN", "")).strip()
        except Exception:
            return ""
    return token if len(token) >= 16 and "\n" not in token and "\r" not in token else ""


def _canonical_index(league: str, policy: dict) -> dict[str, str]:
    names = policy["leagues"][league]["roster"]
    out = {_norm(name): name for name in names}
    for alias, canonical in policy["aliases"][league].items():
        key = _norm(alias)
        if canonical in names and key not in out:
            out[key] = canonical
    for alias, canonical in ALIASES.get(league, {}).items():
        key = _norm(alias)
        if canonical in names and key not in out:
            out[key] = canonical
    return out


def _team_name(team: Any, index: dict[str, str]) -> str | None:
    if not isinstance(team, dict):
        return None
    for field in ("shortName", "name"):
        value = team.get(field)
        if not isinstance(value, str):
            continue
        key = _norm(value)
        if key in index:
            return index[key]
        for tail in ("football club", "futbol club", "fc", "cf", "sc"):
            suffix = _norm(tail)
            if key.endswith(suffix) and key[:-len(suffix)] in index:
                return index[key[:-len(suffix)]]
    return None


def _local_match_date(utc_date: str, league: str) -> str:
    if not isinstance(utc_date, str) or not utc_date.endswith("Z"):
        raise ValueError("Invalid API kickoff time")
    value = datetime.fromisoformat(utc_date.replace("Z", "+00:00"))
    return value.astimezone(ZoneInfo(TIMEZONES[league])).date().isoformat()


def parse_api_schedule(league: str, payload: dict, *, policy: dict | None = None) -> list[dict]:
    """Only pre-match scheduled matches with *exact* roster name mapping survive."""
    if league not in COMPETITIONS:
        raise ValueError("Unsupported league")
    if not isinstance(payload, dict) or not isinstance(payload.get("matches"), list):
        raise FixtureFeedUnavailable("Unexpected fixture feed response")
    policy = policy or load_policy()
    index = _canonical_index(league, policy)
    rows = {}
    for raw in payload["matches"]:
        if not isinstance(raw, dict) or raw.get("status") not in ("SCHEDULED", "TIMED"):
            continue
        home = _team_name(raw.get("homeTeam"), index)
        away = _team_name(raw.get("awayTeam"), index)
        if not home or not away or home == away:
            continue  # fail closed on unknown club names, never invent aliases
        try:
            match_date = _local_match_date(raw["utcDate"], league)
        except (KeyError, ValueError, TypeError):
            continue
        if not "2026-07-01" <= match_date < "2027-07-01":
            continue
        key = (match_date, home, away)
        rows[key] = {"league": league, "fixture_date": match_date,
                     "home": home, "away": away,
                     "canonical_home": home, "canonical_away": away}
    return [rows[key] for key in sorted(rows)]


def fetch_api_schedule(league: str, *, api_token: str, fetcher: Callable | None = None) -> list[dict]:
    if league not in COMPETITIONS:
        raise ValueError("Unsupported league")
    if len(api_token.strip()) < 16:
        raise FixtureFeedUnavailable("Fixture provider is not configured")
    endpoint = f"{API_BASE}/{COMPETITIONS[league]}/matches?season=2026"
    req = Request(endpoint, headers={"X-Auth-Token": api_token, "Accept": "application/json",
                                     "User-Agent": "FMA-Public-FixturePicker/1.0"})
    open_fn = fetcher or urlopen
    try:
        with open_fn(req, timeout=12) as response:
            content = response.read(MAX_BODY_BYTES + 1)
        if len(content) > MAX_BODY_BYTES:
            raise FixtureFeedUnavailable("Fixture feed response too large")
        payload = json.loads(content.decode("utf-8"))
        return parse_api_schedule(league, payload)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, UnicodeError) as exc:
        raise FixtureFeedUnavailable("Fixture feed temporarily unavailable") from exc


def manual_team_choices(league: str) -> list[tuple[str, str]]:
    """Hosted fallback uses only already public club eligibility metadata."""
    if league not in COMPETITIONS:
        return []
    try:
        roster = load_policy()["leagues"][league]["roster"]
        return [(name, name) for name in sorted(roster, key=str.casefold)]
    except (OSError, ValueError, KeyError, TypeError):
        return []
