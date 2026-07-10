#!/usr/bin/env python3
import json
import subprocess
import time
import urllib.error
import urllib.request

import jwt


SERVER_SCRIPT = '/app/solve2.js'
URL = 'http://localhost:8080/api/advisory'
TOKEN_URL = 'http://localhost:8080/api/jwt-token'
WORKER_SCRIPT = '/app/worker.js'
EXPECTED_DEPENDENCIES = {'axios', 'jquery', 'lodash'}


class TestMilestone2:
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
            URL,
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

    def test_post_requires_a_valid_token_and_persists_advisories(self):
        proc = self._start_server()
        try:
            status, data = self._post_json({'advisory': []})
            assert status >= 400
            assert not data.get('success', False)

            token_payload = self._get_json(TOKEN_URL)
            assert isinstance(token_payload, dict)
            token = token_payload.get('token')
            assert isinstance(token, str) and token.strip()

            decoded = jwt.decode(token, options={'verify_signature': False})
            assert isinstance(decoded, dict)

            status, data = self._post_json({'advisory': []}, token=token)
            assert status < 400
            assert data.get('success', False)

            advisories = self._get_json(URL)
            assert isinstance(advisories, list)
        finally:
            self._stop_server(proc)

    def test_worker_fetches_and_submits_advisories_for_all_ledgered_dependencies(self):
        proc = self._start_server()
        worker = subprocess.Popen(['node', WORKER_SCRIPT], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            time.sleep(5)
            advisories = self._get_json(URL)

            assert isinstance(advisories, list)
            assert advisories, 'expected at least one advisory to be submitted'

            submitted_names = set()
            advisory_ids = set()
            for advisory in advisories:
                assert isinstance(advisory, dict)
                assert isinstance(advisory.get('advisoryId'), str) and advisory['advisoryId']
                assert isinstance(advisory.get('name'), str) and advisory['name']
                assert isinstance(advisory.get('age'), str) and advisory['age']
                assert isinstance(advisory.get('severity'), str) and advisory['severity']

                submitted_names.add(advisory['name'])
                assert advisory['advisoryId'] not in advisory_ids
                advisory_ids.add(advisory['advisoryId'])

            assert submitted_names >= EXPECTED_DEPENDENCIES
        finally:
            if worker.poll() is None:
                worker.terminate()
                worker.wait(timeout=2)
                time.sleep(0.5)
            self._stop_server(proc)
