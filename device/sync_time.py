#!/usr/bin/env python3
"""Best-effort startup NTP sync. Failure must never prevent the UI starting."""
import argparse
import json
from pathlib import Path
import subprocess
import time


def sync_time(servers, budget=8):
    deadline = time.monotonic() + budget
    for server in servers:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            # Unprivileged source port works on more home routers; step once at startup.
            result = subprocess.run(
                ['/usr/bin/ntpdate', '-u', '-b', '-p', '1', '-t', '2', server],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=min(4, remaining))
            detail = result.stdout.strip().replace('\n', ' ')
            if result.returncode == 0:
                print('time-sync: success server={} {}'.format(server, detail), flush=True)
                return True
            print('time-sync: failed server={} {}'.format(server, detail), flush=True)
        except subprocess.TimeoutExpired:
            print('time-sync: timeout server={}'.format(server), flush=True)
        except OSError as error:
            print('time-sync: unavailable {}'.format(error), flush=True)
            break
    print('time-sync: keeping system time; continuing offline', flush=True)
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', action='append')
    parser.add_argument('--budget', type=float, default=8)
    args = parser.parse_args()
    try:
        config = json.loads((Path(__file__).parent/'config.json').read_text())
        if not config.get('sync_time_on_start', True) and not args.server:
            print('time-sync: disabled', flush=True)
            return
        servers = args.server or config.get('ntp_servers', ['ntp.aliyun.com', 'time.cloudflare.com'])
        sync_time(servers, max(0, min(args.budget, 8)))
    except Exception as error:
        print('time-sync: keeping system time after error: {}'.format(error), flush=True)


if __name__ == '__main__':
    main()
