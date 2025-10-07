import customtkinter as ctk


def afficher_page_inscription(app, cadre_principal, afficher_page_connexion):

    for widget in cadre_principal.winfo_children():
        widget.destroy()


    label_bienvenue = ctk.CTkLabel(
        cadre_principal,
        text="Rejoignez-nous",
        font=("Segoe UI", 26, "bold"),
        text_color="#2D89EF"
    )
    label_bienvenue.pack(pady=(60, 10))

    label_titre = ctk.CTkLabel(
        cadre_principal,
        text="Créer un compte",
        font=("Segoe UI", 30, "bold"),
        text_color="white"
    )
    label_titre.pack(pady=(10, 30))


    champ_user = ctk.CTkEntry(
        cadre_principal,
        placeholder_text="Nom d’utilisateur",
        width=350,
        height=45,
        corner_radius=10
    )
    champ_user.pack(pady=10)

    champ_pass = ctk.CTkEntry(
        cadre_principal,
        placeholder_text="Mot de passe",
        show="*",
        width=350,
        height=45,
        corner_radius=10
    )
    champ_pass.pack(pady=10)

    champ_confirm = ctk.CTkEntry(
        cadre_principal,
        placeholder_text="Confirmer le mot de passe",
        show="*",
        width=350,
        height=45,
        corner_radius=10
    )
    champ_confirm.pack(pady=10)


    label_message = ctk.CTkLabel(
        cadre_principal,
        text="",
        text_color="red",
        font=("Segoe UI", 14)
    )
    label_message.pack(pady=(10, 10))

    bouton_creer = ctk.CTkButton(
        cadre_principal,
        text="S'inscrire",
        width=250,
        height=45,
        fg_color="#2D89EF",
        hover_color="#2563EB",
        text_color="white",
        corner_radius=12,
        command=lambda: verifier_inscription(
            champ_user.get(),
            champ_pass.get(),
            champ_confirm.get(),
            label_message,
            app,
            cadre_principal,
            afficher_page_connexion
        )
    )
    bouton_creer.pack(pady=25)


    bouton_retour = ctk.CTkButton(
        cadre_principal,
        text="Retour à la connexion",
        width=250,
        height=40,
        fg_color="#2c2c2e",
        text_color="white",
        hover_color="#3a3a3c",
        corner_radius=12,
        command=lambda: afficher_page_connexion(app, cadre_principal, afficher_page_inscription)
    )
    bouton_retour.pack(pady=10)



def verifier_inscription(utilisateur, mot_de_passe, confirmation, label_message, app, cadre_principal, afficher_page_connexion):

    if not utilisateur or not mot_de_passe or not confirmation:
        label_message.configure(text="Veuillez remplir tous les champs.", text_color="red")

    elif mot_de_passe != confirmation:
        label_message.configure(text="Les mots de passe ne correspondent pas.", text_color="red")

    else:
        label_message.configure(text="Compte créé avec succès ", text_color="green")
        label_message.after(1000, lambda: afficher_page_connexion(app, cadre_principal, afficher_page_inscription))
