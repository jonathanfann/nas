"""Flask routes for NAS file server."""

import os
import shlex
import shutil
import subprocess
from pathlib import Path

from flask import (
    Blueprint,
    current_app,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename

from app.utils import (
    BASE_PATH,
    BUCKET_NAMES,
    format_size,
    get_bucket_counts,
    get_media_type,
    get_relative_path,
    list_files_by_bucket,
    search_files,
)

bp = Blueprint("nas", __name__)


@bp.route("/")
@bp.route("/home")
def index():
    """Home: media bucket cards."""
    counts = get_bucket_counts()
    return render_template("home.html", bucket_counts=counts)


@bp.route("/search")
def search():
    """Search files. Always returns HTMX partial."""
    q = request.args.get("q", "").strip()
    page = max(1, request.args.get("page", 1, type=int))
    per_page = 50

    entries, total = search_files(q, page=page, per_page=per_page)
    total_pages = (total + per_page - 1) // per_page if total else 0

    return render_template(
        "partials/search_results.html",
        entries=entries,
        q=q,
        bucket_filter=None,
        page=page,
        total_pages=total_pages,
        total=total,
    )


@bp.route("/health")
def health():
    """Simple health endpoint for restart recovery polling."""
    return jsonify({"status": "ok"}), 200


@bp.route("/bucket/<bucket>")
def bucket(bucket):
    """List files in a media bucket."""
    bucket_lower = bucket.lower()
    if bucket_lower not in BUCKET_NAMES:
        return "Not found", 404
    if bucket != bucket_lower:
        return redirect(url_for("nas.bucket", bucket=bucket_lower))
    page = max(1, request.args.get("page", 1, type=int))
    per_page = 50

    entries, total = list_files_by_bucket(bucket_lower, page=page, per_page=per_page)
    total_pages = (total + per_page - 1) // per_page if total else 0

    template = "bucket_images.html" if bucket_lower == "images" else "bucket.html"
    response = render_template(
        template,
        bucket=bucket_lower,
        entries=entries,
        page=page,
        total_pages=total_pages,
        total=total,
    )
    # Prevent caching so card view always loads fresh after deploy
    resp = make_response(response)
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp


@bp.route("/browse/")
@bp.route("/browse/<path:subpath>")
def browse(subpath=""):
    """Browse directory or download file."""
    path = get_relative_path(subpath)
    if not path.exists():
        return "Path not found", 404
    if not path.is_dir():
        return send_from_directory(path.parent, path.name, as_attachment=True)

    per_page = 50
    page = max(1, request.args.get("page", 1, type=int))
    q = request.args.get("q", "").strip()

    all_entries = []
    for item in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
        if item.name.startswith("."):
            continue
        try:
            stat = item.stat()
            all_entries.append(
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

    total = len(all_entries)
    total_pages = (total + per_page - 1) // per_page if total else 0
    start = (page - 1) * per_page
    entries = all_entries[start : start + per_page]

    parent = path.parent
    try:
        parent_rel = str(parent.relative_to(BASE_PATH)) if parent != BASE_PATH else ""
    except ValueError:
        parent_rel = ""
    path_display = "/" + subpath if subpath else "/"
    path_upload = subpath.rstrip("/") if subpath else ""

    return render_template(
        "browse.html",
        path_display=path_display,
        path_upload=path_upload,
        parent_rel=parent_rel,
        entries=entries,
        page=page,
        total_pages=total_pages,
        total=total,
        subpath=subpath,
        q=q,
    )


@bp.route("/upload/", methods=["POST"])
@bp.route("/upload/<path:subpath>", methods=["POST"])
def upload(subpath=""):
    """Handle file uploads."""
    path = get_relative_path(subpath)
    if not path.exists() or not path.is_dir():
        return "Invalid path", 400
    redirect_to = request.form.get("redirect_to") or request.args.get("redirect_to")
    if "file" not in request.files:
        if redirect_to == "home":
            return redirect(url_for("nas.index"))
        return redirect(url_for("nas.browse", subpath=subpath))
    for file in request.files.getlist("file"):
        if file and file.filename:
            filename = secure_filename(file.filename)
            if not filename:
                continue

            if redirect_to == "home":
                bucket = get_media_type(Path(filename))
                target_dir = get_relative_path(bucket)
                if not target_dir.exists() or not target_dir.is_dir():
                    target_dir = get_relative_path("files")
                    target_dir.mkdir(parents=True, exist_ok=True)
            else:
                target_dir = path

            file.save(target_dir / filename)
    if redirect_to == "home":
        return redirect(url_for("nas.index"))
    return redirect(url_for("nas.browse", subpath=subpath))


@bp.route("/download/<path:filepath>")
def download(filepath):
    """Download a file."""
    path = get_relative_path(filepath)
    if not path.exists() or path.is_dir():
        return "Not found", 404
    return send_from_directory(path.parent, path.name, as_attachment=True)


@bp.route("/preview/<path:filepath>")
def preview(filepath):
    """Serve a file for inline display (e.g. images in img tags)."""
    path = get_relative_path(filepath)
    if not path.exists() or path.is_dir():
        return "Not found", 404
    return send_from_directory(path.parent, path.name, as_attachment=False)


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

    redirect_to = request.form.get("redirect_to") or request.args.get("redirect_to")
    if redirect_to and redirect_to.startswith("bucket:"):
        bucket = redirect_to.split(":", 1)[1]
        if bucket in BUCKET_NAMES:
            return redirect(url_for("nas.bucket", bucket=bucket))
    try:
        parent = (
            str(path.parent.relative_to(BASE_PATH)) if path.parent != BASE_PATH else ""
        )
    except ValueError:
        parent = ""
    return redirect(url_for("nas.browse", subpath=parent))


@bp.route("/restart", methods=["POST"])
def restart():
    """Restart the NAS web service and return a clear result."""
    service_name = os.environ.get("NAS_SERVICE_NAME", "nas-web")
    custom_command = os.environ.get("NAS_RESTART_COMMAND", "").strip()

    def executable_candidates(name, fallback_paths):
        found = shutil.which(name)
        candidates = []
        if found:
            candidates.append(found)
        for path in fallback_paths:
            if (
                path not in candidates
                and os.path.isfile(path)
                and os.access(path, os.X_OK)
            ):
                candidates.append(path)
        return candidates

    sudo_bins = executable_candidates("sudo", ["/usr/bin/sudo", "/bin/sudo"])
    systemctl_bins = executable_candidates(
        "systemctl", ["/usr/bin/systemctl", "/bin/systemctl"]
    )

    restart_commands = []
    if custom_command:
        restart_commands.append(shlex.split(custom_command))

    for systemctl_bin in systemctl_bins:
        for sudo_bin in sudo_bins:
            restart_commands.append(
                [sudo_bin, "-n", systemctl_bin, "restart", service_name]
            )
        restart_commands.append([systemctl_bin, "restart", service_name])
        restart_commands.append([systemctl_bin, "--user", "restart", service_name])

    if not restart_commands:
        return (
            "Restart failed. Could not find restart binaries.\n"
            "No executable 'systemctl' found in PATH or common locations.\n"
            "Set NAS_RESTART_COMMAND in your .env (example: '/usr/bin/systemctl restart nas-web').",
            500,
        )

    errors = []

    for command in restart_commands:
        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=15,
            )
            return "", 200
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            stdout = (exc.stdout or "").strip()
            details = stderr or stdout or f"exit status {exc.returncode}"
            errors.append(f"{' '.join(command)} -> {details}")
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            errors.append(f"{' '.join(command)} -> {exc}")

    current_app.logger.error(
        "Restart failed for service '%s': %s", service_name, " | ".join(errors)
    )
    return (
        "Restart failed. Ensure systemd service exists, service name is correct "
        "(NAS_SERVICE_NAME), and sudo rights are configured.\n" + "\n".join(errors),
        500,
    )
