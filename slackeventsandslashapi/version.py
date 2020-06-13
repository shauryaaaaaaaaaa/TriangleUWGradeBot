# see: http://legacy.python.org/dev/peps/pep-0440/#public-version-identifiers
"""
This is a slightly modified version of Slack's events API for python
It can be found here: https://github.com/slackapi/python-slack-events-api

The only difference is that it will emit the data from a POST to this server
    even if it isn't an "event", therefore allowing one to process Slash commands
    without having to build a Flask server from the ground up
"""

__version__ = '2.1.0'
