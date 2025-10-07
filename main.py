from interface_connexion import creer_application, creer_cadre_principal, afficher_page_connexion
from interface_inscription import afficher_page_inscription


def main():

    app = creer_application()
    cadre_principal = creer_cadre_principal(app)

    # fct pour éviter les imports circulaires
    def ouvrir_page_inscription(app, cadre, afficher_page_connexions):
        afficher_page_inscription(app, cadre, afficher_page_connexions)

    afficher_page_connexion(app, cadre_principal, ouvrir_page_inscription)
    app.mainloop()


if __name__ == "__main__":
    main()
