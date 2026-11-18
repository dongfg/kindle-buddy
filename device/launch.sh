#!/bin/sh
set -eu
if [ "$(id -u)" -ne 0 ]; then
    exec /var/local/mkk/su -c '/bin/sh /mnt/us/kindle-buddy/launch.sh'
fi
if [ -f /tmp/kindle-buddy.pid ] && kill -0 "$(cat /tmp/kindle-buddy.pid)" 2>/dev/null; then
    exit 0
fi
# Return to the library launcher promptly; let its own drawing finish first.
nohup sh -c 'sleep 3; exec sh /mnt/us/kindle-buddy/start.sh' \
    > /mnt/us/kindle-buddy/buddy.log 2>&1 < /dev/null &
