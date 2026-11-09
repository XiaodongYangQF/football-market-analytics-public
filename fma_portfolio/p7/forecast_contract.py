"""P7.2 input validation contract. No private scientific model is bundled."""
from __future__ import annotations
from datetime import date
from math import isfinite
from typing import Any

SUPPORTED_LEAGUES = {'E0', 'D1', 'SP1', 'I1', 'F1'}

class InvalidForecastInput(ValueError):
    pass


def validate_request(fields: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(fields, dict):
        raise InvalidForecastInput('Invalid request')
    league = fields.get('league')
    if league not in SUPPORTED_LEAGUES:
        raise InvalidForecastInput('Select a supported competition')
    home, away = fields.get('home'), fields.get('away')
    if not all(isinstance(x, str) and 1 <= len(x.strip()) <= 100 for x in (home, away)):
        raise InvalidForecastInput('Provide both teams (up to 100 characters each)')
    if home.strip().casefold() == away.strip().casefold():
        raise InvalidForecastInput('Home and away teams must differ')
    when = fields.get('fixture_date')
    if isinstance(when, date):
        when = when.isoformat()
    try:
        when = date.fromisoformat(when).isoformat()
    except (ValueError, TypeError):
        raise InvalidForecastInput('Invalid fixture date') from None
    keys = ('ah_line', 'ah_home_odds', 'ah_away_odds', 'asian_line',
            'asian_over_odds', 'asian_under_odds', 'fixed_over_odds', 'fixed_under_odds')
    numbers = {}
    for key in keys:
        raw = fields.get(key)
        if raw is None or isinstance(raw, bool):
            raise InvalidForecastInput(f'Provide a valid value for {key}')
        try:
            value = float(raw)
        except (TypeError, ValueError, OverflowError):
            raise InvalidForecastInput(f'Provide a valid value for {key}') from None
        if not isfinite(value):
            raise InvalidForecastInput(f'Value must be finite: {key}')
        numbers[key] = value
    for key in keys:
        if 'odds' in key and not 1.01 <= numbers[key] <= 1000.0:
            raise InvalidForecastInput(f'Decimal odds must be between 1.01 and 1000: {key}')
    if not 0.5 <= numbers['asian_line'] <= 6.0:
        raise InvalidForecastInput('Main Asian Total line must be between 0.5 and 6.0')
    for key in ('ah_line', 'asian_line'):
        grid = numbers[key] / 0.25
        if abs(grid - round(grid)) > 1e-9:
            raise InvalidForecastInput(f'Market line must use 0.25 steps: {key}')
    return {'league': league, 'home': home.strip(), 'away': away.strip(),
            'fixture_date': when, **numbers}

