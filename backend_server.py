#!/usr/bin/env python3
"""VimLookup Backend Server - Entry point for PyInstaller bundling

This script is the entry point for the standalone backend executable.
It runs the FastAPI server in production mode.
"""

import os
import sys

# Set production mode before any imports
os.environ["VIMLOOKUP_PRODUCTION"] = "1"

# When running as a PyInstaller bundle, we need to handle the path differently
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    BASE_DIR = sys._MEIPASS
    # Add the bundled packages to path
    sys.path.insert(0, BASE_DIR)
else:
    # Running as script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(BASE_DIR, 'src'))


def main():
    import uvicorn
    from lookup.config import get_app_data_dir

    # Print startup info
    data_dir = get_app_data_dir()
    print(f"VimLookup Backend Server")
    print(f"Data directory: {data_dir}")
    print(f"Starting server on http://127.0.0.1:2989")

    # Run the server
    uvicorn.run(
        "web.backend.app:app",
        host="127.0.0.1",
        port=2989,
        log_level="info",
        # No reload in production
        reload=False,
    )


if __name__ == "__main__":
    main()
