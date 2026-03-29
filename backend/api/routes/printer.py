from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from api.config import Config
from api.printer import PrinterManager

printer_bp = Blueprint("printer", __name__)


@printer_bp.route("/printer/jobs", methods=["GET"])
@jwt_required()
def printer_jobs():
    """Retourne la file d'attente d'impression."""
    try:
        pm = PrinterManager()
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    return jsonify({"jobs": pm.lister_jobs(Config.PRINTER_NAME)})


@printer_bp.route("/printer/jobs", methods=["DELETE"])
@jwt_required()
def cancel_all_jobs():
    """Annule tous les jobs et réinitialise la file."""
    try:
        pm = PrinterManager()
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    pm.annuler_tous_jobs(Config.PRINTER_NAME)
    return jsonify({"message": "File purgée"})


@printer_bp.route("/printer/jobs/<int:job_id>", methods=["DELETE"])
@jwt_required()
def cancel_job(job_id):
    """Annule un job et réinitialise la file pour arrêter l'imprimante."""
    try:
        pm = PrinterManager()
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    pm.annuler_job(job_id)
    # Toujours purger + reset pour forcer l'arrêt du Selphy
    pm.annuler_tous_jobs(Config.PRINTER_NAME)
    return jsonify({"message": "Job annulé"})


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
            "printing": status["job_en_cours"],
            "message": status["message"],
            "errors": status["erreurs"],
            "reasons": status["reasons"],
        }
    )
