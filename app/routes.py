"""Flask routes for NAS file server."""

from flask import (
    Blueprint,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
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
                    "path": (
                        str(item.relative_to(BASE_PATH)) if item != BASE_PATH else ""
                    ),
                    "is_dir": item.is_dir(),
                    "size_str": format_size(stat.st_size) if item.is_file() else "-",
                }
            )
        except OSError:
            continue

    parent = path.parent
    parent_rel = str(parent.relative_to(BASE_PATH)) if parent != BASE_PATH else ""
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
