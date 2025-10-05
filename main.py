import Test
import customtkinter as ctk
from Test import calculer_sous_reseaux


# Configuration du thème
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Création de l'application
app = ctk.CTk()
Test.configurer_fenetre(app)

# Création de l'interface
main_frame = Test.creer_frame_principale(app)
Test.creer_titre(main_frame)
entry_reseau, entry_nb = Test.creer_zone_saisie(main_frame)
table_container = Test.creer_tableau(main_frame)

# Bouton calculer (doit être créé après la zone de saisie)
Test.creer_bouton_calculer(main_frame, entry_reseau, entry_nb, table_container)

# Affichage initial
Test.afficher_resultats(entry_reseau, entry_nb, table_container)

# Bouton quitter
Test.creer_bouton_quitter(main_frame, app)

# Lancement
app.mainloop()
#Jiahao