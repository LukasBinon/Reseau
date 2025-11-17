import sqlite3
import customtkinter as ctk
from tkinter import messagebox
import session
from database import get_conn, get_decoupe_details, update_full_decoupe
import ipaddress  # Nécessaire pour les calculs

DB_NAME = "reseau.db"

bleu = "#2D89EF"
bleuHover = "#2563EB"
gris = "#2c2c2e"
grisHover = "#3a3a3c"
blanc = "white"
bg = "#1c1c1e"


# --- LOGIQUE DE CALCUL (Recréée depuis Test.py) ---
# (Cette logique est nécessaire pour recalculer la découpe)
def logic_decoupe_recalculer(ip_reseau, masque, nb_sous_reseaux):
    """
    Valide et recalcule les sous-réseaux.
    Lève des ValueError en cas de problème.
    Retourne une liste de tuples formatés pour la DB.
    """
    try:
        net_str = f"{ip_reseau}/{masque}"
        net = ipaddress.ip_network(net_str, strict=False)
        if str(net.network_address) != ip_reseau:
            raise ValueError(f"L'IP {ip_reseau} n'est pas une adresse réseau. (Utilisez {net.network_address})")
    except Exception as e:
        raise ValueError(f"IP/Masque invalide: {e}")

    try:
        nb_sr_int = int(nb_sous_reseaux)
        if nb_sr_int <= 0:
            raise ValueError()
    except Exception:
        raise ValueError("Le nombre de sous-réseaux doit être un entier positif.")

    # Calculer le préfixe
    s_bits = (nb_sr_int - 1).bit_length()
    new_prefix = net.prefixlen + s_bits

    if new_prefix > 30:  # Contrainte
        raise ValueError(f"Découpe impossible: le nouveau préfixe /{new_prefix} est > /30.")

    nouveaux_srs = list(net.subnets(new_prefix=new_prefix))
    nouveaux_srs = nouveaux_srs[:nb_sr_int]  # Garder seulement le nombre demandé

    formatted_srs = []
    for sr in nouveaux_srs:
        network = sr.network_address
        broadcast = sr.broadcast_address
        total = sr.num_addresses
        nb_hotes = max(total - 2, 0)

        if total >= 4:
            plage_debut = str(ipaddress.IPv4Address(int(network) + 1))
            plage_fin = str(ipaddress.IPv4Address(int(broadcast) - 1))
        else:
            plage_debut, plage_fin = "", ""

        formatted_srs.append((
            str(network),
            str(sr.netmask),  # Le masque du sous-réseau
            plage_debut,
            plage_fin,
            str(broadcast),
            nb_hotes
        ))
    return formatted_srs


# --- FIN DE LA LOGIQUE DE CALCUL ---


def ouvrir_fenetre_recherche_decoupe():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    app = ctk.CTkToplevel()
    app.title("Recherche et Gestion de Découpe Réseau")
    app.state('zoomed')
    app.configure(fg_color=bg)

    app.transient()
    app.grab_set()

    current_decoupe_id = None  # Mémorise l'ID de la découpe affichée

    # --- Zone de recherche ---
    frame = ctk.CTkFrame(app, fg_color=gris, corner_radius=15)
    frame.pack(pady=30, padx=30, fill="x")

    label_nom = ctk.CTkLabel(frame, text="Nom de la découpe :", text_color=blanc, font=("Segoe UI", 16, "bold"))
    label_nom.grid(row=0, column=0, padx=20, pady=20, sticky="w")

    entry_nom = ctk.CTkEntry(frame, placeholder_text="Ex: Réseau Bureau", width=300, height=40, font=("Segoe UI", 14))
    entry_nom.grid(row=0, column=1, padx=10)

    # --- Tableau des résultats ---
    tableau_frame = ctk.CTkScrollableFrame(app, corner_radius=12, fg_color=gris)
    tableau_frame.pack(padx=30, pady=20, fill="both", expand=True)

    def rechercher_decoupe(nom_decoupe):
        # (Cette fonction ne change pas)
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id_decoupe, id_responsable FROM decoupe WHERE nom_decoupe = ?", (nom_decoupe,))
            row = cur.fetchone()
            if not row:
                return None, []

            id_decoupe, id_responsable = row
            if id_responsable != session.utilisateur_connecte_id:
                raise PermissionError("Vous n'avez pas les droits pour consulter cette découpe.")

            cur.execute("""
                        SELECT ip_reseau, masque, ip_debut, ip_fin, ip_broadcast, nb_ips
                        FROM sous_reseau
                        WHERE id_decoupe = ?
                        """, (id_decoupe,))
            sous_reseaux = cur.fetchall()
            return id_decoupe, sous_reseaux

    def afficher_decoupe():
        nonlocal current_decoupe_id
        current_decoupe_id = None
        nom = entry_nom.get().strip()

        if not nom:
            messagebox.showerror("Erreur", "Veuillez entrer un nom de découpe.", parent=app)
            return

        for widget in tableau_frame.winfo_children():
            widget.destroy()

        try:
            id_decoupe, sous_reseaux = rechercher_decoupe(nom)

            if id_decoupe is None:
                messagebox.showinfo("Résultat", "Aucune découpe trouvée avec ce nom.", parent=app)
                return

            current_decoupe_id = id_decoupe

            if not sous_reseaux:
                messagebox.showinfo("Résultat", f"La découpe '{nom}' existe mais n'a aucun sous-réseau enregistré.",
                                    parent=app)
                return

            # Affichage tableau (inchangé)
            colonnes = ["IP Réseau", "Masque", "IP Début", "IP Fin", "Broadcast", "Nb IPs"]
            for j, col in enumerate(colonnes):
                ctk.CTkLabel(tableau_frame, text=col, font=("Segoe UI", 16, "bold"), fg_color=bleu, text_color="white",
                             corner_radius=8).grid(row=0, column=j, padx=5, pady=8, sticky="nsew")
            for i, sr in enumerate(sous_reseaux, start=1):
                bg_color = grisHover if i % 2 == 0 else gris
                for j, val in enumerate(sr):
                    ctk.CTkLabel(tableau_frame, text=str(val), font=("Segoe UI", 14), text_color=blanc,
                                 fg_color=bg_color, corner_radius=6).grid(row=i, column=j, padx=5, pady=5,
                                                                          sticky="nsew")

        except PermissionError as e:
            messagebox.showerror("Accès refusé", str(e), parent=app)
        except Exception as e:
            messagebox.showerror("Erreur", f"Une erreur inattendue est survenue : {e}", parent=app)

    # --- MODIFICATION: Ouvre la fenêtre de dialogue pour modifier ---
    def ouvrir_dialogue_modification():
        nonlocal current_decoupe_id
        if current_decoupe_id is None:
            messagebox.showerror("Erreur", "Veuillez d'abord rechercher une découpe valide.", parent=app)
            return

        try:
            # 1. Récupérer les données actuelles
            details = get_decoupe_details(current_decoupe_id, session.utilisateur_connecte_id)

            # 2. Ouvrir une fenêtre de dialogue
            dialog = ctk.CTkToplevel(app)
            dialog.title(f"Modifier: {details['nom_decoupe']}")
            dialog.geometry("500x400")
            dialog.transient()
            dialog.grab_set()

            dialog_frame = ctk.CTkFrame(dialog, fg_color=gris)
            dialog_frame.pack(fill="both", expand=True, padx=10, pady=10)

            # --- Champs de la boîte de dialogue ---
            ctk.CTkLabel(dialog_frame, text="Nom :").grid(row=0, column=0, padx=10, pady=5, sticky="e")
            entry_edit_nom = ctk.CTkEntry(dialog_frame, width=250)
            entry_edit_nom.grid(row=0, column=1, padx=10, pady=5)
            entry_edit_nom.insert(0, details['nom_decoupe'])

            ctk.CTkLabel(dialog_frame, text="IP Réseau :").grid(row=1, column=0, padx=10, pady=5, sticky="e")
            entry_edit_ip = ctk.CTkEntry(dialog_frame, width=250)
            entry_edit_ip.grid(row=1, column=1, padx=10, pady=5)
            entry_edit_ip.insert(0, details['ip_reseau'])

            ctk.CTkLabel(dialog_frame, text="Masque (Ex: 255.255.255.0) :").grid(row=2, column=0, padx=10, pady=5,
                                                                                 sticky="e")
            entry_edit_masque = ctk.CTkEntry(dialog_frame, width=250)
            entry_edit_masque.grid(row=2, column=1, padx=10, pady=5)
            entry_edit_masque.insert(0, details['masque'])

            ctk.CTkLabel(dialog_frame, text="Nombre de Sous-Réseaux :").grid(row=3, column=0, padx=10, pady=5,
                                                                             sticky="e")
            entry_edit_nb_sr = ctk.CTkEntry(dialog_frame, width=250)
            entry_edit_nb_sr.grid(row=3, column=1, padx=10, pady=5)
            entry_edit_nb_sr.insert(0, details['nombre_sous_reseaux'] or "")

            # --- MODIFICATION: AJOUT DE LA LOGIQUE CLASSFUL ---

            def _update_mask_for_classful_edit(*args):
                """Logique copiée de Test.py, s'active si le mode est classful."""
                ip_text = entry_edit_ip.get().strip()
                masque = ""
                try:
                    ip_obj = ipaddress.IPv4Address(ip_text.split("/")[0])
                    first = ip_obj.packed[0]  # Récupère le premier octet

                    if 1 <= first <= 126:
                        masque = "255.0.0.0"  # Classe A
                    elif 128 <= first <= 191:
                        masque = "255.255.0.0"  # Classe B
                    elif 192 <= first <= 223:
                        masque = "255.255.255.0"  # Classe C
                    else:
                        masque = ""  # IP invalide (D, E, etc.)
                except Exception:
                    masque = ""  # IP non valide
                finally:
                    # Forcer la mise à jour du champ masque
                    entry_edit_masque.configure(state="normal")
                    entry_edit_masque.delete(0, "end")
                    entry_edit_masque.insert(0, masque)
                    entry_edit_masque.configure(state="disabled")

            # Vérifier le mode de la découpe et appliquer la logique
            if details['mode'] == 'classful':
                # Lier l'événement KeyRelease au champ IP
                entry_edit_ip.bind("<KeyRelease>", _update_mask_for_classful_edit)
                # Verrouiller le masque immédiatement
                _update_mask_for_classful_edit()
            else:
                # S'assurer que le masque est modifiable si classless
                entry_edit_masque.configure(state="normal")

            # --- FIN DE LA MODIFICATION ---

            def executer_modification():
                # Récupérer les nouvelles valeurs
                new_nom = entry_edit_nom.get().strip()
                new_ip = entry_edit_ip.get().strip()
                new_masque = entry_edit_masque.get().strip()  # Lit la valeur (auto-remplie ou manuelle)
                new_nb_sr = entry_edit_nb_sr.get().strip()

                if not all([new_nom, new_ip, new_masque, new_nb_sr]):
                    messagebox.showerror("Erreur", "Tous les champs sont obligatoires.", parent=dialog)
                    return

                try:
                    # 3. Recalculer les sous-réseaux
                    nouveaux_sous_reseaux = logic_decoupe_recalculer(new_ip, new_masque, new_nb_sr)

                    # 4. Préparer le dictionnaire de données pour 'decoupe'
                    new_data = {
                        "nom_decoupe": new_nom,
                        "ip_reseau": new_ip,
                        "masque": new_masque,  # Enregistre le masque correct
                        "nombre_sous_reseaux": int(new_nb_sr),
                        "mode": details['mode'],  # Garder l'ancien mode
                    }

                    # 5. Appeler la fonction DB
                    update_full_decoupe(
                        decoupe_id=current_decoupe_id,
                        owner_id=session.utilisateur_connecte_id,
                        new_data=new_data,
                        new_subnets=nouveaux_sous_reseaux
                    )

                    messagebox.showinfo("Succès", "Découpe mise à jour.", parent=app)
                    dialog.destroy()

                    # Rafraîchir l'interface principale
                    entry_nom.delete(0, "end")
                    entry_nom.insert(0, new_nom)
                    afficher_decoupe()

                except (ValueError, PermissionError, sqlite3.IntegrityError) as e:
                    messagebox.showerror("Erreur de modification", str(e), parent=dialog)
                except Exception as e:
                    messagebox.showerror("Erreur", f"Erreur inattendue: {e}", parent=dialog)

            # Bouton de validation
            btn_save = ctk.CTkButton(dialog_frame, text="Enregistrer", command=executer_modification, fg_color=bleu,
                                     hover_color=bleuHover)
            btn_save.grid(row=4, column=0, columnspan=2, pady=20)

        except (ValueError, PermissionError) as e:
            messagebox.showerror("Erreur", str(e), parent=app)
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur inattendue: {e}", parent=app)

    # --- Boutons ---
    btn_rechercher = ctk.CTkButton(frame, text="Rechercher", width=150, height=40,
                                   fg_color=bleu, hover_color=bleuHover,
                                   text_color="white", font=("Segoe UI", 14, "bold"),
                                   command=afficher_decoupe)
    btn_rechercher.grid(row=0, column=2, padx=10)

    # --- BOUTON MODIFIÉ ---
    btn_modifier = ctk.CTkButton(frame, text="Modifier...", width=150, height=40,
                                 fg_color=grisHover, hover_color=gris,
                                 text_color="white", font=("Segoe UI", 14, "bold"),
                                 command=ouvrir_dialogue_modification)  # <--- Appel de la nouvelle fonction
    btn_modifier.grid(row=0, column=3, padx=10)

    # --- Bouton de fermeture ---
    btn_quitter = ctk.CTkButton(app, text="Fermer", width=120, height=40,
                                fg_color=gris, hover_color=grisHover,
                                text_color="white", font=("Segoe UI", 14, "bold"),
                                command=app.destroy)
    btn_quitter.pack(pady=10)

    app.mainloop()