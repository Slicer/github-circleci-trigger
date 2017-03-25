
import logging
import os

from functools import wraps

import requests

from flask import abort, Flask, request
from flask import logging as flask_logging
from github_webhook import Webhook
from ipaddress import ip_address, ip_network

app = Flask(__name__)
webhook = Webhook(app, endpoint='/postreceive', secret=os.environ.get('GITHUB_WEBHOOK_SECRET'))


@app.before_first_request
def setup_logging():
    if app.debug:
        return
    # Add handler to Flask logger to send records to gunicorn stderr.
    # https://github.com/benoitc/gunicorn/issues/379
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(flask_logging.PROD_LOG_FORMAT))
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    # ... and disable existing handlers to avoid duplicated entries
    app.config['LOGGER_HANDLER_POLICY'] = 'never'


def ip_check(func):
    @wraps(func)
    def with_ip_check(*args, **kwargs):

        if int(os.environ.get('DISABLE_IP_CHECK', False)):
            return func(*args, **kwargs)

        # Store the IP address of the requester
        request_ip = ip_address(u'{0}'.format(request.access_route[0]))

        # If GHE_ADDRESS is specified, use it as the hook_blocks.
        if os.environ.get('GHE_ADDRESS', None):
            hook_blocks = [unicode(os.environ.get('GHE_ADDRESS'))]
        # Otherwise get the hook address blocks from the API.
        else:
            hook_blocks = requests.get('https://api.github.com/meta').json()['hooks']

        # Support debugging
        if os.environ.get('FLASK_DEBUG', 0):
            hook_blocks.append(u'127.0.0.0/8')

        # Check if the POST request is from github.com or GHE
        for block in hook_blocks:
            if ip_address(request_ip) in ip_network(block):
                break  # the remote_addr is within the network range of github.
        else:
            abort(403)

        return func(*args, **kwargs)
    return with_ip_check


def circleci_new_build(source_event, payload):
    app.logger.info({
        'status': 'triggered',
        'action': 'circleci_new_build',
        'source_event': source_event,
        'payload': payload
    })

    worker_token = os.environ.get('CIRCLECI_TOKEN', None)
    if not worker_token:
        app.logger.error('CIRCLECI_TOKEN is not set')
        return
    worker_repo = os.environ.get('CIRCLECI_REPO', None)
    if not worker_repo:
        app.logger.error('CIRCLECI_REPO is not set')
        return

    api_url = 'https://circleci.com/api/v1.1/project/github/' + worker_repo

    response = requests.post(api_url, params={'circle-token': worker_token}, json={
        'build_parameters': {
            'SLICER_REPO_NAME': payload['repo'],
            'SLICER_REPO_BRANCH': payload['branch'],
            'SLICER_REPO_TAG': payload['tag'],
            'SLICER_REPO_REVISION': payload['revision'],
        }
    })
    response.raise_for_status()


@app.route('/')
@ip_check
def hello():
    # Todo: List available endpoints and supported GitHub events
    return 'Hello World!'


@webhook.hook(event_type='ping')
@ip_check
def on_ping(data):
    return 'The impossible exists only until we find a way to make it possible'


@webhook.hook(event_type='pull_request')
@ip_check
def on_pull_request(data):

    payload = {
        'repo': data['pull_request']['head']['repo']['full_name'],
        'branch': data['pull_request']['head']['ref'],
        'tag': '',
        'revision': data['pull_request']['head']['sha']
    }

    source_event = {'type': 'pull_request', 'action': data['action'], 'number': data['number']}

    if data['action'] not in ['opened', 'edited']:
        app.logger.info({
            'status': 'ignored',
            'action': 'circleci_new_build',
            'source_event': source_event,
            'payload': payload
        })
        return

    circleci_new_build(source_event, payload)


@webhook.hook(event_type='push')
@ip_check
def on_push(data):

    # Extract repo, branch and tag
    repo = data['repository']['full_name']
    branch = ''
    tag = ''
    if data['ref'].startswith('refs/tags/'):
        tag = data['ref'].lstrip('refs/tags/')
        branch = data['base_ref'].lstrip('refs/heads/')
    elif data['ref'].startswith('refs/heads/'):
        branch = data['ref'].lstrip('refs/heads/')
    else:
        app.logger.error('Unsupported ref: %s' % data['ref'])
        abort(500)

    source_event = {'type': 'push'}
    payload = {'repo': repo, 'branch': branch, 'tag': tag, 'revision': data['after']}

    # Only consider Push event associated with update to 'master' branch
    # or tags.
    if branch != 'master' and not tag:
        app.logger.info({
            'status': 'ignored',
            'action': 'circleci_new_build',
            'source_event': source_event,
            'payload': payload
        })
        return

    circleci_new_build(source_event, payload)


if __name__ == '__main__':
    app.run()
