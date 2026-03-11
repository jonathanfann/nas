# NAS File Server

A Flask web app to browse, upload, and download files from a configurable directory.

## Prerequisites

- Python 3.11+
- Node.js 20+ (optional, for linting and pre-commit hooks)

## Setup

1. **Clone the repo**

    ```bash
    git clone <your-repo-url>
    cd nas
    ```

2. **Create and activate a virtual environment**

    ```bash
    python -m venv .venv
    source .venv/bin/activate   # Linux/macOS
    # or: .venv\Scripts\activate  # Windows
    ```

3. **Install Python dependencies**

    ```bash
    pip install -r requirements.txt
    ```

4. **Configure environment**

    ```bash
    cp .env.example .env
    ```

    Edit `.env` and set `NAS_BASE_PATH` to the directory you want to serve (e.g. `/Projects/nas` or `/mnt/storage`). Create the directory if it doesn't exist.

5. **Run the server**
    ```bash
    python file_server.py
    ```
    The app listens on `http://0.0.0.0:8080`.

## Production

For production, use a WSGI server such as Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8080 "app:create_app()"
```

### Systemd service (optional)

To run as a service and use the in-app "Restart" button, create `/etc/systemd/system/nas-web.service`:

```ini
[Unit]
Description=NAS File Server
After=network.target

[Service]
User=your-user
WorkingDirectory=/path/to/nas
Environment="PATH=/path/to/nas/.venv/bin"
ExecStart=/path/to/nas/.venv/bin/gunicorn -w 4 -b 0.0.0.0:8080 "app:create_app()"
Restart=always

[Install]
WantedBy=multi-user.target
```

Then: `sudo systemctl daemon-reload && sudo systemctl enable nas-web && sudo systemctl start nas-web`

The restart endpoint requires the service to be named `nas-web` and the app user to have passwordless sudo for `systemctl restart nas-web`.

## Development

- **Lint**: `npm run lint` (ESLint + Prettier)
- **Format**: `npm run lint:fix` (auto-fix)
- **Python**: `black .` and `djlint templates --reformat`

Pre-commit hooks (Husky) run lint and security checks on staged files. Run `npm install` to enable them.
