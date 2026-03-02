#!/usr/bin/env python3
"""Startup script for Railway deployment - reads PORT from environment variable."""
import os
import subprocess
import sys

port = os.environ.get('PORT', '8080')
print(f"Starting Gearz On The Go on port {port}", flush=True)

cmd = [
    sys.executable, '-m', 'gunicorn',
    '--bind', f'0.0.0.0:{port}',
    '--workers', '2',
    '--timeout', '120',
    'app:app'
]
print(f"Running: {' '.join(cmd)}", flush=True)
os.execvp(cmd[0], cmd)
