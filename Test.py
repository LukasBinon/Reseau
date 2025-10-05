import ipaddress
import customtkinter as ctk


def calculer_sous_reseaux(reseau_de_base, nb_sous_reseaux):
    """Calcule les sous-réseaux."""

    # Convertit le texte en objet réseau (ex: "192.168.1.0/24" devient un objet manipulable)
    reseau = ipaddress.ip_network(reseau_de_base)

    # Calcule le nouveau masque nécessaire pour créer les sous-réseaux
    # Exemple: pour 4 SR, on fait 24 + (4-1).bit_length() = 24 + 2 = /26
    nouveau_prefixe = reseau.prefixlen + (nb_sous_reseaux - 1).bit_length()

    # Découpe le réseau en sous-réseaux avec le nouveau masque
    sous_reseaux = list(reseau.subnets(new_prefix=nouveau_prefixe))

    # Liste qui va contenir les infos de chaque sous-réseau
    resultats = []

    # Parcourt chaque sous-réseau (i = numéro, sr = sous-réseau)
    for i, sr in enumerate(sous_reseaux, start=1):
        # Récupère l'adresse réseau (ex: 192.168.1.0)
        adresse_reseau = str(sr.network_address)

        # Récupère l'adresse broadcast (ex: 192.168.1.63)
        adresse_broadcast = str(sr.broadcast_address)

        # Liste toutes les IPs utilisables (machines) du sous-réseau
        hosts = list(sr.hosts())

        # Vérifie s'il y a des hôtes disponibles
        if hosts:
            # Crée la plage: première IP - dernière IP (ex: 192.168.1.1 - 192.168.1.62)
            plage = f"{hosts[0]} - {hosts[-1]}"
            # Compte le nombre d'hôtes
            nb_hotes = len(hosts)
        else:
            # Si pas d'hôtes (réseau trop petit)
            plage = "Aucun"
            nb_hotes = 0

        # Ajoute toutes les infos de ce sous-réseau à la liste des résultats
        resultats.append([
            f"Sous-réseau {i}",  # Nom du sous-réseau
            adresse_reseau,  # Adresse réseau
            adresse_broadcast,  # Adresse broadcast
            plage,  # Plage d'IPs utilisables
            str(nb_hotes)  # Nombre d'hôtes
        ])

    # Retourne la liste complète de tous les sous-réseaux
    return resultats


def configurer_fenetre(app):
    """Configure la fenêtre principale."""
    app.title("🌐 Calculateur de Découpe Réseau IP")
    # Plein écran après que la fenêtre soit créée
    app.update_idletasks()



def creer_frame_principale(app):
    """Crée le cadre principal."""
    frame = ctk.CTkFrame(app, corner_radius=20)
    frame.pack(fill="both", expand=True, padx=50, pady=40)
    return frame


def creer_titre(frame):
    """Crée le titre."""
    titre = ctk.CTkLabel(
        frame,
        text="🌐 Calculateur de Découpe Réseau IP",
        font=("Arial", 36, "bold")
    )
    titre.pack(pady=30)


def creer_zone_saisie(frame):
    """Crée la zone pour entrer le réseau et le nombre."""
    input_frame = ctk.CTkFrame(frame, corner_radius=15)
    input_frame.pack(pady=20, padx=30, fill="x")

    # Label et champ pour le réseau
    ctk.CTkLabel(
        input_frame,
        text="Réseau de base :",
        font=("Arial", 16, "bold")
    ).grid(row=0, column=0, padx=20, pady=15, sticky="w")

    entry_reseau = ctk.CTkEntry(
        input_frame,
        placeholder_text="Ex: 192.168.1.0/24",
        width=250,
        height=40,
        font=("Arial", 14)
    )
    entry_reseau.grid(row=0, column=1, padx=20, pady=15)
    entry_reseau.insert(0, "192.168.1.0/24")

    # Label et champ pour le nombre
    ctk.CTkLabel(
        input_frame,
        text="Nombre de sous-réseaux :",
        font=("Arial", 16, "bold")
    ).grid(row=0, column=2, padx=20, pady=15, sticky="w")

    entry_nb = ctk.CTkEntry(
        input_frame,
        placeholder_text="Ex: 4",
        width=150,
        height=40,
        font=("Arial", 14)
    )
    entry_nb.grid(row=0, column=3, padx=20, pady=15)
    entry_nb.insert(0, "4")

    return entry_reseau, entry_nb


def creer_bouton_calculer(frame, entry_reseau, entry_nb, table_container):
    """Crée le bouton pour calculer."""
    input_frame = frame.winfo_children()[1]  # Récupère le frame des inputs

    bouton = ctk.CTkButton(
        input_frame,
        text="✨ Calculer",
        command=lambda: afficher_resultats(entry_reseau, entry_nb, table_container),
        width=150,
        height=40,
        font=("Arial", 16, "bold"),
        corner_radius=10
    )
    bouton.grid(row=0, column=4, padx=20, pady=15)


def creer_tableau(frame):
    """Crée le tableau scrollable."""
    table_container = ctk.CTkScrollableFrame(frame, corner_radius=15)
    table_container.pack(fill="both", expand=True, padx=30, pady=20)
    return table_container


def afficher_entetes(table_container):
    """Affiche les en-têtes du tableau."""
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
        header.grid(row=0, column=j, padx=8, pady=12, sticky="ew")


def afficher_donnees(table_container, donnees):
    """Affiche les données dans le tableau."""
    for i, ligne in enumerate(donnees, start=1):
        # Couleur alternée pour les lignes
        if i % 2 == 0:
            bg_color = ("#d9d9d9", "#2b2b2b")
        else:
            bg_color = ("#e6e6e6", "#333333")

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
            cell.grid(row=i, column=j, padx=8, pady=6, sticky="ew")


def afficher_resultats(entry_reseau, entry_nb, table_container):
    """Recalcule et affiche les résultats."""
    # Efface l'ancien contenu
    for widget in table_container.winfo_children():
        widget.destroy()

    # Récupère les valeurs
    reseau = entry_reseau.get()
    nb = int(entry_nb.get())

    # Calcule
    donnees = calculer_sous_reseaux(reseau, nb)

    # Affiche
    afficher_entetes(table_container)
    afficher_donnees(table_container, donnees)


def creer_bouton_quitter(frame, app):
    """Crée le bouton Quitter."""
    bouton = ctk.CTkButton(
        frame,
        text="❌ Quitter",
        command=app.quit,
        width=150,
        height=40,
        font=("Arial", 14, "bold"),
        corner_radius=10
    )
    bouton.pack(pady=20)

