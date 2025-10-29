import customtkinter as ctk
from interface_menu import afficher_menu
from database import verifier_identifiants


def afficher_page_connexion(app, cadre_principal, afficher_page_inscription):

    for widget in cadre_principal.winfo_children():
        widget.destroy()

    label_bienvenue = ctk.CTkLabel(
        cadre_principal,
        text="Bienvenue dans votre application réseau",
        font=("Segoe UI", 26, "bold"),
        text_color="#2D89EF"
    )
    label_bienvenue.pack(pady=(60, 10))

    label_titre = ctk.CTkLabel(
        cadre_principal,
        text="Connexion à l’application",
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


    label_message = ctk.CTkLabel(
        cadre_principal,
        text="",
        text_color="red"
    )
    label_message.pack(pady=(5, 0))


    bouton_connexion = ctk.CTkButton(
        cadre_principal,
        text="Se connecter",
        width=250,
        height=45,
        fg_color="#2D89EF",
        hover_color="#2563EB",
        text_color="white",
        corner_radius=12,

        command=lambda: verifier_connexion(
            champ_user.get(),
            champ_pass.get(),
            label_message,
            app,
            cadre_principal
        )
    )
    bouton_connexion.pack(pady=25)

    bouton_inscription = ctk.CTkButton(
        cadre_principal,
        text="Créer un compte",
        width=250,
        height=40,
        fg_color="#2c2c2e",
        text_color="white",
        hover_color="#3a3a3c",
        corner_radius=12,
        command=lambda: afficher_page_inscription(app, cadre_principal, afficher_page_connexion)
    )
    bouton_inscription.pack(pady=10)

    bouton_quitter = ctk.CTkButton(
        cadre_principal,
        text="Quitter",
        width=250,
        height=40,
        fg_color="#1c1c1e",
        text_color="white",
        hover_color="#3a3a3c",
        corner_radius=12,
        command=app.destroy
    )
    bouton_quitter.pack(pady=10)




def verifier_connexion(utilisateur, mot_de_passe, label_message, app, cadre_principal):
    if verifier_identifiants(utilisateur, mot_de_passe):
        label_message.configure(text="Connexion réussie ", text_color="green")
        from interface_menu import afficher_menu
        afficher_menu(app, cadre_principal)
    else:
        label_message.configure(text="Nom d’utilisateur ou mot de passe incorrect ", text_color="red")


# fct creant l'app
def creer_application():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    app = ctk.CTk()
    app.title("Mon appli réseau - Connexion")

    # --- DÉBUT DE LA MODIFICATION ---

    # Ajoutez cette ligne pour forcer l'initialisation de la fenêtre
    app.update_idletasks()

    # Ces lignes fonctionneront maintenant correctement
    largeur = app.winfo_screenwidth()
    hauteur = app.winfo_screenheight()
    app.geometry(f"{largeur}x{hauteur}+0+0")

    # --- FIN DE LA MODIFICATION ---

    return app


def creer_cadre_principal(app):

    cadre = ctk.CTkFrame(app, corner_radius=0, fg_color="#1c1c1e")
    cadre.pack(fill="both", expand=True)
    return cadre
