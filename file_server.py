#!/usr/bin/env python3
"""
NAS Web File Server - Browse, upload, and download files from /Projects/nas
"""

from app import create_app
from app.utils import BASE_PATH

app = create_app()

if __name__ == "__main__":
    if not BASE_PATH.exists():
        print(f"Error: {BASE_PATH} does not exist. Is the drive mounted?")
        exit(1)
    app.run(host="0.0.0.0", port=8080, debug=False)
