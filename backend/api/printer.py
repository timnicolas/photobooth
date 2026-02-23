"""PrinterManager — gestion de l'imprimante Canon Selphy CP1500 via CUPS."""
import os

import cups


class PrinterManager:
    def __init__(self):
        try:
            self.conn = cups.Connection()
        except Exception as e:
            raise RuntimeError(f"Impossible de se connecter à CUPS : {e}")

    def lister_imprimantes(self):
        """Retourne une liste des noms d'imprimantes disponibles."""
        try:
            return list(self.conn.getPrinters().keys())
        except Exception:
            return []

    def obtenir_statut(self, nom_imprimante):
        """Retourne un dictionnaire avec l'état précis de l'imprimante."""
        try:
            printers = self.conn.getPrinters()

            if nom_imprimante not in printers:
                return {"en_erreur": True, "message": "Imprimante introuvable", "bloquee": False}

            attrs = printers[nom_imprimante]
            reasons = attrs.get("printer-state-reasons", ["none"])
            state = attrs.get("printer-state", 3)  # 3=Idle, 4=Processing, 5=Stopped

            status = {
                "nom": nom_imprimante,
                "en_erreur": False,
                "message": "Prête",
                "bloquee": False,
                "reasons": reasons,
            }

            reasons_str = " ".join(reasons).lower()

            if state == 5:
                status["bloquee"] = True
                status["message"] = "En pause (File stoppée)."

            if "media-empty" in reasons_str or "media-needed" in reasons_str:
                status["en_erreur"] = True
                status["message"] = "ERREUR : Plus de papier."
            elif "marker-supply-empty" in reasons_str or "no-toner" in reasons_str:
                status["en_erreur"] = True
                status["message"] = "ERREUR : Plus d'encre."
            elif "offline" in reasons_str:
                status["en_erreur"] = True
                status["message"] = "ERREUR : Imprimante déconnectée."
            elif "input-tray-missing" in reasons_str:
                status["en_erreur"] = True
                status["message"] = "ERREUR : Bac papier manquant."
            elif "other-error" in reasons_str:
                status["en_erreur"] = True
                status["message"] = "ERREUR : Problème inconnu."
            elif state == 4:
                status["message"] = "Impression en cours..."
            elif "none" not in reasons_str and reasons:
                status["message"] = f"Info : {reasons_str}"

            return status

        except Exception as e:
            return {"en_erreur": True, "message": f"Erreur système : {e}", "bloquee": False}

    def reset_error(self, nom_imprimante, purger_file=False):
        """Tente de débloquer l'imprimante après une erreur."""
        try:
            if purger_file:
                self.conn.cancelAllJobs(nom_imprimante)

            self.conn.enablePrinter(nom_imprimante)

            etat = self.obtenir_statut(nom_imprimante)
            return not etat["bloquee"]

        except cups.IPPError:
            return False

    def relancer_file(self, nom_imprimante):
        """Réactive l'imprimante (nécessaire après une erreur papier sur Selphy)."""
        try:
            self.conn.enablePrinter(nom_imprimante)
            return True
        except cups.IPPError:
            return False

    def imprimer_image(self, nom_imprimante, chemin_image, sans_bordure=True, noir_blanc=False):
        """Imprime l'image avec gestion des options Selphy CP1500."""
        if not os.path.exists(chemin_image):
            raise FileNotFoundError(f"Fichier introuvable : {chemin_image}")

        options_cups = {
            "MediaType": "photographic",
            "cupsPrintQuality": "Normal",
            "fit-to-page": "True",
            "PageSize": "Postcard.Fullbleed" if sans_bordure else "Postcard",
            "ColorModel": "Gray" if noir_blanc else "RGB",
        }

        try:
            job_id = self.conn.printFile(nom_imprimante, chemin_image, "Job Python", options_cups)
            return job_id
        except cups.IPPError as e:
            raise RuntimeError(f"Erreur d'envoi CUPS : {e}")
