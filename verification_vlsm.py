import customtkinter as ctk
import ipaddress
from tkinter import messagebox
import session
from database import ajouter_test_historique


def calculer_bloc_ip(nb_ips_utilisables: int) -> int:
    """
    Calcule la taille du bloc (puissance de 2) nécessaire pour un nombre d'IP utilisables.
    Ex: 100 IP -> 100 + 2 (réseau/broadcast) = 102.
    La puissance de 2 suivante est 128 (bloc /25).
    """
    if nb_ips_utilisables <= 0:
        raise ValueError("Le nombre d'IP doit être strictement positif.")

    # +2 pour l'adresse réseau et l'adresse de broadcast
    total_requis = nb_ips_utilisables + 2

    # Le bloc minimum standard est un /30 (4 IPs) pour 2 hôtes
    if total_requis < 4:
        total_requis = 4

    # Calcule le nombre de bits hôte nécessaires (ceil(log2(total_requis)))
    h_bits = (total_requis - 1).bit_length()

    # La taille du bloc est 2^h_bits
    taille_bloc = 2 ** h_bits
    return taille_bloc


def verifier_possibilite_vlsm(reseau_de_base_str: str, masque_str: str | None, besoins_list: list[int]):
    """
    Vérifie si une liste de besoins (nb d'IP) peut tenir dans un réseau de base.
    besoins_list: une liste d'entiers [100, 50, 30]
    """
    # 1. Parser le réseau de base
    try:
        net_str = reseau_de_base_str.strip()
        masque_clean = masque_str.strip() if masque_str else None

        if "/" in net_str:
            # Cas 1: L'IP a un CIDR, mais le champ masque est AUSSI rempli
            if masque_clean:
                raise ValueError(
                    "Conflit de saisie : Fournissez le masque DANS le réseau de base (ex: 192.168.1.0/24) "
                    "OU dans le champ 'Masque', mais PAS les deux."
                )
            # Cas 2: L'IP a un CIDR, le champ masque est vide (OK)
            pass
        else:
            # Cas 3: L'IP n'a pas de CIDR, le champ masque est rempli (OK)
            if masque_clean:
                if masque_clean.startswith("/"):
                    net_str = f"{net_str}{masque_clean}"
                else:
                    net_str = f"{net_str}/{masque_clean}"
            # Cas 4: L'IP n'a pas de CIDR, le champ masque est vide (Erreur)
            else:
                raise ValueError("Masque manquant pour le réseau de base.")

        # 'net_str' est maintenant propre, on peut tenter de le parser
        net = ipaddress.ip_network(net_str, strict=False)
        total_ips_disponibles = net.num_addresses

    except Exception as e:
        # Intercepte nos 'ValueError' ou les erreurs de 'ip_network'
        raise ValueError(f"Réseau de base ou masque invalide : {e}")

    # 2. Parser la liste des besoins
    if not besoins_list:
        raise ValueError("La liste des besoins ne peut être vide.")

    total_ips_requises = 0

    # 3. Calculer le total requis
    for besoin in sorted(besoins_list, reverse=True):
        try:
            taille_bloc = calculer_bloc_ip(besoin)
            total_ips_requises += taille_bloc

        except ValueError as e:
            raise ValueError(f"Besoin invalide ({besoin}) : {e}")

    # 4. Comparer
    possible = total_ips_requises <= total_ips_disponibles

    message = (
        f"Réseau de base : {net.with_prefixlen}\n"
        f"Total IPs disponibles : {total_ips_disponibles}\n"
        f"Total IPs requises: {total_ips_requises}\n"
        f"--------------------------------------------------\n"
        f"Résultat : Découpe VLSM possible : {'OUI' if possible else 'NON'}\n"
        f"--------------------------------------------------"
    )

    return possible, message


def ouvrir_fenetre_verification_vlsm():
    THEME_BLUE = "#2D89EF"
    THEME_BLUE_HOVER = "#2563EB"
    THEME_GREY_BUTTON = "#2c2c2e"
    THEME_GREY_HOVER = "#3a3a3c"
    THEME_TEXT_WHITE = "white"
    THEME_BACKGROUND = "#1c1c1e"
    THEME_QUIT_BG = "#1c1c1e"

    app_vlsm = ctk.CTkToplevel()
    app_vlsm.title("🧪 Vérification de Faisabilité VLSM")

    # --- MISE EN PLEIN ÉCRAN (MAXIMISÉ) ---
    app_vlsm.state('zoomed')

    app_vlsm.configure(fg_color=THEME_BACKGROUND)

    # S'assure que la fenêtre reste au-dessus de l'application principale
    app_vlsm.transient()
    app_vlsm.grab_set()  # Rend la fenêtre modale

    # Frame principal qui utilise la couleur de fond
    frame = ctk.CTkFrame(app_vlsm, fg_color=THEME_BACKGROUND)
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    titre = ctk.CTkLabel(frame, text="Vérification Faisabilité VLSM",
                         font=("Segoe UI", 30, "bold"),
                         text_color=THEME_BLUE)  # Couleur du titre
    titre.pack(pady=40)

    # --- Formulaire d'entrées ---
    input_frame = ctk.CTkFrame(frame, fg_color="transparent")
    input_frame.pack(pady=10, fill="x", padx=30)

    # Centre la frame d'inputs
    input_frame.grid_columnconfigure(0, weight=1)
    input_frame.grid_columnconfigure(1, weight=1)

    ctk.CTkLabel(input_frame, text="Réseau de base :", font=("Segoe UI", 16), text_color=THEME_TEXT_WHITE).grid(row=0,
                                                                                                                column=0,
                                                                                                                sticky="e",
                                                                                                                padx=10,
                                                                                                                pady=15)
    entry_reseau = ctk.CTkEntry(input_frame, placeholder_text="192.168.1.0/24 ou 192.168.1.0", width=350, height=45,
                                corner_radius=10)
    entry_reseau.grid(row=0, column=1, padx=10, pady=15, sticky="w")

    ctk.CTkLabel(input_frame, text="Masque (si pas CIDR) :", font=("Segoe UI", 16), text_color=THEME_TEXT_WHITE).grid(
        row=1, column=0, sticky="e", padx=10, pady=15)
    entry_masque = ctk.CTkEntry(input_frame, placeholder_text="/24 ou 255.255.255.0", width=350, height=45,
                                corner_radius=10)
    entry_masque.grid(row=1, column=1, padx=10, pady=15, sticky="w")

    ctk.CTkLabel(input_frame, text="Besoins (IPs utilisables) :", font=("Segoe UI", 16),
                 text_color=THEME_TEXT_WHITE).grid(row=2, column=0, sticky="e", padx=10, pady=15)
    entry_besoins = ctk.CTkEntry(input_frame, placeholder_text="Ex: 10", width=350, height=45,
                                 corner_radius=10)
    entry_besoins.grid(row=2, column=1, padx=10, pady=15, sticky="w")

    # --- Zone de Résultat ---
    result_textbox = ctk.CTkTextbox(frame, height=200, font=("Courier New", 14),
                                    state="disabled", wrap="word", corner_radius=10,
                                    fg_color=THEME_GREY_BUTTON)  # Fond gris
    result_textbox.pack(pady=20, fill="x", expand=True, padx=100)

    # --- Cadre pour les boutons ---
    button_frame = ctk.CTkFrame(frame, fg_color="transparent")
    button_frame.pack(pady=20)

    # --- Fonction de rappel du bouton ---
    def on_verifier_click():
        reseau = entry_reseau.get().strip()
        masque = entry_masque.get().strip()
        besoins_str = entry_besoins.get().strip()

        # Préparation des données pour le log
        id_user = session.utilisateur_connecte_id
        entree_log = f"R: {reseau}, M: {masque}, B: {besoins_str}"

        if not reseau or not besoins_str:
            msg = "Veuillez remplir le réseau de base et les besoins."
            messagebox.showerror("Erreur", msg, parent=app_vlsm)

            return

        try:
            besoins_list = [int(b.strip()) for b in besoins_str.split(',') if b.strip()]
            if not besoins_list:
                raise ValueError("Liste de besoins vide.")
        except ValueError as e:
            msg = "Format des besoins invalide. Utilisez des nombres séparés (ex: 100, 50, 30)."
            messagebox.showerror("Erreur", msg, parent=app_vlsm)
            return

        try:
            possible, message = verifier_possibilite_vlsm(reseau, masque, besoins_list)

            result_textbox.configure(state="normal")
            result_textbox.delete("1.0", "end")
            result_textbox.insert("1.0", message)

            if possible:
                result_textbox.configure(text_color="#4CAF50")  # Vert
            else:
                result_textbox.configure(text_color="#F44336")  # Rouge

            result_textbox.configure(state="disabled")

            ajouter_test_historique(
                type_test="Vérification VLSM",
                entree=entree_log,
                resultat=f"Possible: {'OUI' if possible else 'NON'}",
                est_valide=possible,
                id_utilisateur=id_user
            )

        except Exception as e:
            messagebox.showerror("Erreur de calcul", str(e), parent=app_vlsm)

    # --- Boutons ---
    btn_verifier = ctk.CTkButton(button_frame, text="Vérifier la Faisabilité",
                                 command=on_verifier_click,
                                 # Style du bouton "Se connecter"
                                 fg_color=THEME_BLUE,
                                 hover_color=THEME_BLUE_HOVER,
                                 text_color=THEME_TEXT_WHITE,
                                 width=250,
                                 height=45,
                                 font=("Segoe UI", 16, "bold"),
                                 corner_radius=12)
    btn_verifier.pack(side="left", padx=10)

    btn_quitter = ctk.CTkButton(button_frame, text="Fermer",
                                command=app_vlsm.destroy,
                                # Style du bouton "Quitter"
                                fg_color=THEME_QUIT_BG,
                                hover_color=THEME_GREY_HOVER,
                                text_color=THEME_TEXT_WHITE,
                                width=250,
                                height=45,
                                font=("Segoe UI", 16, "bold"),
                                corner_radius=12)
    btn_quitter.pack(side="left", padx=10)