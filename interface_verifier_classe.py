import customtkinter as ctk
import session
import re
from ipaddress import IPv4Network, AddressValueError
from verifier_classe import ipv4_valide, verifie_classfull, ClasseIPV4
from database import ajouter_test_historique


# --- Thèmes personnalisés ---
THEME_BACKGROUND = "#1e1e1e"
THEME_GREY_BUTTON = "#2d2d2d"
THEME_GREY_HOVER = "#3a3a3a"
THEME_BLUE = "#0078d7"
THEME_BLUE_HOVER = "#005a9e"
THEME_TEXT_WHITE = "#ffffff"

# Fonction pour afficher une popup élégante
def afficher_popup(titre, message):
    popup = ctk.CTkToplevel()
    popup.geometry("300x150")
    popup.title(titre)
    popup.grab_set()  # Empêche l'interaction avec la fenêtre principale

    label = ctk.CTkLabel(popup, text=message, wraplength=250, justify="center")
    label.pack(pady=20)

    btn_close = ctk.CTkButton(popup, text="Fermer", command=popup.destroy)
    btn_close.pack(pady=10)

def ouvrir_fenetre():
    historique_resultats = []  # Liste pour stocker tous les résultats

    def bouton_clique():
        ip = inputIp.get()
        cidr = inputCIDR.get()
        masque = inputMasque.get()
        user_id = session.utilisateur_connecte_id
        ip_complet = None

        # Nettoyer le tableau avant d'afficher (mais garder historique)
        for widget in tableau_frame.winfo_children():
            widget.destroy()

        # Créer les entêtes
        for j, col in enumerate(colonnes):
            ctk.CTkLabel(
                tableau_frame,
                text=col,
                font=("Segoe UI", 16, "bold"),
                fg_color=THEME_BLUE,
                text_color="white",
                corner_radius=8
            ).grid(row=0, column=j, padx=5, pady=8, sticky="nsew")

        # Vérification IP
        if not ipv4_valide(ip):
            afficher_popup("Erreur", "Adresse IP invalide")
            # Ajout dans historique + DB
            ajouter_test_historique(
                type_test="Vérification IP",
                entree=ip,
                resultat="Adresse IP invalide",
                est_valide=False,
                id_utilisateur=user_id  # à remplacer par l'ID réel
            )
        else:
            try:
                if cidr:
                    ip_complet = f"{ip}/{cidr}"
                elif masque:
                    if re.match(r"^(0|255)\.(0|255)\.(0|255)\.(0|255)$", masque):
                        ip_complet = f"{ip}/{masque}"
                    else:
                        afficher_popup("Erreur", "Masque invalide")
                        ajouter_test_historique("Vérification IP", ip, "Masque invalide", False, user_id)
                else:
                    afficher_popup("Erreur", "Veuillez entrer un CIDR ou un masque.")
                    ajouter_test_historique("Vérification IP", ip, "CIDR ou masque manquant", False, user_id)

                if ip_complet is not None:
                    reseau = IPv4Network(ip_complet, strict=False)
                    if not 8 <= reseau.prefixlen <= 30:
                        afficher_popup("Erreur", "Masque invalide")
                        historique_resultats.append([ip, f"/{cidr}" or masque or "-", "-", "❌"])
                        ajouter_test_historique("Vérification IP", ip_complet, "Masque invalide", False, user_id)
                    else:
                        classe = verifie_classfull(reseau)
                        if classe is ClasseIPV4.CLASSE_RESERVE:
                            historique_resultats.append([ip, f"/{cidr}" if cidr else masque, classe.value, "❌"])
                            ajouter_test_historique("Vérification IP", ip_complet, f"{classe.value}", False, user_id)
                        else:
                            historique_resultats.append([ip, f"/{cidr}" if cidr else masque, classe.value, "✅"])
                            ajouter_test_historique("Vérification IP", ip_complet, f"{classe.value}", True, user_id)
            except ValueError:
                afficher_popup("Erreur", "Adresse IP ou masque invalide.")
                ajouter_test_historique("Vérification IP", ip, "Adresse IP ou masque invalide", False, user_id)

        # Affichage de tout l'historique (dernier en haut)
        for i, ligne in enumerate(reversed(historique_resultats), start=1):
            bg_color = THEME_GREY_HOVER if i % 2 == 0 else THEME_GREY_BUTTON
            for j, val in enumerate(ligne):
                text_color = "green" if (j == 3 and val == "✅") else ("red" if j == 3 else THEME_TEXT_WHITE)

                ctk.CTkLabel(
                    tableau_frame,
                    text=str(val),
                    font=("Segoe UI", 14),
                    text_color=text_color,
                    fg_color=bg_color,
                    corner_radius=6
                ).grid(row=i, column=j, padx=5, pady=5, sticky="nsew")

    # --- Reste du code inchangé ---
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    app = ctk.CTk()
    app.title("🔍 Vérificateur d’adresse IP")
    app.geometry(f"{app.winfo_screenwidth()}x{app.winfo_screenheight()}+0+0")
    app.configure(fg_color=THEME_BACKGROUND)

    frame_inputs = ctk.CTkFrame(app, fg_color=THEME_GREY_BUTTON, corner_radius=15)
    frame_inputs.pack(pady=30, padx=30, fill="x")

    label_ip = ctk.CTkLabel(frame_inputs, text="Adresse IP :", text_color=THEME_TEXT_WHITE,
                             font=("Segoe UI", 16, "bold"))
    label_ip.grid(row=0, column=0, padx=20, pady=20, sticky="w")
    inputIp = ctk.CTkEntry(frame_inputs, placeholder_text="Ex: 192.168.1.1",
                             width=250, height=40, font=("Segoe UI", 14))
    inputIp.grid(row=0, column=1, padx=10)

    label_cidr = ctk.CTkLabel(frame_inputs, text="CIDR :", text_color=THEME_TEXT_WHITE,
                               font=("Segoe UI", 16, "bold"))
    label_cidr.grid(row=0, column=2, padx=20, pady=20, sticky="w")
    inputCIDR = ctk.CTkEntry(frame_inputs, placeholder_text="Ex: 24",
                               width=100, height=40, font=("Segoe UI", 14))
    inputCIDR.grid(row=0, column=3, padx=10)

    label_masque = ctk.CTkLabel(frame_inputs, text="Masque :", text_color=THEME_TEXT_WHITE,
                                 font=("Segoe UI", 16, "bold"))
    label_masque.grid(row=0, column=4, padx=20, pady=20, sticky="w")
    inputMasque = ctk.CTkEntry(frame_inputs, placeholder_text="Ex: 255.255.255.0",
                                 width=200, height=40, font=("Segoe UI", 14))
    inputMasque.grid(row=0, column=5, padx=10)

    tableau_frame = ctk.CTkScrollableFrame(app, corner_radius=12, fg_color=THEME_GREY_BUTTON)
    tableau_frame.pack(padx=30, pady=20, fill="both", expand=True)
    # Colonnes
    colonnes = ["IP", "Masque", "Classe", "Disponible"]

    # Configurer les colonnes pour qu'elles s'étendent
    for j in range(len(colonnes)):
        tableau_frame.grid_columnconfigure(j, weight=1)
        # Créer les entêtes
        for j, col in enumerate(colonnes):
            ctk.CTkLabel(
                tableau_frame,
                text=col,
                font=("Segoe UI", 16, "bold"),
                fg_color=THEME_BLUE,
                text_color="white",
                corner_radius=8
            ).grid(row=0, column=j, padx=5, pady=8, sticky="nsew")

    bouton = ctk.CTkButton(frame_inputs, text="✅ Vérifier", width=150, height=40,
                            fg_color=THEME_BLUE, hover_color=THEME_BLUE_HOVER,
                            text_color="white", font=("Segoe UI", 14, "bold"),
                            command=bouton_clique)
    bouton.grid(row=0, column=6, padx=20)

    btn_quitter = ctk.CTkButton(app, text="Fermer", width=120, height=40,
                                fg_color=THEME_GREY_BUTTON, hover_color=THEME_GREY_HOVER,
                                text_color="white", font=("Segoe UI", 14, "bold"),
                                command=app.destroy)
    btn_quitter.pack(pady=10)

    app.mainloop()