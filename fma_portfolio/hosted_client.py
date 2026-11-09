"""Disabled-by-default hosted P7 forecast transport; no private model is bundled.

Only server-side Streamlit code can read the token. Access is restricted to
allowlisted OIDC identities; anonymous browser sessions cannot call this API.
"""
from __future__ import annotations

import ipaddress
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener

from .p7.forecast_contract import validate_request
from .p7.owner_local import _clean_projection, ForecastUnavailable


class HostedConfigurationError(ValueError):
    pass


class _NoRedirect(HTTPRedirectHandler):
    """Never forward a private gateway token to another origin."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _open_no_redirect(req: Request, timeout_seconds: int):
    return build_opener(_NoRedirect()).open(req, timeout=timeout_seconds)


def _endpoint(base: str, *, allow_loopback_http: bool = False) -> str:
    try:
        parts = urlsplit(base.strip())
        hostname = parts.hostname or ''
        port = parts.port
    except (ValueError, AttributeError) as exc:
        raise HostedConfigurationError('Invalid hosted forecast endpoint') from exc
    if parts.username or parts.password or parts.query or parts.fragment or parts.path not in ('', '/'):
        raise HostedConfigurationError('Hosted endpoint must be an origin without credentials, path or query')
    if not hostname or any(c.isspace() for c in hostname):
        raise HostedConfigurationError('Missing gateway host')
    if parts.scheme == 'http':
        if not (allow_loopback_http and hostname in ('localhost', '127.0.0.1', '::1')):
            raise HostedConfigurationError('Hosted gateway requires HTTPS')
    elif parts.scheme == 'https':
        if hostname in ('localhost', '127.0.0.1', '::1') or hostname.endswith('.local'):
            raise HostedConfigurationError('Production HTTPS gateway cannot be a local host')
        try:
            ip = ipaddress.ip_address(hostname)
        except ValueError:
            pass
        else:
            if not ip.is_global:
                raise HostedConfigurationError('Gateway cannot use private or loopback IP')
    else:
        raise HostedConfigurationError('Unsupported hosted gateway protocol')
    authority = parts.netloc
    if not authority or port == 0:
        raise HostedConfigurationError('Invalid hosted gateway port')
    return f'{parts.scheme}://{authority.rstrip("/")}/v1/forecast'


def _config(environ: dict | None = None) -> tuple[str, str, set[str]] | None:
    env = os.environ if environ is None else environ
    if env.get('FMA_HOSTED_FORECAST_ENABLED') != '1':
        return None
    token = env.get('FMA_HOSTED_FORECAST_API_TOKEN', '')
    allowed = {email.strip().casefold() for email in env.get('FMA_HOSTED_ALLOWED_EMAILS','').split(',') if email.strip()}
    if len(token) < 32 or any(c in token for c in '\r\n') or not allowed or any('@' not in email for email in allowed):
        raise HostedConfigurationError('Hosted forecast requires a token and OIDC email allowlist')
    url = _endpoint(env.get('FMA_HOSTED_FORECAST_API_URL',''),
                    allow_loopback_http=env.get('FMA_HOSTED_ALLOW_LOOPBACK_HTTP') == '1')
    return url, token, allowed


def hosted_configured() -> bool:
    try:
        return _config() is not None
    except HostedConfigurationError:
        return False


def hosted_authorized(user: object) -> bool:
    """Accept only an authenticated Streamlit OIDC user in the server process."""
    try:
        cfg = _config()
        if cfg is None or not bool(getattr(user, 'is_logged_in', False)):
            return False
        email = getattr(user, 'email', '')
        return isinstance(email,str) and email.casefold() in cfg[2]
    except (HostedConfigurationError, AttributeError, RuntimeError, TypeError):
        return False


def predict_hosted(request: dict, *, timeout_seconds: int = 1150) -> dict:
    """Called exclusively from the authenticated server-side Streamlit handler."""
    cfg = _config()
    if cfg is None:
        raise ForecastUnavailable('Hosted forecast pilot is disabled')
    if not 2 <= timeout_seconds <= 1200:
        raise ValueError('Invalid hosted forecast timeout')
    url, token, _ = cfg
    payload = json.dumps({'request':validate_request(request)}, allow_nan=False, separators=(',',':')).encode('utf-8')
    req = Request(url, data=payload, headers={'Authorization': 'Bearer '+token,
                  'Content-Type': 'application/json', 'Accept': 'application/json'}, method='POST')
    try:
        with _open_no_redirect(req, timeout_seconds) as resp:
            if resp.status != 200 or resp.headers.get('Content-Type','').split(';')[0].strip().lower() != 'application/json':
                raise ForecastUnavailable('Hosted prediction service returned an invalid response')
            blob = resp.read(4097)
    except (HTTPError, URLError, OSError, TimeoutError) as exc:
        raise ForecastUnavailable('Hosted prediction service is unavailable or over quota') from exc
    if len(blob) > 4096:
        raise ForecastUnavailable('Hosted prediction response is too large')
    try:
        result = json.loads(blob.decode('utf-8'))
        if not isinstance(result,dict) or set(result) != {'ok','result'} or result['ok'] is not True:
            raise ValueError('Malformed hosted result')
        return _clean_projection(result['result'])
    except (ValueError, UnicodeError, KeyError, TypeError, ForecastUnavailable) as exc:
        raise ForecastUnavailable('Hosted prediction service returned an invalid model projection') from exc
