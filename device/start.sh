#!/bin/sh
set -eu
cd /mnt/us/kindle-buddy
/mnt/us/python3/bin/python3.9 -u sync_time.py || true
exec /mnt/us/python3/bin/python3.9 -u buddy.py
