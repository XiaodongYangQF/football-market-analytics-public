"""P7.4 forecast snapshots, user exports and LOCAL-only durable archive.

The archive is NOT an official settled performance ledger. No visitor records
are written to server disk in cloud mode; only the loopback P7.2 preview
launcher can opt into the owner-only local archive.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import io
import json
import math
from pathlib import Path
import re
import uuid

from .forecast_contract import validate_request, InvalidForecastInput

SCHEMA = 'FMA_PUBLIC_WEB_FORECAST_ARCHIVE_V1'
POLICY = 'PUBLIC_V2_AH_A_OU_B_REVERSED_1U'
MAX_ROWS = 10000
MAX_IMPORT_BYTES = 4_000_000

EXPORT_FIELDS = (
    'record_id','saved_at_utc','fixture_date','competition','home_team','away_team',
    'ah_line','ah_home_odds','ah_away_odds','asian_line','asian_over_odds',
    'asian_under_odds','fixed_over_odds','fixed_under_odds',
    'ah_status','ah_direction','ah_stake_u','ou_status','ou_direction','ou_stake_u',
    'policy_version',
)
TEXT_FIELDS = ('competition','home_team','away_team')
INPUT_FIELDS = ('ah_line','ah_home_odds','ah_away_odds','asian_line','asian_over_odds',
                'asian_under_odds','fixed_over_odds','fixed_under_odds')

class SavedForecastsError(ValueError):
    pass


def _text(value: object, limit: int = 120) -> str:
    if not isinstance(value,str) or not (1 <= len(value.strip()) <= limit):
        raise SavedForecastsError('Invalid record text')
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise SavedForecastsError('Control characters are not allowed in saved records')
    return value.strip()


def _market(item: object, name: str) -> dict:
    if not isinstance(item,dict):
        raise SavedForecastsError('Missing model market output')
    status, direction, stake = item.get('status'), item.get('direction'), item.get('stake_u')
    if status == 'FORECAST':
        choices = {'ah':('HOME','AWAY'), 'ou':('OVER','UNDER')}[name]
        if direction not in choices or type(stake) not in (float,int) or stake != 1.0:
            raise SavedForecastsError('Invalid Public V2 model output')
        return {'status':'FORECAST','direction':direction,'stake_u':1.0}
    if status == 'NO_SIGNAL' and direction is None and stake is None:
        return {'status':'NO_SIGNAL','direction':None,'stake_u':None}
    # Unavailable is not a successful prediction, and cannot be archived.
    raise SavedForecastsError('Only successful forecasts and NO SIGNAL results can be saved')


def create_record(request: dict, result: dict, *, competition: str,
                  display_home: str, display_away: str,
                  now: datetime | None = None, record_id: str | None = None) -> dict:
    """Snapshot exactly one validated model call; zero internal ids or paths."""
    try:
        validated = validate_request(request)
    except InvalidForecastInput as exc:
        raise SavedForecastsError(str(exc)) from exc
    if not isinstance(result,dict) or set(result) != {'ah','ou'}:
        raise SavedForecastsError('Model result is not a valid public projection')
    ah,ou=_market(result['ah'],'ah'),_market(result['ou'],'ou')
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise SavedForecastsError('Timestamp must be timezone-aware')
    instant=instant.astimezone(timezone.utc)
    identifier = str(uuid.uuid4()) if record_id is None else str(uuid.UUID(record_id))
    record={
        'record_id':identifier,
        'saved_at_utc':instant.isoformat(timespec='seconds').replace('+00:00','Z'),
        'fixture_date':validated['fixture_date'],
        'competition':_text(competition),
        'home_team':_text(display_home),
        'away_team':_text(display_away),
    }
    for name in INPUT_FIELDS:
        record[name]=float(validated[name])
    for prefix,item in (('ah',ah),('ou',ou)):
        record[f'{prefix}_status']=item['status']
        record[f'{prefix}_direction']=item['direction']
        record[f'{prefix}_stake_u']=item['stake_u']
    record['policy_version']=POLICY
    return record


def validate_saved_record(value: object) -> dict:
    if not isinstance(value,dict) or set(value)!=set(EXPORT_FIELDS):
        raise SavedForecastsError('Unrecognized saved-record fields')
    try:
        identifier=str(uuid.UUID(value['record_id']))
        when=datetime.fromisoformat(value['saved_at_utc'].replace('Z','+00:00'))
        if when.tzinfo is None or when.utcoffset() is None:
            raise ValueError('Timestamp missing timezone')
        if when.utcoffset().total_seconds()!=0:
            raise ValueError('Timestamp must be UTC')
        from datetime import date
        fixture_date=date.fromisoformat(value['fixture_date']).isoformat()
    except (ValueError,KeyError,TypeError,AttributeError) as exc:
        raise SavedForecastsError('Invalid saved record identity/date') from exc
    if value['policy_version'] != POLICY:
        raise SavedForecastsError('Unsupported policy version')
    # Revalidate all numbers via exact P7.2 contract. Teams are display names,
    # not a model re-run. Exported records must never execute a prediction.
    input_data={'league':'E0','home':'Home','away':'Away','fixture_date':fixture_date}
    for name in INPUT_FIELDS:
        number=value[name]
        if type(number) not in (float,int) or not math.isfinite(number):
            raise SavedForecastsError('Invalid odds or handicap in record')
        input_data[name]=number
    try:validate_request(input_data)
    except InvalidForecastInput as exc:raise SavedForecastsError(str(exc)) from exc
    record={'record_id':identifier,
            'saved_at_utc':when.isoformat(timespec='seconds').replace('+00:00','Z'),
            'fixture_date':fixture_date}
    for name in TEXT_FIELDS:record[name]=_text(value[name])
    for name in INPUT_FIELDS:record[name]=float(value[name])
    for market in ('ah','ou'):
        result=_market({'status':value[f'{market}_status'],
                        'direction':value[f'{market}_direction'],
                        'stake_u':value[f'{market}_stake_u']},market)
        for field in ('status','direction','stake_u'):
            record[f'{market}_{field}']=result[field]
    record['policy_version']=POLICY
    return record


def normalize_records(items: object) -> list[dict]:
    if not isinstance(items,list) or len(items)>MAX_ROWS:
        raise SavedForecastsError('Archive is not a valid bounded list')
    seen=set();records=[]
    for item in items:
        row=validate_saved_record(item)
        if row['record_id'] in seen:raise SavedForecastsError('Duplicate record ID')
        seen.add(row['record_id']);records.append(row)
    return records


def archive_json(records: list[dict]) -> bytes:
    payload={'schema':SCHEMA,'records':normalize_records(records)}
    return (json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')


def parse_archive(data: bytes) -> list[dict]:
    if not isinstance(data,bytes) or len(data)>MAX_IMPORT_BYTES:
        raise SavedForecastsError('JSON archive exceeds size limit (4MB)')
    try:payload=json.loads(data.decode('utf-8-sig'))
    except (ValueError,UnicodeError) as exc:
        raise SavedForecastsError('Unable to read JSON archive') from exc
    if not isinstance(payload,dict) or set(payload)!={'schema','records'} or payload['schema']!=SCHEMA:
        raise SavedForecastsError('Unknown JSON archive format')
    return normalize_records(payload['records'])


def merge_records(existing: list[dict], incoming: list[dict]) -> tuple[list[dict],int]:
    current=normalize_records(existing)
    more=normalize_records(incoming)
    ids={r['record_id'] for r in current}
    count=0
    for row in more:
        if row['record_id'] not in ids:
            if len(current)>=MAX_ROWS:raise SavedForecastsError('Archive limit reached')
            ids.add(row['record_id']);current.append(row);count+=1
    return current,count


def _csv_safe(value: object) -> object:
    """Prevent Excel formula interpretation in text fields on CSV opening."""
    if isinstance(value,str) and re.match(r'^\s*[=+@\-\t\r\n]',value):
        return "'"+value
    return value


def archive_csv(records: list[dict]) -> bytes:
    rows=normalize_records(records)
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=EXPORT_FIELDS)
    writer.writeheader()
    for row in rows:
        writer.writerow({key:_csv_safe(row.get(key)) for key in EXPORT_FIELDS})
    return stream.getvalue().encode('utf-8-sig')




def row_for_display(row: dict) -> dict:
    return {
        'Saved (UTC)':row['saved_at_utc'],
        'Date':row['fixture_date'],
        'Competition':row['competition'],
        'Fixture':f"{row['home_team']} vs {row['away_team']}",
        'AH':row['ah_direction'] if row['ah_status']=='FORECAST' else 'NO SIGNAL',
        'AH line':row['ah_line'],
        'OU':row['ou_direction'] if row['ou_status']=='FORECAST' else 'NO SIGNAL',
        'OU line':row['asian_line'],
    }
