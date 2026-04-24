"""PrinterManager — gestion de l'imprimante Canon Selphy CP1500 via CUPS."""
import os
import struct
import time
import urllib.error
import urllib.request

import cups


class PrinterManager:
    def __init__(self):
        try:
            self.conn = cups.Connection()
        except Exception as e:
            raise RuntimeError(f"Impossible de se connecter à CUPS : {e}")

    # ── IPP direct ────────────────────────────────────────────────────────────

    @staticmethod
    def _build_get_printer_attrs(printer_uri: str) -> bytes:
        """Construit une requête IPP/1.1 Get-Printer-Attributes minimale."""
        def _a(tag: int, name: str, value: str) -> bytes:
            nb, vb = name.encode(), value.encode()
            return bytes([tag]) + struct.pack('>H', len(nb)) + nb + struct.pack('>H', len(vb)) + vb

        return (
            b'\x01\x01'           # IPP/1.1
            b'\x00\x0b'           # Get-Printer-Attributes
            b'\x00\x00\x00\x01'   # request-id = 1
            b'\x01'               # begin-operation-attributes
            + _a(0x47, 'attributes-charset', 'utf-8')
            + _a(0x48, 'attributes-natural-language', 'en-us')
            + _a(0x45, 'printer-uri', printer_uri)
            + b'\x03'             # end-of-attributes
        )

    @staticmethod
    def _parse_ipp_attrs(data: bytes) -> dict:
        """Parse une réponse IPP binaire en dict. Attributs multi-valeurs → liste."""
        if len(data) < 8:
            return {}

        pos = 8  # saute version(2) + status(2) + request-id(4)
        result: dict = {}
        last_name: str | None = None

        while pos < len(data):
            tag = data[pos]
            pos += 1

            if tag == 0x03:  # end-of-attributes
                break
            if tag < 0x10:  # délimiteur de groupe (0x01–0x0F)
                last_name = None
                continue

            if pos + 2 > len(data):
                break
            name_len = struct.unpack('>H', data[pos:pos + 2])[0]
            pos += 2

            if pos + name_len > len(data):
                break
            name = data[pos:pos + name_len].decode('utf-8', errors='replace')
            pos += name_len

            if pos + 2 > len(data):
                break
            val_len = struct.unpack('>H', data[pos:pos + 2])[0]
            pos += 2

            if pos + val_len > len(data):
                break
            val_bytes = data[pos:pos + val_len]
            pos += val_len

            attr_name = name if name else last_name
            if not attr_name:
                continue
            if name:
                last_name = name

            # Out-of-band (0x10–0x1F) : nom présent mais pas de valeur utile
            if tag < 0x20:
                continue

            # Décodage par type
            if tag in (0x21, 0x23):  # integer / enum
                if val_len != 4:
                    continue
                value = struct.unpack('>i', val_bytes)[0]
            elif tag == 0x22:  # boolean
                value = bool(val_bytes[0]) if val_bytes else False
            elif tag in (0x34, 0x37, 0x4A):  # collection (non géré)
                continue
            else:  # toutes les variantes string
                value = val_bytes.decode('utf-8', errors='replace')

            if attr_name in result:
                existing = result[attr_name]
                if not isinstance(existing, list):
                    result[attr_name] = [existing]
                result[attr_name].append(value)
            else:
                result[attr_name] = value

        return result

    def _ipp_direct_attrs(self, ip: str, port: int = 631) -> dict:
        """Interroge directement le serveur IPP de l'imprimante, sans passer par CUPS."""
        printer_uri = f'ipp://{ip}/ipp/print'
        body = self._build_get_printer_attrs(printer_uri)
        req = urllib.request.Request(
            f'http://{ip}:{port}/ipp/print',
            data=body,
            headers={'Content-Type': 'application/ipp'},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return self._parse_ipp_attrs(resp.read())

    def lister_imprimantes(self):
        """Retourne une liste des noms d'imprimantes disponibles."""
        try:
            return list(self.conn.getPrinters().keys())
        except Exception:
            return []

    def obtenir_statut(self, nom_imprimante, wifi_ip=None):
        """Retourne un dictionnaire avec l'état précis de l'imprimante.

        Si wifi_ip est fourni, l'état de l'imprimante est lu directement via IPP
        (temps réel, sans cache CUPS). Les jobs restent gérés via CUPS.
        """
        try:
            # ── État imprimante ───────────────────────────────────────────────
            state, reasons, message_raw = 3, ["none"], ""

            if wifi_ip:
                try:
                    ipp = self._ipp_direct_attrs(wifi_ip)
                    state = ipp.get("printer-state", 3)
                    reasons = ipp.get("printer-state-reasons", ["none"])
                    if isinstance(reasons, str):
                        reasons = [reasons]
                    message_raw = ipp.get("printer-state-message", "") or ""
                except Exception:
                    wifi_ip = None  # fallback CUPS

            if not wifi_ip:
                printers = self.conn.getPrinters()
                if nom_imprimante not in printers:
                    return {
                        "en_erreur": True, "message": "Imprimante introuvable",
                        "bloquee": False, "erreurs": ["Imprimante introuvable"],
                        "job_en_cours": False, "reasons": [],
                    }
                attrs = printers[nom_imprimante]
                reasons = attrs.get("printer-state-reasons", ["none"])
                if isinstance(reasons, str):
                    reasons = [reasons]
                state = attrs.get("printer-state", 3)
                message_raw = attrs.get("printer-state-message", "") or ""

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
