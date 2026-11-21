#!/bin/sh
set -e
mkdir -p /data
chown -R app:app /data 2>/dev/null || true
exec setpriv --reuid=app --regid=app --init-groups "$@"
