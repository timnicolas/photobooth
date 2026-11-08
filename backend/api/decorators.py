from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request


def admin_required(fn=None, *, locations=None):
    """Décorateur : vérifie le JWT et exige is_admin=True.

    Utilisable nu (@admin_required) ou avec les emplacements du token acceptés
    (@admin_required(locations=["headers", "query_string"])).
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request(locations=locations)
            if not get_jwt().get("is_admin", False):
                return jsonify({"error": "Accès réservé aux administrateurs"}), 403
            return f(*args, **kwargs)
        return wrapper

    return decorator(fn) if fn is not None else decorator
