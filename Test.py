import ipaddress
import customtkinter as ctk
from tkinter import messagebox
import sqlite3  # Importé pour la gestion d'erreur IntegrityError

import session
from database import get_connection, get_user_id


# =========================
#   LOGIQUE & UTILITAIRES
# =========================
# (Toutes les fonctions logiques ci-dessous sont INCHANGÉES)
# ... ( _parse_network, _tabuler_sous_reseaux, calculer_sous_reseaux ) ...
def _parse_network(reseau_de_base: str, masque_str: str | None):
    """
    Accepte :
      - '192.168.1.0/24' (CIDR)
      - '192.168.1.0' + masque '/24' ou '255.255.255.0'
    Retourne un IPv4Network (strict=False pour tolérer une IP d'hôte).
    """
    if not reseau_de_base or not reseau_de_base.strip():  # strip supprime les espaces
        raise ValueError("Réseau de base manquant.")

    reseau_de_base = reseau_de_base.strip()

    # Si CIDR déjà fourni
    if "/" in reseau_de_base:
        # AJOUT : Vérification de conflit
        if masque_str and masque_str.strip():
            raise ValueError(
                "Conflit de saisie : Fournissez le masque DANS le réseau de base (ex: 192.168.1.0/24) "
                "OU dans le champ 'Masque', mais PAS les deux."
            )
        net = ipaddress.ip_network(reseau_de_base, strict=False)
    else:
        if masque_str is None or not masque_str.strip():
            raise ValueError("Masque manquant. Fournis un masque (ex: 255.255.255.0 ou /24).")
        masque_str = masque_str.strip()

        if masque_str.startswith("/"):
            try:
                prefix = int(masque_str[1:])
            except ValueError:
                raise ValueError("Préfixe invalide. Exemple : /24")
        else:
            # Convertir un masque pointé en préfixe
            try:
                prefix = ipaddress.IPv4Network(f"0.0.0.0/{masque_str}").prefixlen
            except Exception:
                raise ValueError("Masque invalide. Exemples valides : 255.255.255.0 ou /24")

        if not (0 <= prefix <= 32):
            raise ValueError("Préfixe invalide : doit être entre /0 et /32.")

        net = ipaddress.ip_network(f"{reseau_de_base}/{prefix}", strict=False)

    if net.version != 4:
        raise NotImplementedError("Seul IPv4 est géré dans cette version.")
    return net


def _tabuler_sous_reseaux(sous_reseaux: list[ipaddress.IPv4Network]):
    """
    Transforme la liste de sous-réseaux en lignes :
    [Nom, Adresse réseau, Broadcast, Plage utilisable, Nb hôtes]
    (Sans générer la liste de tous les hôtes.)
    """
    resultats = []
    for i, sr in enumerate(sous_reseaux, start=1):
        network = sr.network_address
        broadcast = sr.broadcast_address
        total = sr.num_addresses

        if total >= 4:
            first_host = ipaddress.IPv4Address(int(network) + 1)
            last_host = ipaddress.IPv4Address(int(broadcast) - 1)
            nb_hotes = total - 2
            plage = f"{first_host} - {last_host}"
        else:
            nb_hotes = max(total - 2, 0)
            plage = "Aucun"

        resultats.append([
            f"Sous-réseau {i}",
            str(network),
            str(broadcast),
            plage,
            str(nb_hotes),
        ])
    return resultats


def calculer_sous_reseaux(
        reseau_de_base: str,
        nb_sous_reseaux: int | None = None,
        masque: str | None = None,
        nb_ips_utilisables: int | None = None
):
    """
    Calcule des sous-réseaux en respectant :
      - nb_sous_reseaux (optionnel)
      - nb_ips_utilisables par SR (optionnel)
    Retourne des lignes prêtes pour l'affichage.
    """
    net = _parse_network(reseau_de_base, masque if "/" not in reseau_de_base else None)
    p = net.prefixlen

    # Normaliser les entrées
    s_bits = 0
    if nb_sous_reseaux is not None:
        if nb_sous_reseaux <= 0:
            raise ValueError("Le nombre de sous-réseaux doit être strictement positif.")
        s_bits = (nb_sous_reseaux - 1).bit_length()  # ceil(log2(n))
    prefix_from_subnets = p + s_bits  # borne inférieure sur le /xx

    prefix_from_hosts_max = 32  # pas de contrainte par défaut
    if nb_ips_utilisables is not None:
        if nb_ips_utilisables <= 0:
            raise ValueError("Le nombre d'IP utilisables / SR doit être strictement positif.")
        required_total = nb_ips_utilisables + 2  # règle IPv4 classique
        if required_total < 4:
            required_total = 4
        h = (required_total - 1).bit_length()  # ceil(log2(required_total))
        prefix_from_hosts_max = 32 - h  # /xx max autorisé pour respecter le nb d'IP

        if prefix_from_hosts_max < p:
            raise ValueError(
                f"Incompatible : {net.with_prefixlen} ne peut pas fournir {nb_ips_utilisables} IP utilisables "
                f"par sous-réseau."
            )

    if nb_sous_reseaux is not None and nb_ips_utilisables is not None:
        if prefix_from_subnets > prefix_from_hosts_max:
            raise ValueError(
                f"Incompatible : impossible de créer {nb_sous_reseaux} sous-réseau(x) avec "
                f"{nb_ips_utilisables} IP utilisables chacun dans {net.with_prefixlen}."
            )

    if nb_sous_reseaux is not None:
        new_prefix = prefix_from_subnets
    elif nb_ips_utilisables is not None:
        new_prefix = max(p, prefix_from_hosts_max)
    else:
        new_prefix = p  # pas de découpe

    sous_reseaux = list(net.subnets(new_prefix=new_prefix))
    if nb_sous_reseaux is not None:
        sous_reseaux = sous_reseaux[:nb_sous_reseaux]

    return _tabuler_sous_reseaux(sous_reseaux), new_prefix, net


# =========================
#   UI (Interface Mise à Jour)
# =========================

# --- Palette de couleurs basée sur interface_connexion.py ---
THEME_BLUE = "#2D89EF"
THEME_BLUE_HOVER = "#2563EB"
THEME_GREY_BUTTON = "#2c2c2e"
THEME_GREY_HOVER = "#3a3a3c"
THEME_TEXT_WHITE = "white"
THEME_BACKGROUND = "#1c1c1e"
THEME_QUIT_BG = "#1c1c1e"


def configurer_fenetre(app):
    app.title("Générateur de Plan d'Adressage Réseau")
    # app.update_idletasks() # Déplacé vers ouvrir_fenetre_decoupe


def creer_frame_principale(app):
    # Ce cadre prend la couleur de fond de l'application
    frame = ctk.CTkFrame(app, corner_radius=0, fg_color=THEME_BACKGROUND)
    frame.pack(fill="both", expand=True, padx=20, pady=20)
    return frame


def creer_titre(frame):
    titre = ctk.CTkLabel(
        frame,
        text="Générateur de Plan d'Adressage",
        font=("Segoe UI", 34, "bold"),
        text_color=THEME_BLUE  # Couleur titre
    )
    titre.pack(pady=(20, 20))


def creer_zone_saisie(frame):
    """
    Crée la zone de saisie en respectant le thème.
    """

    # --- Cadre pour le Mode (Classful/Classless) ---
    mode_frame = ctk.CTkFrame(frame, fg_color=THEME_GREY_BUTTON, corner_radius=10)
    mode_frame.pack(pady=(10, 0), padx=30, fill="x")

    mode_label = ctk.CTkLabel(mode_frame, text="Type d'adresse IP :",
                              font=("Segoe UI", 16, "bold"), text_color=THEME_TEXT_WHITE)
    mode_label.grid(row=0, column=0, padx=20, pady=15, sticky="w")

    mode_var = ctk.StringVar(value="classless")
    radio_classful = ctk.CTkRadioButton(mode_frame, text="Classful", variable=mode_var, value="classful",
                                        font=("Segoe UI", 14), border_color=THEME_BLUE, fg_color=THEME_BLUE)
    radio_classless = ctk.CTkRadioButton(mode_frame, text="Classless", variable=mode_var, value="classless",
                                         font=("Segoe UI", 14), border_color=THEME_BLUE, fg_color=THEME_BLUE)
    radio_classful.grid(row=0, column=1, padx=10, pady=15)
    radio_classless.grid(row=0, column=2, padx=10, pady=15)

    # --- Cadre pour le Nom de la découpe ---
    nom_frame = ctk.CTkFrame(frame, fg_color=THEME_GREY_BUTTON, corner_radius=10)
    nom_frame.pack(pady=(10, 0), padx=30, fill="x")

    ctk.CTkLabel(nom_frame, text="Nom de la découpe :",
                 font=("Segoe UI", 16, "bold"), text_color=THEME_TEXT_WHITE).grid(row=0, column=0, padx=20, pady=15,
                                                                                  sticky="w")
    entry_nom_decoupe = ctk.CTkEntry(nom_frame, placeholder_text="Ex: Réseau bureau",
                                     width=350, height=45, font=("Segoe UI", 14), corner_radius=10)
    entry_nom_decoupe.grid(row=0, column=1, padx=20, pady=15)

    # --- Cadre pour les Inputs IP ---
    input_frame = ctk.CTkFrame(frame, fg_color=THEME_GREY_BUTTON, corner_radius=15)
    input_frame.pack(pady=20, padx=30, fill="x")

    # Ligne 1: Réseau + Masque
    ctk.CTkLabel(input_frame, text="Réseau de base :",
                 font=("Segoe UI", 16, "bold"), text_color=THEME_TEXT_WHITE).grid(row=0, column=0, padx=20, pady=15,
                                                                                  sticky="w")
    entry_reseau = ctk.CTkEntry(input_frame, placeholder_text="Ex: 192.168.1.0 ou 192.168.1.0/24",
                                width=300, height=45, font=("Segoe UI", 14), corner_radius=10)
    entry_reseau.grid(row=0, column=1, padx=20, pady=15)
    entry_reseau.insert(0, "192.168.1.0")

    ctk.CTkLabel(input_frame, text="Masque (si pas CIDR) :",
                 font=("Segoe UI", 16, "bold"), text_color=THEME_TEXT_WHITE).grid(row=0, column=2, padx=20, pady=15,
                                                                                  sticky="w")
    entry_masque = ctk.CTkEntry(input_frame, placeholder_text="Ex: 255.255.255.0 ou /24",
                                width=250, height=45, font=("Segoe UI", 14), corner_radius=10)
    entry_masque.grid(row=0, column=3, padx=20, pady=15)

    # Ligne 2: Nb SR + Nb IP
    ctk.CTkLabel(input_frame, text="Nombre de sous-réseaux :",
                 font=("Segoe UI", 16, "bold"), text_color=THEME_TEXT_WHITE).grid(row=1, column=0, padx=20, pady=15,
                                                                                  sticky="w")
    entry_nb = ctk.CTkEntry(input_frame, placeholder_text="Ex: 4 (optionnel)",
                            width=200, height=45, font=("Segoe UI", 14), corner_radius=10)
    entry_nb.grid(row=1, column=1, padx=20, pady=15)
    entry_nb.insert(0, "4")

    ctk.CTkLabel(input_frame, text="Nb d'IP utilisables / SR :",
                 font=("Segoe UI", 16, "bold"), text_color=THEME_TEXT_WHITE).grid(row=1, column=2, padx=20, pady=15,
                                                                                  sticky="w")
    entry_nb_ip = ctk.CTkEntry(input_frame, placeholder_text="Ex: 50 (optionnel)",
                               width=200, height=45, font=("Segoe UI", 14), corner_radius=10)
    entry_nb_ip.grid(row=1, column=3, padx=20, pady=15)

    # --- Logique de mise à jour du masque (Classful) ---
    def mettre_a_jour_masque(*_):
        ip_txt = entry_reseau.get().strip()
        try:
            # Gère les IP sans /
            ip_base = ip_txt.split("/")[0] if "/" in ip_txt else ip_txt

            # S'assurer que ip_base n'est pas vide
            if not ip_base:
                entry_masque.configure(state="normal")
                return

            ip_obj = ipaddress.IPv4Address(ip_base)

            if mode_var.get() == "classful":
                # Détection correcte des classes A, B, C
                if ip_obj >= ipaddress.IPv4Address("1.0.0.0") and ip_obj <= ipaddress.IPv4Address("126.255.255.255"):
                    masque = "255.0.0.0"  # Classe A
                elif ip_obj >= ipaddress.IPv4Address("128.0.0.0") and ip_obj <= ipaddress.IPv4Address(
                        "191.255.255.255"):
                    masque = "255.255.0.0"  # Classe B
                elif ip_obj >= ipaddress.IPv4Address("192.0.0.0") and ip_obj <= ipaddress.IPv4Address(
                        "223.255.255.255"):
                    masque = "255.255.255.0"  # Classe C
                else:
                    masque = ""  # (ex: 127.0.0.1, 224.x.x.x)

                entry_masque.configure(state="normal")
                entry_masque.delete(0, "end")
                entry_masque.insert(0, masque)
                entry_masque.configure(state="disabled")  # Griser le masque
            else:
                # Mode Classless, réactiver le masque
                entry_masque.configure(state="normal")
        except Exception:
            # Si l'IP est invalide, réactiver le masque pour saisie manuelle
            entry_masque.configure(state="normal")

    # --- Liaison des événements ---
    entry_reseau.bind("<FocusOut>", mettre_a_jour_masque)
    entry_reseau.bind("<KeyRelease>", mettre_a_jour_masque)
    radio_classful.configure(command=mettre_a_jour_masque)
    radio_classless.configure(command=mettre_a_jour_masque)

    # Expose les champs pour la fonction principale
    input_frame.entry_masque = entry_masque
    input_frame.entry_nb_ip = entry_nb_ip
    # Association "créative" pour récupérer les valeurs plus tard
    input_frame.entry_nom_decoupe = entry_nom_decoupe
    input_frame.mode_var = mode_var

    return entry_reseau, entry_nb


def creer_bouton_calculer(frame, entry_reseau, entry_nb, table_container):
    # Récupère le frame des inputs (3e enfant du frame principal, après titre et mode)
    try:
        # Titre [0], Mode [1], Nom [2], Inputs [3]
        input_frame = frame.winfo_children()[3]
    except IndexError:
        input_frame = frame  # Fallback

    bouton = ctk.CTkButton(
        input_frame,
        text="Calculer et Enregistrer",  # Texte mis à jour
        command=lambda: afficher_resultats(entry_reseau, entry_nb, table_container),
        width=250,
        height=45,
        font=("Segoe UI", 16, "bold"),
        corner_radius=12,
        # Couleurs du thème
        fg_color=THEME_BLUE,
        hover_color=THEME_BLUE_HOVER,
        text_color=THEME_TEXT_WHITE
    )
    # Ligne 3 = sous les inputs
    bouton.grid(row=3, column=0, columnspan=2, padx=20, pady=20, sticky="w")


def creer_tableau(frame):
    # Le conteneur du tableau prend une couleur de fond grise
    table_container = ctk.CTkScrollableFrame(frame, corner_radius=15, fg_color=THEME_GREY_BUTTON)
    table_container.pack(fill="both", expand=True, padx=30, pady=20)

    # Configure la grille pour qu'elle s'étende sur la largeur
    table_container.grid_columnconfigure(0, weight=1)  # Permet aux colonnes de s'étirer
    table_container.grid_columnconfigure(1, weight=1)
    table_container.grid_columnconfigure(2, weight=1)
    table_container.grid_columnconfigure(3, weight=1)
    table_container.grid_columnconfigure(4, weight=1)

    return table_container


def afficher_resultats(entry_reseau, entry_nb, table_container):
    """Compatible avec ton main : lit aussi les nouveaux inputs via entry_reseau.master."""
    # Efface l'ancien tableau
    for widget in table_container.winfo_children():
        widget.destroy()

    reseau_txt = entry_reseau.get().strip()
    nb_sr_txt = entry_nb.get().strip()

    # Récupérer les nouveaux champs depuis le frame parent des entrées
    input_frame = entry_reseau.master
    masque_txt = input_frame.entry_masque.get().strip() if hasattr(input_frame, "entry_masque") else ""
    nb_ip_txt = input_frame.entry_nb_ip.get().strip() if hasattr(input_frame, "entry_nb_ip") else ""
    nom_decoupe = input_frame.entry_nom_decoupe.get().strip() if hasattr(input_frame, "entry_nom_decoupe") else ""
    mode = input_frame.mode_var.get() if hasattr(input_frame, "mode_var") else "classless"

    # --- Validation du Nom ---
    if not nom_decoupe:
        messagebox.showerror("Erreur de saisie", "Le 'Nom de la découpe' est obligatoire pour l'enregistrement.")
        return

    # Parse nombres optionnels
    nb_sr = None
    nb_ip = None
    try:
        if nb_sr_txt:
            nb_sr = int(nb_sr_txt)
        if nb_ip_txt:
            nb_ip = int(nb_ip_txt)
    except ValueError:
        messagebox.showerror("Erreur de saisie", "Les champs numériques doivent contenir des entiers valides.")
        return

    # Adapter l'IP si mode classful
    if mode == "classful":
        try:
            ip_str = reseau_txt.split("/")[0] if "/" in reseau_txt else reseau_txt
            if not ip_str: raise ValueError("IP vide")
            ip_obj = ipaddress.IPv4Address(ip_str)

            if ip_obj >= ipaddress.IPv4Address("1.0.0.0") and ip_obj <= ipaddress.IPv4Address("126.255.255.255"):
                prefix = 8
            elif ip_obj >= ipaddress.IPv4Address("128.0.0.0") and ip_obj <= ipaddress.IPv4Address("191.255.255.255"):
                prefix = 16
            elif ip_obj >= ipaddress.IPv4Address("192.0.0.0") and ip_obj <= ipaddress.IPv4Address("223.255.255.255"):
                prefix = 24
            else:
                raise ValueError("IP non classée dans A/B/C.")
            reseau_txt = f"{ip_obj}/{prefix}"
            masque_txt = None  # masque ignoré
        except Exception as e:
            messagebox.showerror("Erreur", f"IP classful invalide : {e}")
            return

    # Variable pour l'enregistrement BDD
    net_pour_bdd = None
    masque_sr_pour_bdd = None

    try:
        donnees, prefix, net = calculer_sous_reseaux(
            reseau_de_base=reseau_txt,
            nb_sous_reseaux=nb_sr,
            masque=masque_txt,
            nb_ips_utilisables=nb_ip
        )
        net_pour_bdd = net  # Sauvegarde pour la BDD
        # Calculer le masque des sous-réseaux pour la BDD
        masque_sr_pour_bdd = str(ipaddress.IPv4Network(f"0.0.0.0/{prefix}").netmask)

        # Bandeau info
        info = ctk.CTkLabel(
            table_container,
            text=f"Découpe '{nom_decoupe}' de {net.with_prefixlen} en /{prefix}  (SR générés: {len(donnees)})",
            font=("Segoe UI", 16, "bold"),
            text_color=THEME_BLUE  # Couleur thème
        )
        info.grid(row=0, column=0, columnspan=5, padx=8, pady=(4, 10), sticky="w")

        # Entêtes
        offset = 1
        colonnes = ["Sous-réseau", "Adresse réseau", "Broadcast", "Plage utilisable", "Nb hôtes"]
        for j, col in enumerate(colonnes):
            header = ctk.CTkLabel(
                table_container,
                text=col,
                font=("Segoe UI", 18, "bold"),
                anchor="center",
                fg_color=THEME_BLUE,  # Couleur thème
                text_color=THEME_TEXT_WHITE,
                corner_radius=10
            )
            header.grid(row=offset, column=j, padx=8, pady=12, sticky="nsew")

        # Données
        for i, ligne in enumerate(donnees, start=1):
            # Alternance des couleurs de fond
            bg_color = THEME_GREY_HOVER if i % 2 == 0 else THEME_GREY_BUTTON
            for j, valeur in enumerate(ligne):
                cell = ctk.CTkLabel(
                    table_container,
                    text=valeur,
                    font=("Segoe UI", 15),
                    anchor="center",
                    fg_color=bg_color,
                    corner_radius=8
                )
                cell.grid(row=i + offset, column=j, padx=8, pady=6, sticky="nsew")

    except ValueError as ve:
        messagebox.showerror("Erreur", str(ve))
        return  # Ne pas continuer si le calcul échoue
    except NotImplementedError as nie:
        messagebox.showwarning("Fonction non disponible", str(nie))
        return
    except Exception as e:
        messagebox.showerror("Erreur", f"Une erreur est survenue : {e}")
        return

    # --- Enregistrement dans la base ---
    try:
        id_utilisateur = session.utilisateur_connecte_id
        if id_utilisateur is not None and net_pour_bdd is not None:
            enregistrer_decoupe(
                nom_decoupe=nom_decoupe,
                mode=mode,
                ip_reseau=str(net_pour_bdd.network_address),
                masque_parent=str(net_pour_bdd.netmask),  # Masque du réseau parent
                masque_sr=masque_sr_pour_bdd,  # Masque des sous-réseaux
                nb_sous_reseaux=len(donnees),
                nb_ips_par_sr=nb_ip if nb_ip else None,
                type_decoupe="classique",
                id_utilisateur=id_utilisateur,
                sous_reseaux=donnees
            )
            messagebox.showinfo("Succès", f"La découpe '{nom_decoupe}' a été calculée et enregistrée avec succès.")
        else:
            messagebox.showwarning("Utilisateur",
                                   "Utilisateur non trouvé ou erreur de calcul. La découpe n'a pas été enregistrée.")
    except sqlite3.IntegrityError:
        messagebox.showerror("Erreur Base de Données",
                             f"Le nom de découpe '{nom_decoupe}' existe déjà. Veuillez en choisir un autre.")
    except Exception as e:
        messagebox.showwarning("Base de données", f"Erreur lors de l'enregistrement : {e}")


def creer_bouton_quitter(frame, app):
    bouton = ctk.CTkButton(
        frame,
        text="Fermer",  # Texte mis à jour
        command=app.destroy,  # Utilise destroy() pour fermer cette fenêtre
        width=200,
        height=40,
        font=("Segoe UI", 14, "bold"),
        corner_radius=10,
        # Couleurs du thème
        fg_color=THEME_GREY_BUTTON,
        hover_color=THEME_GREY_HOVER,
        text_color=THEME_TEXT_WHITE
    )
    bouton.pack(pady=20, side="bottom")  # Placé en bas


def enregistrer_decoupe(nom_decoupe, mode, ip_reseau, masque_parent, masque_sr, nb_sous_reseaux, nb_ips_par_sr,
                        type_decoupe, id_utilisateur, sous_reseaux):
    conn = get_connection()
    cur = conn.cursor()

    # Insérer la découpe (utilise le masque parent)
    cur.execute("""
        INSERT INTO decoupe (nom_decoupe, mode, ip_reseau, masque, nombre_sous_reseaux, nombre_ips_par_sr, type_decoupe, id_responsable)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        nom_decoupe,
        mode,
        ip_reseau,
        masque_parent,  # Masque du réseau d'origine
        nb_sous_reseaux,
        nb_ips_par_sr,
        "classique",
        id_utilisateur
    ))

    id_decoupe = cur.lastrowid

    # Insérer les sous-réseaux (utilise le masque_sr calculé)
    for ligne in sous_reseaux:
        _, ip_reseau_sr, ip_broadcast, plage, nb_ips = ligne

        # Correction pour gérer "Aucun"
        ip_debut, ip_fin = "N/A", "N/A"
        if " - " in plage:
            ip_debut, ip_fin = plage.split(" - ")

        cur.execute("""
            INSERT INTO sous_reseau (id_decoupe, ip_reseau, masque, ip_debut, ip_fin, ip_broadcast, nb_ips)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            id_decoupe,
            ip_reseau_sr,
            masque_sr,  # Masque correct du sous-réseau
            ip_debut,
            ip_fin,
            ip_broadcast,
            int(nb_ips)
        ))

    conn.commit()
    conn.close()


def ouvrir_fenetre_decoupe():
    ctk.set_appearance_mode("dark")  # Forcer le mode sombre
    ctk.set_default_color_theme("dark-blue")

    app = ctk.CTk()
    app.configure(fg_color=THEME_BACKGROUND)  # Fond de la fenêtre

    # --- MISE EN PLEIN ÉCRAN (Manuelle) ---
    app.update_idletasks()
    largeur = app.winfo_screenwidth()
    hauteur = app.winfo_screenheight()
    app.geometry(f"{largeur}x{hauteur}+0+0")
    # --- FIN PLEIN ÉCRAN ---

    configurer_fenetre(app)
    frame = creer_frame_principale(app)  # Le cadre principal prend la couleur de fond

    # Création des zones
    creer_titre(frame)
    entry_reseau, entry_nb = creer_zone_saisie(frame)
    table_container = creer_tableau(frame)

    # Le bouton calculer est créé et placé DANS la zone de saisie
    creer_bouton_calculer(frame, entry_reseau, entry_nb, table_container)

    # Le bouton quitter est à l'extérieur, en bas
    creer_bouton_quitter(frame, app)

    app.mainloop()