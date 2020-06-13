"""
This is a slightly modified version of Slack's events API for python
It can be found here: https://github.com/slackapi/python-slack-events-api

The only difference is that it will emit the data from a POST to this server
    even if it isn't an "event", therefore allowing one to process Slash commands
    without having to build a Flask server from the ground up
"""

from pyee import EventEmitter
from .server import SlackServer


class SlackEventAdapter(EventEmitter):
    # Initialize the Slack event server
    # If no endpoint is provided, default to listening on '/slack/events'
    def __init__(self, signing_secret, endpoint="/slack/events", server=None, **kwargs):
        EventEmitter.__init__(self)
        self.signing_secret = signing_secret
        self.server = SlackServer(signing_secret, endpoint, self, server, **kwargs)

    def start(self, host='127.0.0.1', port=None, debug=False, **kwargs):
        """
        Start the built in webserver, bound to the host and port you'd like.
        Default host is `127.0.0.1` and port 8080.

        :param host: The host you want to bind the build in webserver to
        :param port: The port number you want the webserver to run on
        :param debug: Set to `True` to enable debug level logging
        :param kwargs: Additional arguments you'd like to pass to Flask
        """
        self.server.run(host=host, port=port, debug=debug, **kwargs)
