import io
import logging
import math
import os
import zipfile

from flask import Blueprint, Response, jsonify, request, send_from_directory
from flask_jwt_extended import jwt_required

from api.config import Config
from api.decorators import admin_required
from api.models import Photo
from api.printer import PrinterManager

photos_bp = Blueprint("photos", __name__)
logger = logging.getLogger(__name__)

_PHOTOS_ABS = os.path.abspath(Config.PHOTOS_DIR)


def _raw_filename(filename: str) -> str:
    return filename.replace(".jpg", "_raw.jpg")


def _zip_entries(photos, want_raw: bool) -> list[tuple[str, str]]:
    """Retourne la liste (chemin source, nom dans l'archive) des fichiers existants."""
    entries = []
    for p in photos:
        filepath = os.path.join(Config.PHOTOS_DIR, p.filename)
        if want_raw:
            raw_fname = _raw_filename(p.filename)
            raw_path = os.path.join(Config.PHOTOS_DIR, raw_fname)
            # Si la version brute existe, l'utiliser ; sinon fallback sur la version filtrée
            src_path = raw_path if os.path.exists(raw_path) else filepath
            arcname = raw_fname
        else:
            src_path, arcname = filepath, p.filename
        if os.path.exists(src_path):
            entries.append((src_path, arcname))
    return entries


class _ChunkSink(io.RawIOBase):
    """Flux en écriture seule, non seekable : zipfile y écrit, le générateur vide les octets."""

    def __init__(self):
        self._chunks: list[bytes] = []

    def writable(self):
        return True

    def write(self, b):
        self._chunks.append(bytes(b))
        return len(b)

    def drain(self) -> bytes:
        data = b"".join(self._chunks)
        self._chunks.clear()
        return data


_ZIP_READ_CHUNK = 1024 * 1024


def _stream_zip(entries: list[tuple[str, str]]):
    """Génère un ZIP à la volée, sans le construire en mémoire ni sur disque.

    Deflate niveau 1 : les JPEG ne se compressent quasiment pas, le niveau minimal coûte
    peu de CPU au Pi. On garde deflate (plutôt que stored) car c'est le format streaming
    (data descriptors) le mieux supporté par les outils de décompression.
    """
    sink = _ChunkSink()
    with zipfile.ZipFile(sink, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as zf:
        for src_path, arcname in entries:
            try:
                zinfo = zipfile.ZipInfo.from_file(src_path, arcname)  # conserve la date de la photo
                zinfo.compress_type = zipfile.ZIP_DEFLATED
                zinfo.compress_level = 1
                with open(src_path, "rb") as src, zf.open(zinfo, "w") as dst:
                    while chunk := src.read(_ZIP_READ_CHUNK):
                        dst.write(chunk)
                        if data := sink.drain():
                            yield data
            except FileNotFoundError:
                # Photo supprimée entre le listing et la lecture : on l'ignore
                logger.warning("File %s vanished during zip export", src_path)
            if data := sink.drain():
                yield data
    if data := sink.drain():
        yield data


def _zip_response(entries: list[tuple[str, str]], download_name: str) -> Response:
    return Response(
        _stream_zip(entries),
        mimetype="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{download_name}"'},
    )


def _photo_dict(p: Photo) -> dict:
    raw_path = os.path.join(Config.PHOTOS_DIR, _raw_filename(p.filename))
    return {
        "id": p.id,
        "filename": p.filename,
        "mask_id": p.mask_id,
        "orientation": p.orientation,
        "captured_at": p.captured_at.isoformat(),
        "printed": p.printed,
        "raw_available": os.path.exists(raw_path),
    }


@photos_bp.route("/photos", methods=["GET"])
@jwt_required()
def list_photos():
    """Liste les photos paginées, de la plus récente à la plus ancienne.

    Query params:
        page (int, défaut 1) — numéro de page (1-indexé)
    """
    total = Photo.select().count()
    pages = max(1, math.ceil(total / Config.PHOTO_PAGE_SIZE))
    page = max(1, min(request.args.get("page", 1, type=int), pages))

    photos = (
        Photo.select()
        .order_by(Photo.captured_at.desc())
        .paginate(page, Config.PHOTO_PAGE_SIZE)
    )
    return jsonify({
        "photos": [_photo_dict(p) for p in photos],
        "page": page,
        "pages": pages,
        "total": total,
        "page_size": Config.PHOTO_PAGE_SIZE,
    })


@photos_bp.route("/photos/<int:photo_id>", methods=["GET"])
@jwt_required()
def get_photo(photo_id):
    """Détail d'une photo."""
    photo = Photo.get_or_none(Photo.id == photo_id)
    if not photo:
        return jsonify({"error": "Photo introuvable"}), 404
    return jsonify(_photo_dict(photo))


@photos_bp.route("/photos/<int:photo_id>", methods=["DELETE"])
@admin_required
def delete_photo(photo_id):
    """Supprime une photo du disque et de la base (admin uniquement)."""
    photo = Photo.get_or_none(Photo.id == photo_id)
    if not photo:
        return jsonify({"error": "Photo introuvable"}), 404

    for fname in [photo.filename, _raw_filename(photo.filename)]:
        try:
            os.remove(os.path.join(Config.PHOTOS_DIR, fname))
        except FileNotFoundError:
            pass

    photo.delete_instance()
    return jsonify({"message": "Photo supprimée"}), 200


@photos_bp.route("/photos/<int:photo_id>/file", methods=["GET"])
def serve_photo(photo_id):
    """Sert le fichier JPEG d'une photo.

    Query params:
        raw (bool, défaut false) — si true, sert la version sans masque si disponible
    """
    photo = Photo.get_or_none(Photo.id == photo_id)
    if not photo:
        return jsonify({"error": "Photo introuvable"}), 404

    if request.args.get("raw", "false").lower() == "true":
        raw_fname = _raw_filename(photo.filename)
        if os.path.exists(os.path.join(Config.PHOTOS_DIR, raw_fname)):
            return send_from_directory(_PHOTOS_ABS, raw_fname, mimetype="image/jpeg")

    return send_from_directory(_PHOTOS_ABS, photo.filename, mimetype="image/jpeg")


@photos_bp.route("/photos/<int:photo_id>/print", methods=["POST"])
@jwt_required()
def print_photo(photo_id):
    """Envoie une photo à l'imprimante.

    Query params:
        raw (bool, défaut false) — si true, imprime la version sans masque
    """
    want_raw = request.args.get("raw", "false").lower() == "true"
    photo = Photo.get_or_none(Photo.id == photo_id)
    if not photo:
        return jsonify({"error": "Photo introuvable"}), 404

    if want_raw:
        raw_fname = _raw_filename(photo.filename)
        raw_path = os.path.join(Config.PHOTOS_DIR, raw_fname)
        filepath = raw_path if os.path.exists(raw_path) else os.path.join(Config.PHOTOS_DIR, photo.filename)
    else:
        filepath = os.path.join(Config.PHOTOS_DIR, photo.filename)

    try:
        pm = PrinterManager()
        pm.imprimer_image(Config.PRINTER_NAME, filepath, sans_bordure=True)
        photo.printed = True
        photo.save()
        return jsonify({"message": "Impression lancée", "printed": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@photos_bp.route("/photos/download-selection", methods=["POST"])
@jwt_required()
def download_selection():
    """Télécharge un ZIP d'une sélection de photos.

    Body JSON:
        ids  (list[int]) — liste des IDs de photos
        raw  (bool, défaut false) — si true, inclut les versions brutes
    """
    data = request.get_json() or {}
    ids = data.get("ids", [])
    want_raw = data.get("raw", False)

    photos = [p for p in (Photo.get_or_none(Photo.id == pid) for pid in ids) if p]
    return _zip_response(_zip_entries(photos, want_raw), "selection.zip")


@photos_bp.route("/photos/delete-selection", methods=["POST"])
@admin_required
def delete_selection():
    """Supprime une sélection de photos (admin uniquement).

    Body JSON:
        ids (list[int]) — liste des IDs à supprimer
    """
    data = request.get_json() or {}
    ids = data.get("ids", [])

    deleted = []
    for photo_id in ids:
        p = Photo.get_or_none(Photo.id == photo_id)
        if p:
            for fname in [p.filename, _raw_filename(p.filename)]:
                try:
                    os.remove(os.path.join(Config.PHOTOS_DIR, fname))
                except FileNotFoundError:
                    pass
            p.delete_instance()
            deleted.append(photo_id)

    return jsonify({"deleted": deleted}), 200


@photos_bp.route("/photos/export", methods=["GET"])
# Token aussi accepté en query string (?jwt=...) : l'export est déclenché par un lien de
# téléchargement natif (pas de header possible) pour que le navigateur écrive le ZIP sur
# disque au fil de l'eau au lieu de le garder entièrement en mémoire.
@admin_required(locations=["headers", "query_string"])
def export_photos():
    """Génère un ZIP de toutes les photos (admin uniquement).

    Query params:
        raw (bool, défaut false) — si true, exporte les versions sans masque (brutes)
    """
    want_raw = request.args.get("raw", "false").lower() == "true"
    photos = Photo.select().order_by(Photo.captured_at.asc())

    suffix = "_brutes" if want_raw else "_filtrees"
    # Liste construite avant le streaming : la connexion DB est fermée en fin de requête,
    # avant que le générateur ne soit consommé.
    return _zip_response(_zip_entries(list(photos), want_raw), f"photos{suffix}.zip")
