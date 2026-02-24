#!/usr/bin/env python3
"""Docker healthcheck script for garage_bin container."""

import sys
import time
from pathlib import Path

HEARTBEAT_FILE = Path("/tmp/garagecam_heartbeat")
MAX_AGE_SECONDS = 60  # Consider unhealthy if no heartbeat for 60 seconds


def main():
    if not HEARTBEAT_FILE.exists():
        print("UNHEALTHY: No heartbeat file found")
        sys.exit(1)

    try:
        mtime = HEARTBEAT_FILE.stat().st_mtime
        age = time.time() - mtime
        if age > MAX_AGE_SECONDS:
            print(f"UNHEALTHY: Heartbeat is {age:.0f}s old (max {MAX_AGE_SECONDS}s)")
            sys.exit(1)
        print(f"HEALTHY: Heartbeat {age:.0f}s ago")
        sys.exit(0)
    except Exception as e:
        print(f"UNHEALTHY: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
