#!/bin/sh
set -eu
if [ -f /tmp/kindle-buddy.pid ]; then
    kill -TERM "$(cat /tmp/kindle-buddy.pid)"
fi
