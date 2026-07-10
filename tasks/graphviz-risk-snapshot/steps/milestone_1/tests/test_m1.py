#!/usr/bin/env python3
import json
import subprocess
import time
import urllib.error
import urllib.request

import jwt

JWT_SECRET = 'ringo-hope'
JWT_ISSUER = 'graphviz-risk-snapshot'
JWT_AUDIENCE = 'worker'
SERVER_SCRIPT = '/app/solve1.js'
URL = 'http://localhost:8080/api/advisory'


class TestMilestone1:
    # Test setup helpers.
    def _start_server(self):
        proc = subprocess.Popen(['node', SERVER_SCRIPT], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                with urllib.request.urlopen('http://localhost:8080/', timeout=0.5):
                    return proc
            except Exception:
                time.sleep(0.25)
        return proc

    def _stop_server(self, proc):
        if proc.poll() is not None:
            time.sleep(0.5)
            return
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        time.sleep(0.5)

    def _make_jwt(self, user='test', issuer=JWT_ISSUER, audience=JWT_AUDIENCE, secret=JWT_SECRET):
        payload = {
            'user': user,
            'iss': issuer,
            'aud': audience,
            'exp': int(time.time()) + 86400,
        }
        token = jwt.encode(payload, secret, algorithm='HS256')
        if isinstance(token, bytes):
            token = token.decode('utf-8')
        return token

    def _post_json(self, payload, token):
        request = urllib.request.Request(
            URL,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'Authorization': token},
            method='POST',
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                body = response.read().decode('utf-8')
                return response.status, json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8')
            return e.code, json.loads(body) if body else {}

    def test_invalid_jwt_claims_are_rejected(self):
        proc = self._start_server()
        try:
            for kwargs in [
                {'issuer': 'wrong'},
                {'audience': 'not-worker'},
                {'secret': 'wrong-secret'},
            ]:
                status, data = self._post_json({'advisory': []}, self._make_jwt(**kwargs))
                assert status >= 400, kwargs
                assert not data.get('success', False), kwargs
        finally:
            self._stop_server(proc)

    def test_valid_jwt_is_accepted(self):
        proc = self._start_server()
        try:
            status, data = self._post_json({'advisory': []}, self._make_jwt())
            assert status < 400
            assert data.get('success', False)
            assert data == {'success': True}
        finally:
            self._stop_server(proc)
