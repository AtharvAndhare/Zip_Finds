"""
Single entry point — starts both the Flask API and the Vite dev server.

Usage:
    python start.py

Press Ctrl+C to stop both.
"""

import subprocess
import sys
import os
import signal
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(ROOT, "frontend")

procs = []


def kill_all():
    for p in procs:
        try:
            p.terminate()
        except Exception:
            pass
    # Give them a moment, then force-kill
    time.sleep(1)
    for p in procs:
        try:
            p.kill()
        except Exception:
            pass


def main():
    print("=" * 55)
    print("  Zip Finds AI — Starting Backend + Frontend")
    print("=" * 55)

    # --- 1. Start Flask API (port 5000) ---
    print("\n[1/2] Starting Flask API on http://localhost:5000 ...")
    flask_proc = subprocess.Popen(
        [sys.executable, "-m", "api.server"],
        cwd=ROOT,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    procs.append(flask_proc)

    # Give Flask a second to boot
    time.sleep(2)

    # --- 2. Start Vite dev server (port 3000) ---
    print("[2/2] Starting Vite frontend on http://localhost:3000 ...")
    # Use npm.cmd on Windows, npm on Unix
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    vite_proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=FRONTEND_DIR,
        env={**os.environ},
    )
    procs.append(vite_proc)

    print("\n" + "=" * 55)
    print("  App running!")
    print("  Frontend : http://localhost:3000")
    print("  Backend  : http://localhost:5000")
    print("  Press Ctrl+C to stop both.")
    print("=" * 55 + "\n")

    # Wait for either process to exit
    try:
        while True:
            # Check if either crashed
            if flask_proc.poll() is not None:
                print("\n[!] Flask backend exited. Stopping...")
                break
            if vite_proc.poll() is not None:
                print("\n[!] Vite frontend exited. Stopping...")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Shutting down...")
    finally:
        kill_all()
        print("[*] Both servers stopped.")


if __name__ == "__main__":
    # Handle Ctrl+C gracefully on Windows
    signal.signal(signal.SIGINT, lambda *_: None)
    main()
