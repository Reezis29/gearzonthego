#!/bin/bash
PORT="${PORT:-8080}"
echo "Starting Gearz On The Go on port $PORT"
exec gunicorn --bind "0.0.0.0:$PORT" --workers 2 --timeout 120 app:app
