from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from api.config import Config
from api.printer import PrinterManager

printer_bp = Blueprint("printer", __name__)


@printer_bp.route("/printer/status", methods=["GET"])
@jwt_required()
def printer_status():
    """Retourne l'état courant de l'imprimante configurée."""
    try:
        pm = PrinterManager()
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503

    printers = pm.lister_imprimantes()
    if Config.PRINTER_NAME not in printers:
        return jsonify(
            {
                "printer": Config.PRINTER_NAME,
                "available": False,
                "error": "Imprimante non trouvée dans CUPS",
            }
        ), 404

    status = pm.obtenir_statut(Config.PRINTER_NAME)
    return jsonify(
        {
            "printer": Config.PRINTER_NAME,
            "available": True,
            "ready": not status["en_erreur"] and not status["bloquee"],
            "message": status["message"],
            "reasons": status["reasons"],
        }
    )
