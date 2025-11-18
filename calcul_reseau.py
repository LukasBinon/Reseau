import customtkinter as ctk
from tkinter import messagebox
import tkinter as tk  # Pour tk.END, qui est une constante Tcl
import session  # Importé pour gérer l'ID utilisateur, comme dans l'exemple
import ipaddress
from database import (
    init_db,
    #ensure_decoupe,
    add_subnet_result,
    #get_decoupe_by_name_for_owner,
    list_subnet_results,
    log_calc_history,
)
from interface_verif_decoupe_classique import THEME_GREY_HOVER
from netcalc import compute_network_info, check_ip_membership, NetcalcError

# --- Thèmes personnalisés (basés sur interface_verif_decoupe_classique.py) ---
THEME_BACKGROUND = "#1e1e1e"
THEME_FRAME_BG = "#1c1c1e"
THEME_GREY_WIDGET = "#2c2c2e"
THEME_BLUE = "#2D89EF"
THEME_BLUE_HOVER = "#2563EB"
THEME_TEXT_WHITE = "#ffffff"


def _creer_selecteur_mode(parent):
    """Crée les radio-boutons Classless/Classful et retourne le StringVar."""
    mv = ctk.StringVar(value="classless")
    frame = ctk.CTkFrame(parent, fg_color="transparent")

    ctk.CTkRadioButton(
        frame, text="Classless", variable=mv, value="classless",
        text_color=THEME_TEXT_WHITE, font=("Segoe UI", 14)
    ).pack(anchor="w", padx=5, pady=5)

    ctk.CTkRadioButton(
        frame, text="Classful (A/B/C)", variable=mv, value="classful",
        text_color=THEME_TEXT_WHITE, font=("Segoe UI", 14)
    ).pack(anchor="w", padx=5, pady=5)

    return frame, mv


def build_tab1(tab):
    """Construit l'interface de l'onglet 1: Calcul réseau"""

    frame = ctk.CTkFrame(tab, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    # --- MODIFICATION ERGONOMIE ---
    # Configurer les colonnes pour centrer le formulaire
    frame.grid_columnconfigure(0, weight=0)  # Labels
    frame.grid_columnconfigure(1, weight=1)  # Entries
    # --- Fin Modif ---

    # --- Widgets d'entrée ---
    ctk.CTkLabel(frame, text="Adresse IP :", font=("Segoe UI", 16)).grid(row=0, column=0, sticky="e", padx=10, pady=10)
    ip1 = ctk.CTkEntry(frame, placeholder_text="192.168.1.1", width=300, height=35, corner_radius=8)
    ip1.grid(row=0, column=1, pady=10, sticky="w") # sticky 'w' pour aligner

    ctk.CTkLabel(frame, text="Masque (/n ou 255...) :", font=("Segoe UI", 16)).grid(row=1, column=0, sticky="e",
                                                                                    padx=10, pady=10)
    mask1 = ctk.CTkEntry(frame, placeholder_text="/24 ou 255.255.255.0", width=300, height=35, corner_radius=8)
    mask1.grid(row=1, column=1, pady=10, sticky="w")

    ctk.CTkLabel(frame, text="Nom pour le calcul :", font=("Segoe UI", 16)).grid(row=2, column=0, sticky="e", padx=10,
                                                                                  pady=10)
    decoupe_name1 = ctk.CTkEntry(frame, placeholder_text="Optionnel: 'Bureaux_Etage_1'", width=300, height=35,
                                 corner_radius=8)
    decoupe_name1.grid(row=2, column=1, pady=10, sticky="w")

    # --- Sélecteur de mode ---
    mode_frame, mode1_var = _creer_selecteur_mode(frame)
    # --- MODIFICATION ERGONOMIE ---
    mode_frame.grid(row=3, column=0, columnspan=2, sticky="w", padx=20, pady=10)


    # --- Boîte de résultat ---
    res1 = ctk.CTkTextbox(
        frame, font=("Segoe UI", 14), wrap="word", corner_radius=8,
        fg_color=THEME_GREY_WIDGET, state="disabled", height=250
    )
    # --- MODIFICATION ERGONOMIE ---
    res1.grid(row=5, column=0, columnspan=2, sticky="ew", pady=15, padx=5)

    # --- Fonction de rappel (imbriquée) ---
    def _do_calc1():
        ip = ip1.get().strip()
        mask = mask1.get().strip() or None
        mode = mode1_var.get()
        user_id = session.utilisateur_connecte_id

        res1.configure(state="normal")
        res1.delete("1.0", tk.END)

        try:
            info = compute_network_info(ip, mask, mode)

            # 1. Créer la partie haute (commune)
            header_text = f"""--- Résultat du Calcul ({info['mode']}) ---
    Entrée: {info['ip_input']}

    Adresse réseau:   {info['network']}
    Masque (décimal): {info['mask_display']}"""

            # 2. Créer la ligne CIDR (conditionnelle)
            cidr_text = ""
            if info['mode'] == 'classless':
                cidr_text = f"\n    Préfixe CIDR:     /{info['prefixlen']}"

            # 3. Créer la partie basse (commune)
            footer_text = f"""

    Première IP Hôte: {info['first_host']}
    Dernière IP Hôte: {info['last_host']}
    Broadcast:        {info['broadcast']}

    Nombre d'hôtes:   {info['hosts_count']}
    """

            # 4. Combiner le tout
            final_text = header_text + cidr_text + footer_text

            res1.insert(tk.END, final_text)

            name = decoupe_name1.get().strip()

            if name and user_id:
                add_subnet_result(
                    decoupe_name=name,
                    owner_id=user_id,
                    mode=mode,
                    result=info,
                    base_ip=ip,
                    mask=info['mask_display']
                )

            if user_id:
                log_calc_history(user_id, 'compute', {'input_ip': ip, 'input_mask': mask, 'mode': mode, 'result': info})

        except Exception as e:
            if user_id:
                log_calc_history(user_id, 'error', {'input_ip': ip, 'input_mask': mask, 'mode': mode, 'error': str(e)})
            messagebox.showerror("Erreur", str(e))

        res1.configure(state="disabled")

    # --- Bouton ---
    # --- MODIFICATION ERGONOMIE ---
    # Déplacé à la ligne 4
    ctk.CTkButton(
        frame, text="Calculer", command=_do_calc1,
        fg_color=THEME_BLUE, hover_color=THEME_BLUE_HOVER,
        height=40, font=("Segoe UI", 16, "bold")
    ).grid(row=4, column=0, columnspan=2, pady=20)
    # --- Fin Modif ---


def build_tab2(tab):
    """Construit l'interface de l'onglet 2: Appartenance & Bornes"""

    frame = ctk.CTkFrame(tab, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    # --- Configuration ergonomique ---
    frame.grid_columnconfigure(0, weight=0)  # Labels
    frame.grid_columnconfigure(1, weight=1)  # Entries

    # --- Widgets d'entrée ---
    ctk.CTkLabel(frame, text="IP à vérifier :", font=("Segoe UI", 16)).grid(row=0, column=0, sticky="e", padx=10,
                                                                            pady=10)
    ip2 = ctk.CTkEntry(frame, placeholder_text="192.168.1.50", width=300, height=35, corner_radius=8)
    ip2.grid(row=0, column=1, pady=10, sticky="w")

    ctk.CTkLabel(frame, text="IP réseau :", font=("Segoe UI", 16)).grid(row=1, column=0, sticky="e", padx=10, pady=10)
    net2 = ctk.CTkEntry(frame, placeholder_text="192.168.1.0", width=300, height=35, corner_radius=8)
    net2.grid(row=1, column=1, pady=10, sticky="w")

    ctk.CTkLabel(frame, text="Masque réseau :", font=("Segoe UI", 16)).grid(row=2, column=0, sticky="e", padx=10,
                                                                            pady=10)
    mask2 = ctk.CTkEntry(frame, placeholder_text="/24 ou 255.255.255.0", width=300, height=35, corner_radius=8)
    mask2.grid(row=2, column=1, pady=10, sticky="w")

    # --- Sélecteur de mode ---
    mode_frame, mode2_var = _creer_selecteur_mode(frame)
    mode_frame.grid(row=3, column=0, columnspan=2, sticky="w", padx=20, pady=10)

    # --- Boîte de résultat ---
    res2 = ctk.CTkTextbox(
        frame, font=("Segoe UI", 14), wrap="word", corner_radius=8,
        fg_color=THEME_GREY_WIDGET, state="disabled", height=250
    )
    res2.grid(row=5, column=0, columnspan=2, sticky="ew", pady=15, padx=5)

    # --- MODIFICATION: Logique de liaison ---
    def _update_mask_for_mode(*args):
        """Met à jour le champ masque en fonction du mode et de l'IP."""
        mode = mode2_var.get()
        ip_text = net2.get().strip()  # On se base sur l'IP réseau

        if mode == 'classful':
            masque = ""
            try:
                # Tente de déterminer la classe A, B, C
                ip_obj = ipaddress.IPv4Address(ip_text.split("/")[0])
                first = ip_obj.packed[0]  # Récupère le premier octet

                if 1 <= first <= 126:
                    masque = "255.0.0.0"  # Classe A
                elif 128 <= first <= 191:
                    masque = "255.255.0.0"  # Classe B
                elif 192 <= first <= 223:
                    masque = "255.255.255.0"  # Classe C
                # Si classe D/E, 'masque' reste "", netcalc lèvera une erreur au calcul

            except (ipaddress.AddressValueError, ValueError):
                # Si l'IP n'est pas valide, on ne met rien
                masque = ""

            finally:
                mask2.configure(state="normal")
                mask2.delete(0, tk.END)
                mask2.insert(0, masque)
                mask2.configure(state="disabled")  # Griser la case

        else:  # Mode classless
            mask2.configure(state="normal")  # Activer la case

    # Lier les événements de l'IP réseau et des boutons radio
    net2.bind("<KeyRelease>", _update_mask_for_mode)
    net2.bind("<FocusOut>", _update_mask_for_mode)

    # Lier les radio boutons (qui sont dans mode_frame)
    for child in mode_frame.winfo_children():
        if isinstance(child, ctk.CTkRadioButton):
            child.configure(command=_update_mask_for_mode)

    # Appel initial pour régler l'état au démarrage
    _update_mask_for_mode()

    # --- Fonction de rappel (imbriquée) ---
    def _do_calc2():
        ip = ip2.get().strip()
        net_ip = net2.get().strip()

        # --- MODIFICATION ---
        # Doit lire le masque même s'il est désactivé
        mask = mask2.get().strip() or None
        # --- FIN MODIFICATION ---

        mode = mode2_var.get()
        user_id = session.utilisateur_connecte_id

        res2.configure(state="normal")
        res2.delete("1.0", tk.END)

        try:
            res = check_ip_membership(ip, net_ip, mask, mode)

            # (Le reste de votre logique d'affichage propre)
            header_text = f"--- Résultat de l'Appartenance ---\n\nAppartenance: {res['in_network']}\n"
            details_header = f"""\n--- Détails du Réseau de Référence ({res['mode']}) ---
    Entrée (Réseau): {res['ip_input']}
    Masque (décimal): {res['mask_display']}"""
            cidr_text = ""
            if res['mode'] == 'classless':
                cidr_text = f"\n    Préfixe CIDR:     /{res['prefixlen']}"
            footer_text = f"""\n
    Première IP Hôte: {res['first_host']}
    Dernière IP Hôte: {res['last_host']}
    Broadcast:        {res['broadcast']}
    Nombre d'hôtes:   {res['hosts_count']}
"""
            final_text = header_text + details_header + cidr_text + footer_text
            res2.insert(tk.END, final_text)

            if user_id:
                log_calc_history(user_id, 'membership',
                                 {'input_ip': ip, 'input_mask': mask, 'mode': mode, 'result': res})

        except Exception as e:
            if user_id:
                log_calc_history(user_id, 'error', {'input_ip': ip, 'input_mask': mask, 'mode': mode, 'error': str(e)})
            messagebox.showerror("Erreur", str(e))

        res2.configure(state="disabled")

    # --- Bouton ---
    ctk.CTkButton(
        frame, text="Vérifier", command=_do_calc2,
        fg_color=THEME_BLUE, hover_color=THEME_BLUE_HOVER,
        height=40, font=("Segoe UI", 16, "bold")
    ).grid(row=4, column=0, columnspan=2, pady=20)


def build_tab3(tab):
    """Construit l'interface de l'onglet 3: Découpes (DB)"""

    frame = ctk.CTkFrame(tab, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    # --- MODIFICATION ERGONOMIE ---
    # Utilisation de .grid() pour centrer les éléments

    # Configure les lignes : 0 pour la recherche (fixe), 1 pour les résultats (extensible)
    frame.grid_rowconfigure(0, weight=0)
    frame.grid_rowconfigure(1, weight=1)
    frame.grid_columnconfigure(0, weight=1)  # Une seule colonne extensible

    # --- Cadre de recherche ---
    search_frame = ctk.CTkFrame(frame, fg_color="transparent")
    search_frame.grid(row=0, column=0, sticky="ew", pady=10)  # Prend toute la largeur

    # Centrer les éléments dans la barre de recherche
    search_frame.grid_columnconfigure(0, weight=1)  # Espace gauche
    search_frame.grid_columnconfigure(1, weight=0)  # Label
    search_frame.grid_columnconfigure(2, weight=0)  # Entry
    search_frame.grid_columnconfigure(3, weight=0)  # Button
    search_frame.grid_columnconfigure(4, weight=1)  # Espace droit

    ctk.CTkLabel(search_frame, text="Nom de la découpe :", font=("Segoe UI", 16)).grid(row=0, column=1, sticky="e",
                                                                                       padx=(0, 10))

    decoupe_query = ctk.CTkEntry(search_frame, placeholder_text="Bureaux_Etage_1", width=350, height=35,
                                 corner_radius=8)
    decoupe_query.grid(row=0, column=2, sticky="w")

    # --- Boîte de résultat ---
    decoupe_info = ctk.CTkTextbox(
        frame, font=("Segoe UI", 14), wrap="word", corner_radius=8,
        fg_color=THEME_GREY_WIDGET, state="disabled"
    )
    # Placée en .grid() pour remplir l'espace restant
    decoupe_info.grid(row=1, column=0, sticky="nsew", pady=10, padx=5)

    # --- FIN MODIFICATION ERGONOMIE ---

    # --- Fonction de rappel (imbriquée) ---
    def _load_decoupe():
        name = decoupe_query.get().strip()
        user_id = session.utilisateur_connecte_id

        decoupe_info.configure(state="normal")
        decoupe_info.delete('1.0', tk.END)

        if not user_id:
            decoupe_info.insert(tk.END, "Erreur: Utilisateur non connecté.")
            decoupe_info.configure(state="disabled")
            return

        try:
            rows = list_subnet_results(name, user_id)

            if not rows:
                decoupe_info.insert(tk.END, "Réseau introuvable ou vous n'avez pas les permissions.\n")
                return

            # L'en-tête n'affiche plus le mode global
            header = f"Réseau: {name}\n\n"
            decoupe_info.insert(tk.END, header)

            # On boucle sur TOUS les résultats (l'historique)
            for i, r in enumerate(rows, start=1):
                # 1. En-tête du calcul
                header_calcul = f"--- Calcul #{i} (Mode: {r['mode']}) (Fait le {r['created_at']}) ---\n"

                # 2. Ligne d'entrée
                entree_calcul = f"Entrée: base_ip={r['base_ip']} masque={r['mask'] or ''}\n"

                # 3. Ligne réseau (sans préfixe pour l'instant)
                reseau_calcul = f"    réseau={r['network']}  broadcast={r['broadcast']}"

                # 4. Ligne préfixe (conditionnelle)
                prefix_calcul = ""
                if r['mode'] == 'classless':
                    prefix_calcul = f"  préfixe=/{r['prefixlen']}"  # Ajoute le préfixe

                # 5. Lignes des hôtes
                footer_calcul = f"\n    premier hôte={r['first_host']}  dernier hôte={r['last_host']}  nbr hôtes={r['hosts_count']}\n\n"

                # 6. Assemblage et insertion
                final_text = header_calcul + entree_calcul + reseau_calcul + prefix_calcul + footer_calcul
                decoupe_info.insert(tk.END, final_text)

        except PermissionError as e:
            messagebox.showerror("Accès refusé", str(e))
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

        decoupe_info.configure(state="disabled")

    # --- Bouton ---
    # Placé dans le .grid() du search_frame
    ctk.CTkButton(
        search_frame, text="Charger", command=_load_decoupe,
        fg_color=THEME_BLUE, hover_color=THEME_BLUE_HOVER,
        height=35, font=("Segoe UI", 16, "bold")
    ).grid(row=0, column=3, padx=10)


def lancer_application():
    """Crée et lance l'application principale."""

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    app = ctk.CTk()
    app.title("Outil Admin Réseau – IPv4")
    #app.geometry("900x650")
    app.update_idletasks()
    largeur = app.winfo_screenwidth()
    hauteur = app.winfo_screenheight()
    app.geometry(f"{largeur}x{hauteur}+0+0")
    app.configure(fg_color=THEME_FRAME_BG)

    # --- MODIFICATION : BOUTON DÉPLACÉ EN HAUT ---
    # Ce frame est maintenant en haut
    top_frame = ctk.CTkFrame(app, fg_color="transparent")
    # Il se colle en HAUT ('top') et remplit la largeur ('x')
    top_frame.pack(side="top", fill="x", pady=(10, 0), padx=20)

    btn_fermer = ctk.CTkButton(
        top_frame,
        text="Fermer l'application",
        command=app.destroy,
        fg_color=THEME_GREY_WIDGET,  # Style gris
        hover_color=THEME_GREY_HOVER, #
        text_color=THEME_TEXT_WHITE,
        width=250,  # Largeur fixe
        height=35,
        font=("Segoe UI", 14)
    )
    # Le bouton se colle à DROITE ('right') dans le 'top_frame'
    btn_fermer.pack(side="right")
    # --- FIN DE LA MODIFICATION ---

    # Création du conteneur d'onglets
    notebook = ctk.CTkTabview(
        app,
        fg_color=THEME_BACKGROUND,
        segmented_button_fg_color=THEME_GREY_WIDGET,
        segmented_button_selected_color=THEME_BLUE,
        segmented_button_selected_hover_color=THEME_BLUE_HOVER,
        segmented_button_unselected_hover_color=THEME_GREY_WIDGET
    )
    # Le notebook se place sous le 'top_frame' et remplit le reste
    notebook.pack(fill="both", expand=True, padx=10, pady=10)

    # Ajout des onglets
    tab1 = notebook.add(" Calcul réseau")
    tab2 = notebook.add(" Appartenance & Bornes")
    tab3 = notebook.add(" Retrouver un calcul via nom")

    # Construction du contenu de chaque onglet
    build_tab1(tab1)
    build_tab2(tab2)
    build_tab3(tab3)

    app.mainloop()


if __name__ == "__main__":
    init_db()  # Initialise la base de données
    lancer_application()  # Lance l'interface