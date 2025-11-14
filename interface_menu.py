import customtkinter as ctk
import Test
import recherche_decoupe
import interface_verification_vlsm
import interface_verifier_classe


def afficher_menu(app, cadre_principal):

    for widget in cadre_principal.winfo_children():
        widget.destroy()

    label_titre = ctk.CTkLabel(
        cadre_principal,
        text=" Menu Principal",
        font=("Segoe UI", 34, "bold"),
        text_color="#2D89EF"
    )
    label_titre.pack(pady=(60, 20))


    label_sousTitre = ctk.CTkLabel(
        cadre_principal,
        text="Votre application réseau\n Choisissez une fonctionnalité pour commencer ",
        font=("Segoe UI", 18),
        text_color="white"
    )
    label_sousTitre.pack(pady=(0, 40))


    boutons = [
        ("1 Calcul adresse réseau / broadcast", lambda: print("Ouverture fonction 1")),
        ("2 Vérifier appartenance IP", lambda: print("Ouverture fonction 2")),
        ("3 Vérifier découpe classique possible", lambda: print("Ouverture fonction 3")),
        ("4 Réaliser découpe classique (plan d’adressage)", lambda: Test.ouvrir_fenetre_decoupe() ),
        # La ligne suivante est corrigée :
        ("5 Vérifier découpe VLSM possible", lambda: interface_verification_vlsm.ouvrir_fenetre_verification_vlsm()),
        ("6 Vérifier la classe", lambda: interface_verifier_classe.ouvrir_fenetre()),
        ("7 Rechercher une découpe", lambda: recherche_decoupe.ouvrir_fenetre_recherche_decoupe() ),
    ]

    for texte, commande in boutons:
        bouton = ctk.CTkButton(
            cadre_principal,
            text=texte,
            width=420,
            height=50,
            fg_color="#2D89EF",
            hover_color="#2563EB",
            text_color="white",
            font=("Segoe UI", 15, "bold"),
            corner_radius=12,
            command=commande
        )
        bouton.pack(pady=10)

    bouton_quitter = ctk.CTkButton(
        cadre_principal,
        text="Quitter le programme",
        width=300,
        height=40,
        fg_color="#2A2A2A",
        hover_color="#3A3A3A",
        text_color="#E5E5E5",
        corner_radius=10,
        command=app.destroy
    )
    bouton_quitter.pack(pady=(30, 10))


def retour_connexion(app, cadre_principal):

    from interface_connexion import afficher_page_connexion
    from interface_inscription import afficher_page_inscription

    def ouvrir_page_inscription(app_ref, cadre, afficher_page_connexions):
        afficher_page_inscription(app_ref, cadre, afficher_page_connexions)

    afficher_page_connexion(app, cadre_principal, ouvrir_page_inscription)