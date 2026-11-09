"""Season-aware fixture-coverage checks; NO scientific model code or data here.

This is a public, frozen coverage declaration, not a general prediction of model
success. Missing policy, ambiguous teams and unknown seasons fail closed.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import json
import unicodedata

POLICY_PATH = Path(__file__).resolve().parents[1] / 'data' / 'eligibility_policy_2026_27.json'
LEAGUES = frozenset(('E0','D1','SP1','I1','F1'))
SEASON = '2026-27'


class EligibilityPolicyError(ValueError):
    """Policy file is missing, malformed or ambiguous."""


@dataclass(frozen=True)
class Eligibility:
    status: str  # ELIGIBLE, INELIGIBLE, UNVERIFIED
    reason: str
    season: str
    promoted_team: str | None = None


def _norm(name: str) -> str:
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
        return ''
    text = unicodedata.normalize('NFKD', name)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return ''.join(c for c in text.casefold() if c.isalnum())


def load_policy(path: Path | None = None) -> dict:
    """Validate exact public roster/alias schema and avoid ambiguous mappings."""
    path = path or POLICY_PATH
    try:
        if not path.is_file() or path.stat().st_size > 30_000:
            raise EligibilityPolicyError('Missing or oversized season policy')
        obj = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError, UnicodeError) as exc:
        raise EligibilityPolicyError('Unable to read season policy') from exc
    expected = {'schema','season','valid_from','valid_before','leagues','aliases','source_urls','note'}
    if (not isinstance(obj,dict) or set(obj)!=expected or
        obj['schema']!='FMA_ELIGIBILITY_POLICY_V1' or obj['season']!=SEASON or
        obj['valid_from']!='2026-07-01' or obj['valid_before']!='2027-07-01' or
        set(obj['leagues'])!=LEAGUES or set(obj['aliases'])!=LEAGUES or
        set(obj['source_urls'])!=LEAGUES):
        raise EligibilityPolicyError('Invalid season policy schema')
    counts = {'E0':(20,3),'D1':(18,3),'SP1':(20,3),'I1':(20,3),'F1':(18,2)}
    for league, (n_total,n_new) in counts.items():
        entry = obj['leagues'][league]
        if not isinstance(entry,dict) or set(entry)!={'roster','promoted'}:
            raise EligibilityPolicyError('Invalid league entry')
        roster, promoted = entry['roster'], entry['promoted']
        if not (isinstance(roster,list) and len(roster)==n_total and
                isinstance(promoted,list) and len(promoted)==n_new and
                all(isinstance(x,str) and _norm(x) for x in roster+promoted)):
            raise EligibilityPolicyError('Invalid roster or promoted teams')
        normalized = {_norm(team):team for team in roster}
        if len(normalized)!=len(roster) or not set(map(_norm,promoted)).issubset(normalized):
            raise EligibilityPolicyError('Duplicate or unknown promoted team')
        aliases = obj['aliases'][league]
        if not isinstance(aliases,dict):
            raise EligibilityPolicyError('Invalid team aliases')
        for alias, canonical in aliases.items():
            key = _norm(alias)
            if not key or canonical not in roster or (key in normalized and normalized[key]!=canonical):
                raise EligibilityPolicyError('Ambiguous alias mapping')
            normalized[key] = canonical
        url = obj['source_urls'][league]
        if not isinstance(url,str) or not url.startswith('https://'):
            raise EligibilityPolicyError('Missing promotion verification source')
    return obj


def classify_fixture(league: str, home: str, away: str, fixture_date: str | date,
                     *, policy: dict | None = None) -> Eligibility:
    """Only ELIGIBLE permits model execution. Coverage is season-specific.

    Ineligible is determined by a public promoted-team roster. Unknown team,
    unknown league, unknown season or invalid/missing policy -> UNVERIFIED.
    """
    try:
        if policy is None:
            policy = load_policy()
        when = fixture_date if isinstance(fixture_date,date) else date.fromisoformat(fixture_date)
    except (EligibilityPolicyError, ValueError, TypeError, OSError):
        return Eligibility('UNVERIFIED','ELIGIBILITY_POLICY_OR_DATE_UNAVAILABLE',SEASON)
    if league not in LEAGUES or not (date(2026,7,1) <= when < date(2027,7,1)):
        return Eligibility('UNVERIFIED','SEASON_OR_LEAGUE_NOT_COVERED',SEASON)
    values=policy['leagues'][league]
    known={_norm(x):x for x in values['roster']}
    known.update({_norm(k):v for k,v in policy['aliases'][league].items()})
    resolved=[known.get(_norm(x)) for x in (home,away)]
    promoted=set(values['promoted'])
    for name in resolved:
        if name in promoted:
            return Eligibility('INELIGIBLE','PROMOTED_TEAM_2026_27',SEASON,name)
    if None in resolved or resolved[0]==resolved[1]:
        return Eligibility('UNVERIFIED','TEAM_NOT_IN_FROZEN_ROSTER',SEASON)
    return Eligibility('ELIGIBLE','SEASON_ROSTER_CHECK_PASSED',SEASON)
