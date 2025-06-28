#!/bin/bash
# Start ngrok to expose the local server to the internet, allowing
# for an automated OAuth2 authentication flow via the local redirect server.
ngrok http --url=wealthy-optionally-anemone.ngrok-free.app 8080