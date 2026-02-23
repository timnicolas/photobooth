from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from werkzeug.security import check_password_hash

from api.models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)

    if not data or not data.get("mail") or not data.get("password"):
        return jsonify({"error": "Les champs mail et password sont requis"}), 400

    try:
        user = User.get(User.mail == data["mail"])
    except User.DoesNotExist:
        return jsonify({"error": "Identifiants invalides"}), 401

    if not check_password_hash(user.password, data["password"]):
        return jsonify({"error": "Identifiants invalides"}), 401

    token = create_access_token(
        identity=str(user.id),
        additional_claims={
            "mail": user.mail,
            "is_admin": user.is_admin,
        },
    )

    return jsonify(
        {
            "token": token,
            "user": {
                "mail": user.mail,
                "firstname": user.firstname,
                "lastname": user.lastname,
                "is_admin": user.is_admin,
            },
        }
    )
