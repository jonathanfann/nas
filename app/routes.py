"""Flask routes for NAS file server."""

import shutil
import subprocess

from flask import Blueprint, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

from app.utils import BASE_PATH, format_size, get_relative_path

bp = Blueprint("nas", __name__)


@bp.route("/")
def index():
    """Redirect root to browse."""
    return redirect(url_for("nas.browse", path=""))


@bp.route("/browse/")
@bp.route("/browse/<path:subpath>")
def browse(subpath=""):
    """Browse directory or download file."""
    path = get_relative_path(subpath)
    if not path.exists():
        return "Path not found", 404
    if not path.is_dir():
        return send_from_directory(path.parent, path.name, as_attachment=True)

    entries = []
    for item in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
        if item.name.startswith("."):
            continue
        try:
            stat = item.stat()
            entries.append(
                {
                    "name": item.name,
                    "path": str(item.relative_to(BASE_PATH)) if item != BASE_PATH else "",
                    "is_dir": item.is_dir(),
                    "size_str": format_size(stat.st_size) if item.is_file() else "-",
                }
            )
        except OSError:
            continue

    parent = path.parent
    try:
        parent_rel = (
            str(parent.relative_to(BASE_PATH)) if parent != BASE_PATH else ""
        )
    except ValueError:
        parent_rel = ""  # parent is outside BASE_PATH (e.g. at root)
    path_display = "/" + subpath if subpath else "/"
    path_upload = subpath.rstrip("/") if subpath else ""

    return render_template(
        "browse.html",
        path_display=path_display,
        path_upload=path_upload,
        parent_rel=parent_rel,
        entries=entries,
    )


@bp.route("/upload/", methods=["POST"])
@bp.route("/upload/<path:subpath>", methods=["POST"])
def upload(subpath=""):
    """Handle file uploads."""
    path = get_relative_path(subpath)
    if not path.exists() or not path.is_dir():
        return "Invalid path", 400
    if "file" not in request.files:
        return redirect(url_for("nas.browse", path=subpath))
    for file in request.files.getlist("file"):
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(path / filename)
    return redirect(url_for("nas.browse", path=subpath))


@bp.route("/download/<path:filepath>")
def download(filepath):
    """Download a file."""
    path = get_relative_path(filepath)
    if not path.exists() or path.is_dir():
        return "Not found", 404
    return send_from_directory(path.parent, path.name, as_attachment=True)


@bp.route("/delete/<path:filepath>", methods=["POST"])
def delete(filepath):
    """Delete a file or directory."""
    path = get_relative_path(filepath)
    if not path.exists():
        return "Not found", 404
    if path == BASE_PATH:
        return "Cannot delete NAS root", 400
    try:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    except OSError as e:
        return str(e), 500
    try:
        parent = (
            str(path.parent.relative_to(BASE_PATH))
            if path.parent != BASE_PATH
            else ""
        )
    except ValueError:
        parent = ""
    return redirect(url_for("nas.browse", path=parent))


@bp.route("/restart", methods=["POST"])
def restart():
    """Restart the NAS web service."""
    try:
        subprocess.run(
            ["sudo", "systemctl", "restart", "nas-web"],
            check=True,
            capture_output=True,
            timeout=10,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return "Restart failed", 500
    return redirect(url_for("nas.browse", path=""))
