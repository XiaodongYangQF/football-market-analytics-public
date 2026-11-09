"""P8.1C transport/security tests. Stubs are NOT model parity evidence."""
from __future__ import annotations

import http.client
import json
from pathlib import Path
import socket
import threading
from types import SimpleNamespace
from urllib.error import URLError
import pytest

from fma_portfolio.hosted_client import (
    _endpoint,_config,HostedConfigurationError,hosted_authorized,predict_hosted,
)
from fma_portfolio.hosted_gateway import GatewayState, LoopbackGateway
from fma_portfolio.p7.owner_local import ForecastUnavailable, execute_frozen_worker

REQ={
  'league':'E0','home':'Liverpool','away':'Fulham','fixture_date':'2026-11-21',
  'ah_line':-1.0,'ah_home_odds':1.93,'ah_away_odds':1.95,
  'asian_line':2.75,'asian_over_odds':1.9,'asian_under_odds':1.96,
  'fixed_over_odds':1.82,'fixed_under_odds':2.02,
}
RESULT={'ah':{'status':'FORECAST','direction':'HOME','stake_u':1.0},
        'ou':{'status':'NO_SIGNAL','direction':None,'stake_u':None}}
TOKEN='test-only-secret-token-with-more-than-32-characters'


def test_hosted_endpoint_fail_closed():
    for url in ('http://fma.example.com','https://user:password@fma.example.com',
                'https://fma.example.com/path','https://fma.example.com/?api=x',
                'https://127.0.0.1','https://192.168.0.9','file:///etc/passwd',
                'https://fma.example.com:99999','https://localhost'):
        with pytest.raises(HostedConfigurationError):_endpoint(url)
    assert _endpoint('https://inference.example.com')=='https://inference.example.com/v1/forecast'
    assert _endpoint('http://127.0.0.1:8765',allow_loopback_http=True)=='http://127.0.0.1:8765/v1/forecast'
    with pytest.raises(HostedConfigurationError):_endpoint('http://127.0.0.1:8765')


def test_hosted_user_requires_identity_and_explicit_opt_in(monkeypatch):
    monkeypatch.delenv('FMA_HOSTED_FORECAST_ENABLED', raising=False)
    assert not hosted_authorized(SimpleNamespace(is_logged_in=True,email='owner@example.com'))
    monkeypatch.setenv('FMA_HOSTED_FORECAST_ENABLED','1')
    monkeypatch.setenv('FMA_HOSTED_FORECAST_API_URL','https://fma.example.com')
    monkeypatch.setenv('FMA_HOSTED_FORECAST_API_TOKEN',TOKEN)
    monkeypatch.setenv('FMA_HOSTED_ALLOWED_EMAILS','Owner@Example.com')
    assert hosted_authorized(SimpleNamespace(is_logged_in=True,email='owner@example.com'))
    assert not hosted_authorized(SimpleNamespace(is_logged_in=False,email='owner@example.com'))
    assert not hosted_authorized(SimpleNamespace(is_logged_in=True,email='visitor@example.com'))
    assert not hosted_authorized(None)
    monkeypatch.delenv('FMA_HOSTED_FORECAST_API_TOKEN')
    assert not hosted_authorized(SimpleNamespace(is_logged_in=True,email='owner@example.com'))


def test_hosted_client_handles_valid_projection_and_masks_worker_errors(monkeypatch):
    monkeypatch.setenv('FMA_HOSTED_FORECAST_ENABLED','1')
    monkeypatch.setenv('FMA_HOSTED_FORECAST_API_URL','https://model.example.com')
    monkeypatch.setenv('FMA_HOSTED_FORECAST_API_TOKEN',TOKEN)
    monkeypatch.setenv('FMA_HOSTED_ALLOWED_EMAILS','owner@example.com')
    class FakeResponse:
        status=200
        headers={'Content-Type':'application/json'}
        def __init__(self,payload):self.payload=payload
        def read(self,n):return self.payload[:n]
        def __enter__(self):return self
        def __exit__(self,*args):pass
    def fake_urlopen(req,timeout):
        assert req.get_method()=='POST'
        assert req.full_url=='https://model.example.com/v1/forecast'
        assert req.get_header('Authorization')=='Bearer '+TOKEN
        assert json.loads(req.data)=={'request':REQ}
        return FakeResponse(json.dumps({'ok':True,'result':RESULT}).encode())
    monkeypatch.setattr('fma_portfolio.hosted_client._open_no_redirect', fake_urlopen)
    assert predict_hosted(REQ)==RESULT
    monkeypatch.setattr('fma_portfolio.hosted_client._open_no_redirect',lambda *args,**kwargs:FakeResponse(b'{"ok":true,"result":{"debug":"SECRET"}}'))
    with pytest.raises(ForecastUnavailable):predict_hosted(REQ)
    monkeypatch.setattr('fma_portfolio.hosted_client._open_no_redirect',lambda *args,**kwargs:(_ for _ in ()).throw(URLError('private path')))
    with pytest.raises(ForecastUnavailable,match='unavailable'):predict_hosted(REQ)


class running_gateway:
    def __init__(self,state):self.state=state
    def __enter__(self):
        self.server=LoopbackGateway(0,self.state)
        assert self.server.server_address[0]=='127.0.0.1'
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        return self.server
    def __exit__(self,*args):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=2)


def post(server,request=REQ,*,token=TOKEN,ctype='application/json'):
    connection=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
    body=json.dumps({'request':request})
    headers={'Content-Type':ctype}
    if token is not None:headers['Authorization']='Bearer '+token
    connection.request('POST','/v1/forecast',body=body,headers=headers)
    response=connection.getresponse()
    status=response.status
    payload=json.loads(response.read())
    connection.close()
    return status,payload


def test_gateway_auth_quota_and_projection():
    counter=[]
    clock=[100.]
    state=GatewayState(token=TOKEN,executor=lambda req: (counter.append(req), RESULT)[1],
                       max_per_hour=1,cooldown_seconds=0,clock=lambda:clock[0])
    with running_gateway(state) as server:
        assert post(server,token=None)[0]==401
        assert post(server,token='wrong-token')[0]==401
        assert post(server,ctype='text/plain')[0]==415
        assert post(server,request={})[0]==400
        assert post(server,request={**REQ,'private_file':'/etc/passwd'})[0]==400
        assert post(server,request={**REQ,'home':'Home\nUnauthorized: x'})[0]==400
        assert not counter
        assert post(server)==(200,{'ok':True,'result':RESULT})
        assert post(server)==(429,{'error':'quota'})
        assert len(counter)==1
        clock[0]=3701.
        assert post(server)[0]==200


def test_gateway_refuses_parallel_execution_and_exceptions():
    entered=threading.Event()
    proceed=threading.Event()
    def blocked(req):
        entered.set();proceed.wait(timeout=4);return RESULT
    state=GatewayState(token=TOKEN,executor=blocked,max_per_hour=3,cooldown_seconds=0)
    outputs=[]
    with running_gateway(state) as server:
        worker=threading.Thread(target=lambda:outputs.append(post(server)))
        worker.start();assert entered.wait(timeout=3)
        assert post(server)==(503,{'error':'busy'})
        proceed.set();worker.join(timeout=3)
        assert outputs==[(200,{'ok':True,'result':RESULT})]
    with running_gateway(GatewayState(token=TOKEN,executor=lambda req: (_ for _ in ()).throw(RuntimeError('absolute secret path')),cooldown_seconds=0)) as server:
        assert post(server)==(503,{'error':'model_unavailable'})


def test_gateway_rejects_oversized_body_before_worker():
    with running_gateway(GatewayState(token=TOKEN,executor=lambda req:RESULT)) as server:
        conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
        conn.request('POST','/v1/forecast',body='x'*5000,headers={'Authorization':'Bearer '+TOKEN,'Content-Type':'application/json'})
        resp=conn.getresponse(); assert resp.status==413
        resp.read();conn.close()


def test_frozen_executor_uses_original_protocol_with_stub(tmp_path):
    worker=tmp_path/'model_worker.py'
    worker.write_text('''import json,sys
request=json.loads(sys.stdin.read())
assert request['league']=='E0'
print(json.dumps({'ok':True,'result':{'ah':{'status':'FORECAST','direction':'HOME','stake_u':1.0},'ou':{'status':'NO_SIGNAL','direction':None,'stake_u':None}}}))
''')
    import sys
    assert execute_frozen_worker(REQ, project=tmp_path, science=tmp_path, data=tmp_path,
                                 worker=worker,executable=sys.executable,timeout_seconds=5)==RESULT


def test_gateway_source_does_not_contain_private_model(tmp_path):
    root=Path(__file__).resolve().parents[1]
    assert not (root/'fma_portfolio/p7/model_worker.py').exists()
    assert not (root/'backend').exists()


def test_hosted_client_to_loopback_gateway_real_transport(monkeypatch):
    from fma_portfolio.hosted_client import predict_hosted
    with running_gateway(GatewayState(token=TOKEN,executor=lambda req:RESULT,
                                      cooldown_seconds=0)) as server:
        monkeypatch.setenv('FMA_HOSTED_FORECAST_ENABLED','1')
        monkeypatch.setenv('FMA_HOSTED_FORECAST_API_URL',f'http://127.0.0.1:{server.server_port}')
        monkeypatch.setenv('FMA_HOSTED_ALLOW_LOOPBACK_HTTP','1')
        monkeypatch.setenv('FMA_HOSTED_FORECAST_API_TOKEN',TOKEN)
        monkeypatch.setenv('FMA_HOSTED_ALLOWED_EMAILS','owner@example.com')
        assert predict_hosted(REQ,timeout_seconds=3)==RESULT
        monkeypatch.delenv('FMA_HOSTED_ALLOW_LOOPBACK_HTTP')
        with pytest.raises(HostedConfigurationError):predict_hosted(REQ,timeout_seconds=3)


def test_hosted_client_refuses_http_redirects():
    import urllib.error
    from fma_portfolio.hosted_client import _open_no_redirect
    from urllib.request import Request
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    class Redirect(BaseHTTPRequestHandler):
        def do_POST(self):
            self.send_response(302);self.send_header('Location','http://127.0.0.1/steal')
            self.end_headers()
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Redirect)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        req=Request(f'http://127.0.0.1:{server.server_port}/v1/forecast',data=b'{}',
                    headers={'Authorization':'Bearer '+TOKEN})
        with pytest.raises(urllib.error.HTTPError) as err:
            _open_no_redirect(req,2)
        assert err.value.code==302
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)
