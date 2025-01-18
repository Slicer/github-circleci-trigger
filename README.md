# GitHub CircleCI Trigger

A simple GitHub post-receive web hook handler able to trigger a CircleCI build.

# motivation

It is particularly useful for triggering CircleCI build using GitHub token.

# quickstart

First, from a terminal, install and start the server

```bash
# create virtualenv
$ mkvirtualenv github-circleci-trigger

# choose CircleCI project to trigger
$ export CIRCLECI_REPO=orgname/worker-with-privileges (e.g Slicer/apidocs.slicer.org)
$ export CIRCLECI_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# install server
$ git clone https://github.com/Slicer/github-circleci-trigger
$ pip install -r github-circleci-trigger/requirements.txt

# start server
$ cd github-circleci-trigger
$ export FLASK_APP="github-circleci-trigger.py"
$ export GITHUB_WEBHOOK_SECRET="This is a secret"
$ export FLASK_DEBUG="1"
$ python -m flask run
 * Serving Flask app "github-circleci-trigger"
 * Forcing debug mode on
 * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
```

Then, open the URL ``http://127.0.0.1:5000`` in your favorite browser. It should display 
``Hello World!`` on the page and report the following in your terminal:

```
127.0.0.1 - - [25/Mar/2017 04:50:48] "GET / HTTP/1.1" 200 -
```

Now, let's install [ngrok](https://ngrok.com/download) so that we can easily get a public URL
and test.

The `TOKEN` is available at https://dashboard.ngrok.com/get-started/your-authtoken

```bash
$ unzip /path/to/ngrok-v3-stable-linux-amd64.tgz
$ ngrok config add-authtoken TOKEN
$ ngrok http 5000

[...]
Forwarding https://11ab-22-33-44-555.ngrok.io -> http://localhost:5000
```

Open again the ``*.ngrok.io`` URL in your browser and it should still display ``Hello World!``.

Last, open the settings of ``orgname/open-source-project`` GitHub project and add a webhook:

 * Payload URL: ``https://11ab-22-33-44-555.ngrok.io/postreceive``
 * Content type: ``application/json``
 * Secret: ``This is a secret``
 * Let me select individual events: Check ``Push`` and ``Pull Request``

Et voila, each time a commit is pushed (or a pull request is created) on ``orgname/open-source-project`` 
our server will handle the GitHub webhook and trigger CircleCI build of ``orgname/worker-with-privileges``
project with the following parameters:

* ``SLICER_REPO_NAME``
* ``SLICER_REPO_BRANCH``
* ``SLICER_REPO_TAG``
* ``SLICER_REPO_REVISION``

# thanks

This work was inspired from there projects:
* https://github.com/razius/github-webhook-handler
* https://github.com/carlos-jenkins/python-github-webhooks

# license

It is covered by the Slicer License:

https://github.com/slicer-apidocs-builder/License.txt
