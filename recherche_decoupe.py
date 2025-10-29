import sqlite3
import customtkinter as ctk
from tkinter import messagebox
import session

DB_NAME = "reseau.db"

# === Couleurs et style du thème ===
THEME_BLUE = "#2D89EF"
THEME_BLUE_HOVER = "#2563EB"
THEME_GREY_BUTTON = "#2c2c2e"
THEME_GREY_HOVER = "#3a3a3c"
THEME_TEXT_WHITE = "white"
THEME_BACKGROUND = "#1c1c1e"

def get_connection():
    return sqlite3.connect(DB_NAME)

def rechercher_decoupe(nom_decoupe):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id_decoupe, id_responsable FROM decoupe WHERE nom_decoupe = ?", (nom_decoupe,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None, []

    id_decoupe, id_responsable = row
    if id_responsable != session.utilisateur_connecte_id:
        conn.close()
        messagebox.showerror("Erreur", "Vous n'avez pas les droits pour consulter cette découpe.")
        return None, []

    cur.execute("""
        SELECT ip_reseau, masque, ip_debut, ip_fin, ip_broadcast, nb_ips
        FROM sous_reseau
        WHERE id_decoupe = ?
    """, (id_decoupe,))
    sous_reseaux = cur.fetchall()
    conn.close()
    return id_decoupe, sous_reseaux


def ouvrir_fenetre_recherche_decoupe():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    app = ctk.CTk()
    app.title("🔍 Recherche de Découpe Réseau")
    app.geometry("900x600")
    app.configure(fg_color=THEME_BACKGROUND)

    # --- Zone de recherche ---
    frame = ctk.CTkFrame(app, fg_color=THEME_GREY_BUTTON, corner_radius=15)
    frame.pack(pady=30, padx=30, fill="x")

    label_nom = ctk.CTkLabel(frame, text="Nom de la découpe :",
                             text_color=THEME_TEXT_WHITE, font=("Segoe UI", 16, "bold"))
    label_nom.grid(row=0, column=0, padx=20, pady=20, sticky="w")

    entry_nom = ctk.CTkEntry(frame, placeholder_text="Ex: Réseau Bureau",
                             width=300, height=40, font=("Segoe UI", 14))
    entry_nom.grid(row=0, column=1, padx=10)

    def afficher_decoupe():
        nom = entry_nom.get().strip()
        if not nom:
            messagebox.showerror("Erreur", "Veuillez entrer un nom de découpe.")
            return

        _, sous_reseaux = rechercher_decoupe(nom)
        for widget in tableau_frame.winfo_children():
            widget.destroy()

        if not sous_reseaux:
            messagebox.showinfo("Résultat", "Aucune découpe trouvée avec ce nom.")
            return

        colonnes = ["IP Réseau", "Masque", "IP Début", "IP Fin", "Broadcast", "Nb IPs"]

        # Entêtes
        for j, col in enumerate(colonnes):
            ctk.CTkLabel(tableau_frame, text=col, font=("Segoe UI", 16, "bold"),
                         fg_color=THEME_BLUE, text_color="white", corner_radius=8).grid(
                row=0, column=j, padx=5, pady=8, sticky="nsew"
            )

        # Données
        for i, sr in enumerate(sous_reseaux, start=1):
            bg_color = THEME_GREY_HOVER if i % 2 == 0 else THEME_GREY_BUTTON
            for j, val in enumerate(sr):
                ctk.CTkLabel(tableau_frame, text=str(val),
                             font=("Segoe UI", 14), text_color=THEME_TEXT_WHITE,
                             fg_color=bg_color, corner_radius=6).grid(
                    row=i, column=j, padx=5, pady=5, sticky="nsew"
                )

    btn_rechercher = ctk.CTkButton(frame, text="Rechercher", width=150, height=40,
                                   fg_color=THEME_BLUE, hover_color=THEME_BLUE_HOVER,
                                   text_color="white", font=("Segoe UI", 14, "bold"),
                                   command=afficher_decoupe)
    btn_rechercher.grid(row=0, column=2, padx=20)

    # --- Tableau des résultats ---
    tableau_frame = ctk.CTkScrollableFrame(app, corner_radius=12, fg_color=THEME_GREY_BUTTON)
    tableau_frame.pack(padx=30, pady=20, fill="both", expand=True)

    # --- Bouton de fermeture ---
    btn_quitter = ctk.CTkButton(app, text="Fermer", width=120, height=40,
                                fg_color=THEME_GREY_BUTTON, hover_color=THEME_GREY_HOVER,
                                text_color="white", font=("Segoe UI", 14, "bold"),
                                command=app.destroy)
    btn_quitter.pack(pady=10)

    app.mainloop()
