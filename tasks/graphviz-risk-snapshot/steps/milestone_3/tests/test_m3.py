#!/usr/bin/env python3
import hashlib
import hmac
import json
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime


SNAPSHOT_SECRET = 'snapshot-secret-test'
SERVER_SCRIPT = '/app/solve3.js'
GRAPH_URL = 'http://localhost:8080/api/graphviz'
ADVISORY_URL = 'http://localhost:8080/api/advisory'
TOKEN_URL = 'http://localhost:8080/api/jwt-token'
WORKER_SCRIPT = '/app/worker.js'


class TestMilestone3:
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

    def _get_json(self, url, timeout=5, token=None):
        headers = {}
        if token is not None:
            headers['Authorization'] = token
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8'))

    def _post_json(self, payload, token=None):
        headers = {'Content-Type': 'application/json'}
        if token is not None:
            headers['Authorization'] = token

        request = urllib.request.Request(
            ADVISORY_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method='POST',
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                body = response.read().decode('utf-8')
                return response.status, json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8')
            return e.code, json.loads(body) if body else {}

    def test_token_endpoint_and_advisory_endpoint_use_bare_authorization_header(self):
        proc = self._start_server()
        try:
            token_payload = self._get_json(TOKEN_URL)
            assert isinstance(token_payload, dict)
            token = token_payload.get('token')
            assert isinstance(token, str) and token.strip()
            assert not token.startswith('Bearer ')

            status, data = self._post_json({'advisory': []}, token=token)
            assert status < 400
            assert data.get('success', False)
        finally:
            self._stop_server(proc)

    def test_graphviz_snapshot_matches_canonical_payload(self):
        proc = self._start_server()
        worker = subprocess.Popen(['node', WORKER_SCRIPT], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            time.sleep(5)
            token_payload = self._get_json(TOKEN_URL)
            assert isinstance(token_payload, dict)
            token = token_payload.get('token')
            assert isinstance(token, str) and token.strip()

            data = self._get_json(GRAPH_URL, token=token)
            advisories = self._get_json(ADVISORY_URL, token=token)

            assert set(data.keys()) == {'generatedAt', 'findings', 'edges', 'sign'}
            assert isinstance(advisories, list)
            assert isinstance(data['generatedAt'], str)
            datetime.fromisoformat(data['generatedAt'].replace('Z', '+00:00'))

            findings = data['findings']
            assert isinstance(findings, list)
            assert findings, 'expected at least one advisory in the snapshot'
            for finding in findings:
                assert isinstance(finding, dict)
                assert isinstance(finding.get('advisoryId'), str) and finding['advisoryId']
                assert isinstance(finding.get('name'), str) and finding['name']
                assert isinstance(finding.get('age'), str) and finding['age']
                assert isinstance(finding.get('severity'), str) and finding['severity']

            edges = data['edges']
            assert isinstance(edges, list)
            assert all(isinstance(edge, list) and len(edge) == 2 for edge in edges)

            payload = json.dumps(
                {
                    'generatedAt': data['generatedAt'],
                    'findings': data['findings'],
                    'edges': data['edges'],
                },
                separators=(',', ':'),
            )
            signature = hmac.new(SNAPSHOT_SECRET.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).hexdigest()
            assert signature == data['sign']
        finally:
            if worker.poll() is None:
                worker.terminate()
                worker.wait(timeout=2)
                time.sleep(0.5)
            self._stop_server(proc)
