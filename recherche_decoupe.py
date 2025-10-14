import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

DB_NAME = "reseau.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def rechercher_decoupe(nom_decoupe):
    conn = get_connection()
    cur = conn.cursor()

    # Vérifie si la découpe existe
    cur.execute("SELECT id_decoupe FROM decoupe WHERE nom_decoupe = ?", (nom_decoupe,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None, []

    id_decoupe = row[0]

    # Récupère les sous-réseaux associés
    cur.execute("""
        SELECT ip_reseau, masque, ip_debut, ip_fin, ip_broadcast, nb_ips
        FROM sous_reseau
        WHERE id_decoupe = ?
    """, (id_decoupe,))
    sous_reseaux = cur.fetchall()
    conn.close()
    return id_decoupe, sous_reseaux

def afficher_decoupe():
    nom = entry_nom.get().strip()
    if not nom:
        messagebox.showerror("Erreur", "Veuillez entrer un nom de découpe.")
        return

    _, sous_reseaux = rechercher_decoupe(nom)

    for widget in tableau.get_children():
        tableau.delete(widget)

    if not sous_reseaux:
        messagebox.showinfo("Résultat", "Aucune découpe trouvée avec ce nom.")
        return

    for sr in sous_reseaux:
        tableau.insert("", "end", values=sr)

# Interface Tkinter
root = tk.Tk()
root.title("🔍 Recherche de Découpe Réseau")
root.geometry("900x500")

frame = tk.Frame(root)
frame.pack(pady=20)

tk.Label(frame, text="Nom de la découpe :", font=("Arial", 14)).grid(row=0, column=0, padx=10)
entry_nom = tk.Entry(frame, font=("Arial", 14), width=30)
entry_nom.grid(row=0, column=1, padx=10)
btn_rechercher = tk.Button(frame, text="Rechercher", font=("Arial", 14), command=afficher_decoupe)
btn_rechercher.grid(row=0, column=2, padx=10)

colonnes = ["IP Réseau", "Masque", "IP Début", "IP Fin", "Broadcast", "Nb IPs"]
tableau = ttk.Treeview(root, columns=colonnes, show="headings", height=15)
for col in colonnes:
    tableau.heading(col, text=col)
    tableau.column(col, width=140, anchor="center")
tableau.pack(pady=20)

root.mainloop()