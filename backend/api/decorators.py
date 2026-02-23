from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request


def admin_required(fn):
    """Décorateur : vérifie le JWT et exige is_admin=True."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        if not get_jwt().get("is_admin", False):
            return jsonify({"error": "Accès réservé aux administrateurs"}), 403
        return fn(*args, **kwargs)
    return wrapper
