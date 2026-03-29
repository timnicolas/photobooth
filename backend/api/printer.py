"""PrinterManager — gestion de l'imprimante Canon Selphy CP1500 via CUPS."""
import os
import time

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
                return {
                    "en_erreur": True, "message": "Imprimante introuvable",
                    "bloquee": False, "erreurs": ["Imprimante introuvable"],
                    "job_en_cours": False, "reasons": [],
                }

            attrs = printers[nom_imprimante]
            reasons = attrs.get("printer-state-reasons", ["none"])
            state = attrs.get("printer-state", 3)  # 3=Idle, 4=Processing, 5=Stopped
            reasons_str = " ".join(reasons).lower()

            erreurs = []

            # Erreurs hardware détectées via printer-state-reasons
            if "media-empty" in reasons_str or "media-needed" in reasons_str:
                erreurs.append("Plus de papier")
            if "marker-supply-empty" in reasons_str or "toner-empty" in reasons_str or "no-toner" in reasons_str:
                erreurs.append("Plus d'encre")
            if "offline" in reasons_str or "connecting-to-device" in reasons_str:
                erreurs.append("Imprimante déconnectée")
            if "input-tray-missing" in reasons_str or "media-tray-missing" in reasons_str:
                erreurs.append("Bac papier manquant")
            if "cover-open" in reasons_str or "door-open" in reasons_str:
                erreurs.append("Capot ouvert")

            # Inspection des jobs actifs via getJobAttributes()
            # Note : getJobs() ne retourne que job-uri, il faut appeler getJobAttributes().
            # Le Selphy ne remonte jamais media-empty dans printer-state-reasons ;
            # on détecte un blocage si un job est en state 5 (processing) depuis plus de 2 min.
            job_en_cours = state == 4
            try:
                jobs = self.conn.getJobs(which_jobs="not-completed", my_jobs=False)
                for jid in list(jobs.keys())[:10]:
                    try:
                        jattrs = self.conn.getJobAttributes(jid)
                    except Exception:
                        continue

                    printer_uri = jattrs.get("job-printer-uri", "")
                    if nom_imprimante not in printer_uri:
                        continue

                    job_state = jattrs.get("job-state", 0)
                    # IPP : 3=pending, 4=pending-held, 5=processing, 6=processing-stopped
                    if job_state in (3, 4, 5, 6):
                        job_en_cours = True

                    if job_state == 5:  # processing — vérifier si bloqué
                        time_start = jattrs.get("time-at-processing") or 0
                        completed = jattrs.get("date-time-at-completed")
                        now = jattrs.get("job-printer-up-time") or int(time.time())
                        if time_start and completed is None and (now - time_start) > 120:
                            if not any("bloquée" in e for e in erreurs):
                                erreurs.append("Impression bloquée — vérifiez le papier et l'encre")
            except Exception:
                pass

            bloquee = state == 5
            en_erreur = bool(erreurs)

            if erreurs:
                message = " — ".join(erreurs)
            elif bloquee:
                message = "File en pause"
            elif job_en_cours:
                message = "Impression en cours..."
            elif "none" not in reasons_str and reasons:
                message = f"Info : {reasons_str}"
            else:
                message = "Prête"

            return {
                "nom": nom_imprimante,
                "en_erreur": en_erreur,
                "message": message,
                "bloquee": bloquee,
                "erreurs": erreurs,
                "job_en_cours": job_en_cours,
                "reasons": reasons,
            }

        except Exception as e:
            return {
                "en_erreur": True, "message": f"Erreur système : {e}",
                "bloquee": False, "erreurs": [f"Erreur système : {e}"],
                "job_en_cours": False, "reasons": [],
            }

    def lister_jobs(self, nom_imprimante):
        """Retourne les jobs actifs pour l'imprimante."""
        STATE_LABELS = {3: "En attente", 4: "En attente", 5: "En cours", 6: "Bloqué"}
        result = []
        try:
            jobs = self.conn.getJobs(which_jobs="not-completed", my_jobs=False)
            for jid in list(jobs.keys()):
                try:
                    attrs = self.conn.getJobAttributes(jid)
                except Exception:
                    continue
                if nom_imprimante not in attrs.get("job-printer-uri", ""):
                    continue
                job_state = attrs.get("job-state", 0)
                if job_state not in (3, 4, 5, 6):
                    continue
                time_start = attrs.get("time-at-processing") or None
                now = attrs.get("job-printer-up-time") or int(time.time())
                completed = attrs.get("date-time-at-completed")
                elapsed = (now - time_start) if (time_start and completed is None) else None
                result.append({
                    "id": jid,
                    "state": job_state,
                    "state_label": STATE_LABELS.get(job_state, "Inconnu"),
                    "progress": attrs.get("job-media-progress", 0),
                    "created_at": attrs.get("time-at-creation"),
                    "elapsed_seconds": elapsed,
                })
        except Exception:
            pass
        return result

    def annuler_job(self, job_id):
        """Annule un job et purge la file pour forcer l'arrêt de l'imprimante."""
        try:
            self.conn.cancelJob(job_id, purge_job=True)
        except cups.IPPError:
            pass
        return True

    def annuler_tous_jobs(self, nom_imprimante):
        """Annule tous les jobs et réinitialise la file (nécessaire sur Selphy)."""
        try:
            self.conn.cancelAllJobs(nom_imprimante, my_jobs=False)
        except cups.IPPError:
            pass
        try:
            # Disable + enable force le Selphy à vider son buffer
            self.conn.disablePrinter(nom_imprimante)
            self.conn.enablePrinter(nom_imprimante)
        except cups.IPPError:
            pass
        return True

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
        chemin_image = os.path.abspath(chemin_image)
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
