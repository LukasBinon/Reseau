import customtkinter as ctk
from tkinter import messagebox
import session
from database import ajouter_test_historique
from verification_vlsm import verifier_possibilite_vlsm


def ouvrir_fenetre_verification_vlsm():
    bleu = "#2D89EF"
    bleuHover = "#2563EB"
    gris = "#2c2c2e"
    white = "white"
    bg = "#1c1c1e"
    quitbg = "#1c1c1e"

    app_vlsm = ctk.CTkToplevel()
    app_vlsm.title(" Vérification de Faisabilité VLSM")

    app_vlsm.state('zoomed')
    app_vlsm.configure(fg_color=bg)

    #assure que la fenêtre reste au-dessus
    app_vlsm.transient()
    app_vlsm.grab_set()

    # frame principal qui utilise la couleur de fond
    frame = ctk.CTkFrame(app_vlsm, fg_color=bg)
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    titre = ctk.CTkLabel(frame, text="Vérification VLSM",
                         font=("Segoe UI", 30, "bold"),
                         text_color=bleu)
    titre.pack(pady=40)

    # form d'entrées
    input_frame = ctk.CTkFrame(frame, fg_color="transparent")
    input_frame.pack(pady=10, fill="x", padx=30)

    # centre les inputs
    input_frame.grid_columnconfigure(0, weight=1)
    input_frame.grid_columnconfigure(1, weight=1)

    ctk.CTkLabel(input_frame, text="Réseau de base :", font=("Segoe UI", 16), text_color=white).grid(row=0,
                                                                                                    column=0,
                                                                                                    padx=10,
                                                                                                    pady=15,
                                                                                                    sticky="e")
    entry_reseau = ctk.CTkEntry(input_frame, placeholder_text="192.168.1.0/24 ou 192.168.1.0",
                                width=350,
                                height=45,
                                corner_radius=10)
    entry_reseau.grid(row=0,
                      column=1,
                      padx=10,
                      pady=15,
                      sticky="w")

    ctk.CTkLabel(input_frame, text="Masque (si pas CIDR) :", font=("Segoe UI", 16), text_color=white).grid(
        row=1,
        column=0,
        sticky="e",
        padx=10,
        pady=15)
    entry_masque = ctk.CTkEntry(input_frame, placeholder_text="/24 ou 255.255.255.0",
                                width=350,
                                height=45,
                                corner_radius=10)
    entry_masque.grid(row=1,
                      column=1,
                      padx=10,
                      pady=15,
                      sticky="w")

    ctk.CTkLabel(input_frame, text="Besoins (IPs utilisables) :", font=("Segoe UI", 16),
                 text_color=white).grid(row=2, column=0, sticky="e", padx=10, pady=15)
    entry_besoins = ctk.CTkEntry(input_frame, placeholder_text="Ex: 100, 50, 20",
                                 width=350
                                 ,height=45,
                                 corner_radius=10)

    entry_besoins.grid(row=2, column=1, padx=10, pady=15, sticky="w")

    # zone resultat
    result_textbox = ctk.CTkTextbox(frame, height=200, font=("Courier New", 14),
                                    state="disabled", wrap="word", corner_radius=10,
                                    fg_color=gris)
    result_textbox.pack(pady=20, fill="x", expand=True, padx=100)

    #cadre pour les boutons
    button_frame = ctk.CTkFrame(frame, fg_color="transparent")
    button_frame.pack(pady=20)

    # fct de rappel du bouton
    def on_verifier_click():
        reseau = entry_reseau.get().strip()
        masque = entry_masque.get().strip()
        besoins_str = entry_besoins.get().strip()

        # prep donne pour log
        id_user = session.utilisateur_connecte_id
        entree_log = f"R: {reseau}, M: {masque}, B: {besoins_str}"

        if not reseau or not besoins_str:
            msg = "Veuillez remplir le réseau de base et les besoins."
            messagebox.showerror("Erreur", msg, parent=app_vlsm)
            return

        try:
            besoins_list = []

            #coupe la chaîne aux virgules
            morceaux = besoins_str.split(',')
            for b in morceaux:
                # enleve les espace
                morceau_propre = b.strip()

                if morceau_propre:
                    # convertit en nombre et on l'ajoute à la liste
                    nombre = int(morceau_propre)
                    besoins_list.append(nombre)

            # À la fin, besoins_list contient [100, 50, 20]
            if not besoins_list:
                raise ValueError("Liste de besoins vide.")
        except ValueError as e:
            msg = "Format des besoins invalide. Utilisez des nombres séparés par des virgules (ex: 100, 50, 20)."
            messagebox.showerror("Erreur", msg, parent=app_vlsm)
            return

        try:
            # appel de la fonction logique importée
            possible, message = verifier_possibilite_vlsm(reseau, masque, besoins_list)

            result_textbox.configure(state="normal") #rend zone texte modifiable
            result_textbox.delete("1.0", "end") #Efface le résultat précédent.
            result_textbox.insert("1.0", message) #ecrit un nv msg

            if possible:
                result_textbox.configure(text_color="#4CAF50")
            else:
                result_textbox.configure(text_color="#F44336")

            result_textbox.configure(state="disabled")

            # enregistre dans la base de données
            ajouter_test_historique(
                type_test="Vérification VLSM",
                entree=entree_log,
                resultat=f"Possible: {'OUI' if possible else 'NON'}",
                est_valide=possible,
                id_utilisateur=id_user
            )

        except Exception as e:
            messagebox.showerror("Erreur de calcul", str(e), parent=app_vlsm)

    # bouton
    btn_verifier = ctk.CTkButton(button_frame, text="Vérifier",
                                 command=on_verifier_click,
                                 fg_color=bleu,
                                 hover_color=bleuHover,
                                 text_color=white,
                                 width=250,
                                 height=45,
                                 font=("Segoe UI", 16, "bold"),
                                 corner_radius=12)
    btn_verifier.pack(side="left", padx=10)

    btn_quitter = ctk.CTkButton(button_frame, text="Fermer",
                                command=app_vlsm.destroy,
                                fg_color=quitbg,
                                hover_color=gris,
                                text_color=white,
                                width=250,
                                height=45,
                                font=("Segoe UI", 16, "bold"),
                                corner_radius=12)
    btn_quitter.pack(side="left", padx=10)