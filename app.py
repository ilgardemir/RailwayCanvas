import os
import hmac
from functools import wraps
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from flask import Flask, Response, jsonify, render_template, request

app = Flask(__name__)

BASE = os.getenv('CANVAS_BASE_URL', '').strip().rstrip('/')
TOKEN = os.getenv('CANVAS_TOKEN', '').strip()
DASHBOARD_USERNAME = os.getenv('DASHBOARD_USERNAME', '').strip()
DASHBOARD_PASSWORD = os.getenv('DASHBOARD_PASSWORD', '')


def protected(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not DASHBOARD_USERNAME or not DASHBOARD_PASSWORD:
            return 'Set DASHBOARD_USERNAME and DASHBOARD_PASSWORD in Railway Variables.', 503
        auth = request.authorization
        if not auth or not (hmac.compare_digest(auth.username or '', DASHBOARD_USERNAME)
                            and hmac.compare_digest(auth.password or '', DASHBOARD_PASSWORD)):
            return Response('Authentication required', 401, {'WWW-Authenticate': 'Basic realm="Canvas Dashboard"'})
        return view(*args, **kwargs)
    return wrapped


def settings():
    parsed = urlparse(BASE)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
        raise ValueError('Set CANVAS_BASE_URL to your Canvas site URL, e.g. https://school.instructure.com')
    if not TOKEN:
        raise ValueError('Set CANVAS_TOKEN in your environment before starting the server.')


def canvas_get(session, path, params=None):
    url = f'{BASE}/api/v1/{path}'
    rows = []
    while url:
        res = session.get(url, params=params, timeout=20)
        res.raise_for_status()
        data = res.json()
        if not isinstance(data, list):
            raise ValueError('Unexpected Canvas response')
        rows.extend(data)
        url = res.links.get('next', {}).get('url')
        if url and urlparse(url).hostname != urlparse(BASE).hostname:
            raise ValueError('Unexpected pagination URL')
        params = None
    return rows


def is_submitted(a):
    s = a.get('submission') or {}
    return bool(s.get('submitted_at') or s.get('workflow_state') in ('submitted', 'graded', 'pending_review') or s.get('excused'))


@app.route('/')
@protected
def home():
    return render_template('index.html')


@app.route('/api/dashboard')
@protected
def dashboard():
    try:
        settings()
        session = requests.Session()
        session.headers.update({'Authorization': f'Bearer {TOKEN}', 'Accept': 'application/json'})
        courses = canvas_get(session, 'courses', {'enrollment_state': 'active', 'per_page': 100})
        courses = [c for c in courses if c.get('id') and c.get('name') and c.get('workflow_state') != 'unpublished']
        items = []
        errors = []
        for course in courses:
            try:
                assignments = canvas_get(session, f"courses/{course['id']}/assignments", {'include[]': 'submission', 'per_page': 100})
                for a in assignments:
                    if not a.get('published', True):
                        continue
                    submission = a.get('submission') or {}
                    items.append({
                        'id': a.get('id'),
                        'course': course.get('name'),
                        'name': a.get('name', 'Untitled'),
                        'due_at': a.get('due_at'),
                        'url': a.get('html_url'),
                        'submitted': is_submitted(a),
                        'excused': bool(submission.get('excused')),
                        'points': a.get('points_possible'),
                        'grade': submission.get('grade'),
                        'submission_types': a.get('submission_types', []),
                    })
            except requests.RequestException as err:
                errors.append(f"Could not load {course.get('name')}: {type(err).__name__}")
        return jsonify({'courses': len(courses), 'assignments': items, 'warnings': errors, 'updated_at': datetime.now(timezone.utc).isoformat()})
    except requests.HTTPError as err:
        status = err.response.status_code if err.response is not None else 502
        message = 'Canvas denied the request (401/403). Check your token and permissions.' if status in (401, 403) else f'Canvas returned HTTP {status}.'
        return jsonify({'error': message}), 502
    except (requests.RequestException, ValueError) as err:
        return jsonify({'error': str(err)}), 502


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
