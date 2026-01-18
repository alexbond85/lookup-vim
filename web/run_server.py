#!/usr/bin/env python3
"""VimLookup server launcher

Usage:
    python web/run_server.py           # Development mode (uses repo .cache)
    python web/run_server.py --prod    # Production mode (uses ~/Library/Application Support/VimLookup)

For Tauri packaging, use --prod flag.
"""

import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(description="VimLookup server")
    parser.add_argument(
        "--prod", "--production",
        action="store_true",
        help="Run in production mode (use OS app data directory)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=3000,
        help="Port to run the server on (default: 3000)"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)"
    )
    args = parser.parse_args()

    # Set production mode environment variable before importing app
    if args.prod:
        os.environ["VIMLOOKUP_PRODUCTION"] = "1"
        print("Starting VimLookup in PRODUCTION mode")
    else:
        print("Starting VimLookup in DEVELOPMENT mode")

    # Now import uvicorn and run
    import uvicorn
    uvicorn.run(
        "web.backend.app:app",
        host=args.host,
        port=args.port,
        reload=not args.prod,  # Hot reload only in dev mode
        log_level="info"
    )


if __name__ == "__main__":
    main()
