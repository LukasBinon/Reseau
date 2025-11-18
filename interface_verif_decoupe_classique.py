import customtkinter as ctk
from tkinter import messagebox
import re
import session
from database import ajouter_test_historique
from ipaddress import IPv4Address, IPv4Network
from verif_decoupe_classique import determiner_classe, ClasseIPV4, decoupe_par_sous_reseaux, decoupe_par_nombre_hote

# --- Thèmes personnalisés ---
THEME_BACKGROUND = "#1e1e1e"
THEME_GREY_BUTTON = "#2d2d2d"
THEME_GREY_HOVER = "#3a3a3a"
THEME_BLUE = "#0078d7"
THEME_BLUE_HOVER = "#005a9e"
THEME_TEXT_WHITE = "#ffffff"

# --- Interface ---
def ouvrir_fenetre():
    # Couleurs du thème
    bleu = "#2D89EF"
    bleuHover = "#2563EB"
    gris = "#2c2c2e"
    white = "white"
    bg = "#1c1c1e"

    # Configuration de l'apparence
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    # Fenêtre principale

    app = ctk.CTkToplevel()
    app.title("Vérificateur découpe réseau")
    app.state('zoomed')
    app.configure(fg_color=bg)

    app.transient()
    app.grab_set()

    # Frame principal
    frame = ctk.CTkFrame(app, fg_color=bg)
    frame.pack(fill="both", expand=True, padx=6, pady=6)

    # Titre
    titre = ctk.CTkLabel(frame, text="Vérificateur découpe réseau",
                         font=("Segoe UI", 30, "bold"),
                         text_color=bleu)
    titre.pack(pady=40)

    # Frame d'entrées
    input_frame = ctk.CTkFrame(frame, fg_color="transparent")
    input_frame.pack(pady=10, fill="x", padx=30)

    # Centrer les inputs
    input_frame.grid_columnconfigure(0, weight=1)
    input_frame.grid_columnconfigure(1, weight=1)

    # Adresse IP
    ctk.CTkLabel(input_frame, text="Adresse IP :",
                 font=("Segoe UI", 16),
                 text_color=white).grid(row=0, column=0, padx=10, pady=15, sticky="e")
    inputIp = ctk.CTkEntry(input_frame, placeholder_text="192.168.1.0",
                           width=350, height=45, corner_radius=10)
    inputIp.grid(row=0, column=1, padx=10, pady=15, sticky="w")

    # CIDR
    ctk.CTkLabel(input_frame, text="CIDR :",
                 font=("Segoe UI", 16),
                 text_color=white).grid(row=1, column=0, padx=10, pady=15, sticky="e")
    inputCIDR = ctk.CTkEntry(input_frame, placeholder_text="/24",
                             width=350, height=45, corner_radius=10)
    inputCIDR.grid(row=1, column=1, padx=10, pady=15, sticky="w")

    # Masque
    ctk.CTkLabel(input_frame, text="Masque :",
                 font=("Segoe UI", 16),
                 text_color=white).grid(row=2, column=0, padx=10, pady=15, sticky="e")
    inputMasque = ctk.CTkEntry(input_frame, placeholder_text="255.255.255.0",
                               width=350, height=45, corner_radius=10)
    inputMasque.grid(row=2, column=1, padx=10, pady=15, sticky="w")

    # Variable pour le choix
    choix_var = ctk.StringVar(value="sr")

    # Radio buttons
    radio_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
    radio_frame.grid(row=3, column=0, columnspan=2, pady=15)

    ctk.CTkLabel(radio_frame, text="Choisir :",
                 font=("Segoe UI", 16),
                 text_color=white).pack(side="left", padx=10)

    radio_sr = ctk.CTkRadioButton(radio_frame, text="Nb sous-réseaux",
                                  variable=choix_var, value="sr",
                                  text_color=white, font=("Segoe UI", 14))
    radio_sr.pack(side="left", padx=20)

    radio_hote = ctk.CTkRadioButton(radio_frame, text="Nb hôtes par SR",
                                    variable=choix_var, value="hote",
                                    text_color=white, font=("Segoe UI", 14))
    radio_hote.pack(side="left", padx=20)

    # Valeur
    ctk.CTkLabel(input_frame, text="Valeur :",
                 font=("Segoe UI", 16),
                 text_color=white).grid(row=4, column=0, padx=10, pady=15, sticky="e")
    inputValeur = ctk.CTkEntry(input_frame, placeholder_text="Ex: 4",
                               width=350, height=45, corner_radius=10)
    inputValeur.grid(row=4, column=1, padx=10, pady=15, sticky="w")

    # Zone de résultats
    result_textbox = ctk.CTkTextbox(frame, font=("Segoe UI", 14),
                                    state="disabled", wrap="word", corner_radius=10,
                                    fg_color=gris)

    # Cadre pour les boutons
    button_frame = ctk.CTkFrame(frame, fg_color="transparent")

    button_frame.pack(side="bottom", pady=20)
    result_textbox.pack(pady=10, fill="both", expand=True, padx=10)

    # Fonction de clic (à définir selon votre logique)
    def bouton_clique():
        # Récupérer les données entrées par l'utilisateur
        ip = inputIp.get()
        masque = inputMasque.get()
        cidr = inputCIDR.get()
        choix = choix_var.get()
        valeur = inputValeur.get()
        user_id = session.utilisateur_connecte_id

        # Vérifier si l'adresse ip est correct
        try:
            adresse_ip = IPv4Address(ip)
            if determiner_classe(adresse_ip) == ClasseIPV4.CLASSE_RESERVE:
                messagebox.showerror("Erreur", "Cette adreesse IP est réservé", parent=app)
                ajouter_test_historique(
                    "Vérification pour une découpe classique",
                    f"Ip : {ip}, CIDR : {cidr}, Masque : {masque}, choix : {"Sous-Réseaux" if choix == "sr" else "Nombre d'hôte"}, Valeur : {valeur}",
                    "Cette adresse IP est réservé",
                    False,
                    user_id
                )
                return
        except ValueError:
            messagebox.showerror("Erreur", "L'adresse IP est invalide", parent=app)
            ajouter_test_historique(
                "Vérification pour une découpe classique",
                f"Ip : {ip}, CIDR : {cidr}, Masque : {masque}, Choix : {"Sous-Réseaux" if choix == "sr" else "Nombre d'hôte"}, Valeur : {valeur}",
                "L'adresse IP est invalide",
                False,
                user_id
            )
            return

        # Vérifier le masque donnée par l'utilisateur
        if cidr:
            if not cidr.isdigit():
                messagebox.showerror("Erreur", "Le CIDR ne peux contenir que des nombres", parent=app)
                ajouter_test_historique(
                    "Vérification pour une découpe classique",
                    f"Ip : {ip}, CIDR : {cidr}, Masque : {masque}, choix : {"Sous-Réseaux" if choix == "sr" else "Nombre d'hôte"}, Valeur : {valeur}",
                    "Le CIDR ne peux contenir que des nombres",
                    False,
                    user_id
                )
                return
            cidr = int(cidr)
            if cidr < 8 or cidr > 30:
                messagebox.showerror("Erreur", "Le CIDR doit se trouver entre 8 et 30", parent=app)
                ajouter_test_historique(
                    "Vérification pour une découpe classique",
                    f"Ip : {ip}, CIDR : {cidr}, Masque : {masque}, choix : {"Sous-Réseaux" if choix == "sr" else "Nombre d'hôte"}, Valeur : {valeur}",
                    "Le CIDR doit se trouver entre 8 et 30",
                    False,
                    user_id
                )
                return

            reseau = IPv4Network(f"{ip}/{cidr}", strict=False)
        elif masque:
            try:
                reseau = IPv4Network(f"{ip}/{masque}", strict=False)
            except ValueError:
                messagebox.showerror("Erreur", "Le masque n'est pas possible", parent=app)
                ajouter_test_historique(
                    "Vérification pour une découpe classique",
                    f"Ip : {ip}, CIDR : {cidr}, Masque : {masque}, choix : {"Sous-Réseaux" if choix == "sr" else "Nombre d'hôte"}, Valeur : {valeur}",
                    "Ce masque n'est pas possible",
                    False,
                    user_id
                )
                return
        else:
            messagebox.showerror("Erreur", "Vous devez entrer un CIDR ou un masque", parent=app)
            ajouter_test_historique(
                "Vérification pour une découpe classique",
                f"Ip : {ip}, CIDR : {cidr}, Masque : {masque}, choix : {"Sous-Réseaux" if choix == "sr" else "Nombre d'hôte"}, Valeur : {valeur}",
                "Vous devez entrer un CIDR ou un masque",
                False,
                user_id
            )
            return

        # Vérifier si la valeur demandés par l'utilisateur est possible (pas de 0 ou de valeur négative)
        try:
            valeur = int(valeur)
            if valeur <= 0:
                messagebox.showerror("Erreur", "La valeur entrée doit être supérieur à 0", parent=app)
                ajouter_test_historique(
                    "Vérification pour une découpe classique",
                    f"Ip : {ip}, CIDR : {cidr}, Masque : {masque}, choix : {"Sous-Réseaux" if choix == "sr" else "Nombre d'hôte"}, Valeur : {valeur}",
                    "La valeur entrée doit être supérieur à 0",
                    False,
                    user_id
                )
                return
        except ValueError:
            messagebox.showerror("Erreur", "La valeur entrée doit être un nombre", parent=app)
            ajouter_test_historique(
                "Vérification pour une découpe classique",
                f"Ip : {ip}, CIDR : {cidr}, Masque : {masque}, choix : {"Sous-Réseaux" if choix == "sr" else "Nombre d'hôte"}, Valeur : {valeur}",
                "La valeur entré doit être un nombre",
                False,
                user_id
            )
            return

        # Exécuter la bonne méthode en fonction de ce que demande l'utilisateur
        if choix == 'sr':
            possible, nb_ip = decoupe_par_sous_reseaux(reseau, valeur)
            message = (
                f"Réseau de base : {reseau.with_prefixlen}\n"
                f"Total IP utilisable par sous-réseaux : {nb_ip}\n"
                f"--------------------------------------------------\n"
                f"Résultat : Découpe classique possible : {'OUI' if possible else 'NON'}\n"
                f"--------------------------------------------------"
            )
            result_textbox.configure(state="normal")  # Activer
            result_textbox.delete("1.0", "end")
            result_textbox.insert("1.0", message)
            couleur = "#00ff00" if possible else "#ff0000"
            result_textbox.configure(text_color=couleur)
            result_textbox.configure(state="disabled")
            ajouter_test_historique(
                "Vérification pour une découpe classique",
                f"Ip : {ip}, CIDR : {cidr}, Masque : {masque}, choix : {"Sous-Réseaux" if choix == "sr" else "Nombre d'hôte"}, Valeur : {valeur}",
                message,
                True,
                user_id
            )
        elif choix == 'hote':
            possible, nb_sr = decoupe_par_nombre_hote(reseau, valeur)
            message = (
                f"Réseau de base : {reseau.with_prefixlen}\n"
                f"Total de sous-réseaux possible : {nb_sr}\n"
                f"--------------------------------------------------\n"
                f"Résultat : Découpe classique possible : {'OUI' if possible else 'NON'}\n"
                f"--------------------------------------------------"
            )
            result_textbox.configure(state="normal")  # Activer
            result_textbox.delete("1.0", "end")
            result_textbox.insert("1.0", message)
            couleur = "#00ff00" if possible else "#ff0000"  # Vert si True, Rouge si False
            result_textbox.configure(text_color=couleur)
            result_textbox.configure(state="disabled")
            ajouter_test_historique(
                "Vérification pour une découpe classique",
                f"Ip : {ip}, CIDR : {cidr}, Masque : {masque}, choix : {"Sous-Réseaux" if choix == "sr" else "Nombre d'hôte"}, Valeur : {valeur}",
                message,
                True,
                user_id
            )
        return

    # Bouton Vérifier
    btn_verifier = ctk.CTkButton(button_frame, text="Vérifier",
                                 command=bouton_clique,
                                 fg_color=bleu,
                                 hover_color=bleuHover,
                                 text_color=white,
                                 width=250,
                                 height=45,
                                 font=("Segoe UI", 16, "bold"),
                                 corner_radius=12)
    btn_verifier.pack(side="left", padx=10)

    # Bouton Fermer
    btn_quitter = ctk.CTkButton(button_frame, text="Fermer",
                                command=app.destroy,
                                fg_color=bg,
                                hover_color=gris,
                                text_color=white,
                                width=250,
                                height=45,
                                font=("Segoe UI", 16, "bold"),
                                corner_radius=12)
    btn_quitter.pack(side="left", padx=10)


