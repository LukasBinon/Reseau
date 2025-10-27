import ipaddress
import customtkinter as ctk
from tkinter import messagebox

import session
from database import get_connection, get_user_id


# =========================
#   LOGIQUE & UTILITAIRES
# =========================
def _parse_network(reseau_de_base: str, masque_str: str | None):
    """
    Accepte :
      - '192.168.1.0/24' (CIDR)
      - '192.168.1.0' + masque '/24' ou '255.255.255.0'
    Retourne un IPv4Network (strict=False pour tolérer une IP d'hôte).
    """
    if not reseau_de_base or not reseau_de_base.strip(): #strip supprime les espaces
        raise ValueError("Réseau de base manquant.")

    reseau_de_base = reseau_de_base.strip()

    # Si CIDR déjà fourni
    if "/" in reseau_de_base:
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
#   UI (compatible ton main)
# =========================
def configurer_fenetre(app):
    app.title("🌐 Calculateur de Découpe Réseau IP")
    app.update_idletasks()


def creer_frame_principale(app):
    frame = ctk.CTkFrame(app, corner_radius=20)
    frame.pack(fill="both", expand=True, padx=50, pady=40)
    return frame


def creer_titre(frame):
    titre = ctk.CTkLabel(
        frame,
        text="🌐 Calculateur de Découpe Réseau IP",
        font=("Arial", 36, "bold")
    )
    titre.pack(pady=30)


def creer_zone_saisie(frame):
    """
    ⚠️ Compat : renvoie toujours (entry_reseau, entry_nb) comme dans ton main.
    Mais on ajoute en interne :
      - entry_masque (si l'IP n'a pas de CIDR)
      - entry_nb_ip (nombre d'IP utilisables / SR)
      - entry_nom_decoupe (nom de la découpe)
      - mode_var (classful/classless)
    """
    # Ligne -1 : Choix du mode IP
    mode_frame = ctk.CTkFrame(frame, corner_radius=10)
    mode_frame.pack(pady=(10, 0), padx=30, fill="x")

    mode_label = ctk.CTkLabel(mode_frame, text="Type d'adresse IP :", font=("Arial", 16, "bold"))
    mode_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")

    mode_var = ctk.StringVar(value="classless")
    radio_classful = ctk.CTkRadioButton(mode_frame, text="Classful", variable=mode_var, value="classful", font=("Arial", 14))
    radio_classless = ctk.CTkRadioButton(mode_frame, text="Classless", variable=mode_var, value="classless", font=("Arial", 14))
    radio_classful.grid(row=0, column=1, padx=10)
    radio_classless.grid(row=0, column=2, padx=10)



    # Ligne 0 : Nom de la découpe
    nom_frame = ctk.CTkFrame(frame, corner_radius=10)
    nom_frame.pack(pady=(10, 0), padx=30, fill="x")

    ctk.CTkLabel(nom_frame, text="Nom de la découpe :", font=("Arial", 16, "bold")).grid(row=0, column=0, padx=20, pady=10, sticky="w")
    entry_nom_decoupe = ctk.CTkEntry(nom_frame, placeholder_text="Ex: Réseau bureau", width=300, height=40, font=("Arial", 14))
    entry_nom_decoupe.grid(row=0, column=1, padx=20, pady=10)

    # Ligne 1 : Réseau de base + masque
    input_frame = ctk.CTkFrame(frame, corner_radius=15)
    input_frame.pack(pady=20, padx=30, fill="x")

    ctk.CTkLabel(input_frame, text="Réseau de base :", font=("Arial", 16, "bold")).grid(row=0, column=0, padx=20, pady=15, sticky="w")
    entry_reseau = ctk.CTkEntry(input_frame, placeholder_text="Ex: 192.168.1.0 ou 192.168.1.0/24", width=260, height=40, font=("Arial", 14))
    entry_reseau.grid(row=0, column=1, padx=20, pady=15)
    entry_reseau.insert(0, "192.168.1.0")

    ctk.CTkLabel(input_frame, text="Masque (si pas CIDR) :", font=("Arial", 16, "bold")).grid(row=0, column=2, padx=20, pady=15, sticky="w")
    entry_masque = ctk.CTkEntry(input_frame, placeholder_text="Ex: 255.255.255.0 ou /24", width=200, height=40, font=("Arial", 14))
    entry_masque.grid(row=0, column=3, padx=20, pady=15)

    def mettre_a_jour_masque(*_):
        ip_txt = entry_reseau.get().strip()
        try:
            ip_obj = ipaddress.IPv4Address(ip_txt.split("/")[0])
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
                    masque = ""
                entry_masque.configure(state="normal")
                entry_masque.delete(0, "end")
                entry_masque.insert(0, masque)
                entry_masque.configure(state="disabled")
            else:
                entry_masque.configure(state="normal")
        except Exception:
            entry_masque.configure(state="normal")

    # 🔗 Liaison des événements

    entry_reseau.bind("<FocusOut>", mettre_a_jour_masque)
    entry_reseau.bind("<KeyRelease>", mettre_a_jour_masque)
    radio_classful.configure(command=mettre_a_jour_masque)
    radio_classless.configure(command=mettre_a_jour_masque)

    # Ligne 2 : Nombre de sous-réseaux + IP utilisables
    ctk.CTkLabel(input_frame, text="Nombre de sous-réseaux :", font=("Arial", 16, "bold")).grid(row=1, column=0, padx=20, pady=15, sticky="w")
    entry_nb = ctk.CTkEntry(input_frame, placeholder_text="Ex: 4 (optionnel)", width=200, height=40, font=("Arial", 14))
    entry_nb.grid(row=1, column=1, padx=20, pady=15)
    entry_nb.insert(0, "4")

    ctk.CTkLabel(input_frame, text="Nb d'IP utilisables / SR :", font=("Arial", 16, "bold")).grid(row=1, column=2, padx=20, pady=15, sticky="w")
    entry_nb_ip = ctk.CTkEntry(input_frame, placeholder_text="Ex: 50 (optionnel)", width=200, height=40, font=("Arial", 14))
    entry_nb_ip.grid(row=1, column=3, padx=20, pady=15)

    # Expose les nouveaux champs
    input_frame.entry_masque = entry_masque
    input_frame.entry_nb_ip = entry_nb_ip
    input_frame.entry_nom_decoupe = entry_nom_decoupe
    input_frame.mode_var = mode_var

    return entry_reseau, entry_nb
def creer_bouton_calculer(frame, entry_reseau, entry_nb, table_container):
    # Récupère le frame des inputs (3e enfant du frame principal)
    input_frame = frame.winfo_children()[2]
    bouton = ctk.CTkButton(
        input_frame,
        text="✨ Calculer",
        command=lambda: afficher_resultats(entry_reseau, entry_nb, table_container),
        width=150,
        height=40,
        font=("Arial", 16, "bold"),
        corner_radius=10
    )
    # Ligne 2 = sous les inputs
    bouton.grid(row=2, column=0, columnspan=4, padx=20, pady=10, sticky="w")


def creer_tableau(frame):
    table_container = ctk.CTkScrollableFrame(frame, corner_radius=15)
    table_container.pack(fill="both", expand=True, padx=30, pady=20)
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
            ip_str = reseau_txt.split("/")[0]
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

    try:
        donnees, prefix, net = calculer_sous_reseaux(
            reseau_de_base=reseau_txt,
            nb_sous_reseaux=nb_sr,
            masque=masque_txt if "/" not in reseau_txt else None,
            nb_ips_utilisables=nb_ip
        )

        # Bandeau info
        info = ctk.CTkLabel(
            table_container,
            text=f"Découpe '{nom_decoupe}' de {net.with_prefixlen} en /{prefix}  (SR générés: {len(donnees)})",
            font=("Arial", 14, "bold"),
            text_color=("#1f538d", "#8ab4f8")
        )
        info.grid(row=0, column=0, columnspan=5, padx=8, pady=(4, 4), sticky="w")

        # Décaler entêtes et données d'une ligne
        offset = 1
        colonnes = ["Sous-réseau", "Adresse réseau", "Broadcast", "Plage utilisable", "Nb hôtes"]
        for j, col in enumerate(colonnes):
            header = ctk.CTkLabel(
                table_container,
                text=col,
                font=("Arial", 18, "bold"),
                width=220,
                anchor="center",
                fg_color=("#3b8ed0", "#1f538d"),
                text_color="white",
                corner_radius=10
            )
            header.grid(row=offset, column=j, padx=8, pady=12, sticky="ew")

        # Afficher données sous les entêtes (avec offset)
        for i, ligne in enumerate(donnees, start=1):
            bg_color = ("#d9d9d9", "#2b2b2b") if i % 2 == 0 else ("#e6e6e6", "#333333")
            for j, valeur in enumerate(ligne):
                cell = ctk.CTkLabel(
                    table_container,
                    text=valeur,
                    font=("Arial", 15),
                    width=220,
                    anchor="center",
                    fg_color=bg_color,
                    corner_radius=8
                )
                cell.grid(row=i + offset, column=j, padx=8, pady=6, sticky="ew")

    except ValueError as ve:
        messagebox.showerror("Erreur", str(ve))
    except NotImplementedError as nie:
        messagebox.showwarning("Fonction non disponible", str(nie))
    except Exception as e:
        messagebox.showerror("Erreur", f"Une erreur est survenue : {e}")
# Enregistrement dans la base
    try:
        id_utilisateur = session.utilisateur_connecte_id
        if id_utilisateur is not None:
            enregistrer_decoupe(
            nom_decoupe=nom_decoupe,
            mode=mode,
            ip_reseau=str(net.network_address),
            masque=str(net.netmask),
            nb_sous_reseaux=len(donnees),
            nb_ips_par_sr=nb_ip if nb_ip else None,
            type_decoupe="classique",
            id_utilisateur=id_utilisateur,
            sous_reseaux=donnees
            )
        else:
             messagebox.showwarning("Utilisateur", "Utilisateur non trouvé. La découpe n'a pas été enregistrée.")
    except Exception as e:
        messagebox.showwarning("Base de données", f"Erreur lors de l'enregistrement : {e}")

def creer_bouton_quitter(frame, app):
    bouton = ctk.CTkButton(
        frame,
        text="❌ Quitter",
        command=app.quit,
        width=150,
        height=40,
        font=("Arial", 14, "bold"),
        corner_radius=10
    )
    bouton.pack(pady=10)

def enregistrer_decoupe(nom_decoupe, mode, ip_reseau, masque, nb_sous_reseaux, nb_ips_par_sr, type_decoupe, id_utilisateur, sous_reseaux):
    conn = get_connection()
    cur = conn.cursor()

    # Insérer la découpe
    cur.execute("""
        INSERT INTO decoupe (nom_decoupe, mode, ip_reseau, masque, nombre_sous_reseaux, nombre_ips_par_sr, type_decoupe, id_responsable)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        nom_decoupe,
        mode,
        ip_reseau,
        masque,
        nb_sous_reseaux,
        nb_ips_par_sr,
        "classique",  # pour l'instant, on ne gère que le mode classique
        id_utilisateur
    ))

    id_decoupe = cur.lastrowid

    # Insérer les sous-réseaux
    for ligne in sous_reseaux:
        _, ip_reseau_sr, ip_broadcast, plage, nb_ips = ligne
        ip_debut, ip_fin = plage.split(" - ") if " - " in plage else ("", "")
        cur.execute("""
            INSERT INTO sous_reseau (id_decoupe, ip_reseau, masque, ip_debut, ip_fin, ip_broadcast, nb_ips)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            id_decoupe,
            ip_reseau_sr,
            masque,
            ip_debut,
            ip_fin,
            ip_broadcast,
            int(nb_ips)
        ))

    conn.commit()
    conn.close()

def ouvrir_fenetre_decoupe():
    ctk.set_appearance_mode("system")  # "dark" ou "light"
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.geometry("1200x800")

    configurer_fenetre(app)
    frame = creer_frame_principale(app)
    creer_titre(frame)

    entry_reseau, entry_nb = creer_zone_saisie(frame)
    table_container = creer_tableau(frame)
    creer_bouton_calculer(frame, entry_reseau, entry_nb, table_container)
    creer_bouton_quitter(frame, app)

    app.mainloop()
