import sqlite3, json, os, hmac
from datetime import datetime
from contextlib import contextmanager
import hashlib
import session

DB_NAME = "reseau.db"
DB_PATH = os.environ.get("DATABASE_PATH", "reseau.db")
PBKDF2_ITER = int(os.environ.get("RESEAU_PBKDF2_ITER", "200000"))


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    """Crée les tables si elles n'existent pas"""
    with get_conn() as conn:  # Utilisation du context manager
        cur = conn.cursor()

        cur.executescript("""
        CREATE TABLE IF NOT EXISTS utilisateur (
            id_utilisateur INTEGER PRIMARY KEY AUTOINCREMENT,
            nom_utilisateur TEXT UNIQUE NOT NULL,
            mot_de_passe_hash BLOB NOT NULL,
            sel BLOB NOT NULL,
            date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    
        CREATE TABLE IF NOT EXISTS decoupe (
            id_decoupe INTEGER PRIMARY KEY AUTOINCREMENT,
            nom_decoupe TEXT UNIQUE NOT NULL,
            mode TEXT CHECK(mode IN ('classful','classless')) NOT NULL,
            ip_reseau TEXT NOT NULL,
            masque TEXT NOT NULL,
            nombre_sous_reseaux INTEGER,
            nombre_ips_par_sr INTEGER,
            type_decoupe TEXT CHECK(type_decoupe IN ('classique','vlsm')) NOT NULL,
            date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            date_maj TEXT NOT NULL,
            id_responsable INTEGER NOT NULL,
            FOREIGN KEY(id_responsable) REFERENCES utilisateur(id_utilisateur) ON DELETE CASCADE
        );
    
        CREATE TABLE IF NOT EXISTS sous_reseau (
            id_sous_reseau INTEGER PRIMARY KEY AUTOINCREMENT,
            id_decoupe INTEGER NOT NULL,
            ip_reseau TEXT NOT NULL,
            masque TEXT NOT NULL,
            ip_debut TEXT NOT NULL,
            ip_fin TEXT NOT NULL,
            ip_broadcast TEXT NOT NULL,
            nb_ips INTEGER,
            FOREIGN KEY(id_decoupe) REFERENCES decoupe(id_decoupe)
        );
            
        CREATE TABLE IF NOT EXISTS subnet_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            decoupe_name TEXT NOT NULL,
            owner_id INTEGER NOT NULL,
            mode TEXT NOT NULL,
            created_at TEXT NOT NULL,
            
            base_ip TEXT NOT NULL,
            mask TEXT,
            network TEXT NOT NULL,
            broadcast TEXT NOT NULL,
            prefixlen INTEGER NOT NULL,
            first_host TEXT,
            last_host TEXT,
            hosts_count INTEGER NOT NULL,
            
            FOREIGN KEY(owner_id) REFERENCES utilisateur(id_utilisateur) ON DELETE CASCADE
        );
    
        CREATE TABLE IF NOT EXISTS calc_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL, -- 'compute' | 'membership' | 'error'
            input_ip TEXT,
            input_mask TEXT,
            mode TEXT,
            result_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES utilisateur(id_utilisateur)
        );
    
        CREATE TABLE IF NOT EXISTS connexion_log (
            id_log INTEGER PRIMARY KEY AUTOINCREMENT,
            id_utilisateur INTEGER,
            statut TEXT CHECK(statut IN ('succès','échec')),
            date_connexion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            adresse_ip_client TEXT,
            FOREIGN KEY(id_utilisateur) REFERENCES utilisateur(id_utilisateur)
        );
            
        CREATE TABLE IF NOT EXISTS historique_tests (
            id_test INTEGER PRIMARY KEY AUTOINCREMENT,
            type_test TEXT NOT NULL,
            entree TEXT NOT NULL,
            resultat TEXT,
            est_valide BOOLEAN,
            date_test TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            id_utilisateur INTEGER,
            FOREIGN KEY(id_utilisateur) REFERENCES utilisateur(id_utilisateur)
        );
        """)



# --- FONCTIONS UTILISATEUR ---

"""
def hash_password(password: str) -> str:
    #Retourne le hash SHA256 du mot de passe
    return hashlib.sha256(password.encode()).hexdigest()
"""

def ajouter_utilisateur(nom, mot_de_passe):
    """Ajoute un utilisateur à la base et retourne son ID"""
    try:
        with get_conn() as conn:  # Utilisation du context manager
            cur = conn.cursor()
            import os

            salt = os.urandom(16)  # Génère un sel aléatoire
            pwd_hash = _pbkdf2_hash(mot_de_passe, salt)

            cur.execute(
                "INSERT INTO utilisateur (nom_utilisateur, mot_de_passe_hash, sel) VALUES (?, ?, ?)",
                (nom, pwd_hash, salt),
            )
            user_id = cur.lastrowid  # Récupère l'ID généré
            return user_id
    except sqlite3.IntegrityError:
        return None

#ne retourne rien!!!
def get_user_id(nom):
    """Retourne l'ID d'un utilisateur existant"""
    with get_conn() as conn:  # Utilisation du context manager
        cur = conn.cursor()
        cur.execute("SELECT id_utilisateur FROM utilisateur WHERE nom_utilisateur = ?", (nom,))
        row = cur.fetchone()
    return row[0] if row else None


def verifier_identifiants(nom, mot_de_passe):
    """Vérifie si le nom et mot de passe sont valides"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT mot_de_passe_hash, sel FROM utilisateur WHERE nom_utilisateur = ?",
            (nom,),
        )
        row = cur.fetchone()

    if row:
        pwd_hash, salt = row
        candidate = _pbkdf2_hash(mot_de_passe, salt)
        if hmac.compare_digest(candidate, pwd_hash):
            session.utilisateur_connecte_id = get_user_id(nom)
            return True
    return False

def verify_user(username: str, password: str) -> int | None:
    with get_conn() as c:
        row = c.execute(
            "SELECT id_utilisateur, mot_de_passe_hash, sel FROM utilisateur WHERE nom_utilisateur=?", (username,)
        ).fetchone()
        if not row:
            return None
        uid, pwd_hash, salt = row
        candidate = _pbkdf2_hash(password, salt)
        if hmac.compare_digest(candidate, pwd_hash):
            return uid
        return None


# --- FONCTIONS HISTORIQUE ---
def ajouter_test_historique(type_test, entree, resultat, est_valide, id_utilisateur):
    """Ajoute une entrée à l'historique des tests."""

    # Sécurité : ne rien faire si l'utilisateur n'est pas connecté
    if id_utilisateur is None:
        print("Avertissement: Tentative de log sans id_utilisateur.")
        return

    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO historique_tests (type_test, entree, resultat, est_valide, id_utilisateur)
                VALUES (?, ?, ?, ?, ?)
                """,
                (type_test, entree, resultat, est_valide, id_utilisateur)
            )

    except sqlite3.Error as e:
        # Dans une vraie application, on pourrait logger cette erreur dans un fichier
        print(f"Erreur lors de l'enregistrement de l'historique : {e}")










#vérifie si découpe existante si oui, la modifie, si non la crée
# Dans database.py

"""
# Modifiez la signature de la fonction pour accepter les nouveaux arguments
def ensure_decoupe(name: str, owner_id: int, mode: str, ip_reseau: str, masque: str, type_decoupe: str) -> int:
    now = datetime.utcnow().isoformat()
    with get_conn() as c:
        existing = c.execute(
            "SELECT id_decoupe, id_responsable FROM decoupe WHERE nom_decoupe=?", (name,)
        ).fetchone()

        if existing:
            did, oid = existing
            if oid != owner_id:
                raise PermissionError("Cette découpe appartient à un autre utilisateur.")

            # --- MODIFICATION ICI ---
            # Mettre à jour toutes les infos, pas seulement le mode
            c.execute(
                """"""UPDATE decoupe
                   SET mode=?,
                       ip_reseau=?,
                       masque=?,
                       type_decoupe=?,
                       date_maj=?
                   WHERE id_decoupe = ?"""""",
                (mode, ip_reseau, masque, type_decoupe, now, did),
            )
            return did

        # --- MODIFICATION ICI ---
        # Ajouter les nouvelles colonnes à l'INSERT
        cur = c.execute(
            """"""
            INSERT INTO decoupe(nom_decoupe, id_responsable, mode, ip_reseau, masque, type_decoupe, date_creation,
                                date_maj)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """""",
            (name, owner_id, mode, ip_reseau, masque, type_decoupe, now, now),
        )
        return cur.lastrowid
"""

#ajoute un résultat à la liste
def add_subnet_result(decoupe_name: str, owner_id: int, mode: str, result: dict, base_ip: str, mask: str | None):
    with get_conn() as c:
        c.execute(
            """
            INSERT INTO subnet_results(decoupe_name, owner_id, mode, created_at, -- Nouvelles colonnes
                                       base_ip, mask, network, broadcast, prefixlen,
                                       first_host, last_host, hosts_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                # Nouvelles valeurs
                decoupe_name,
                owner_id,
                mode,
                datetime.utcnow().isoformat(),

                # Valeurs du calcul (result)
                base_ip,
                mask,
                result["network"],
                result["broadcast"],
                result["prefixlen"],
                result["first_host"],
                result["last_host"],
                result["hosts_count"],
            ),
        )


#ajoute une entrée à l'historique des calculs
def log_calc_history(user_id: int, action: str, payload: dict):
    with get_conn() as c:
        c.execute(
            """
            INSERT INTO calc_history(user_id, action, input_ip, input_mask, mode, result_json, created_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (
                user_id,
                action,
                payload.get("input_ip"),
                payload.get("input_mask"),
                payload.get("mode"),
                json.dumps(payload.get("result") if payload.get("result") is not None else payload),
                datetime.utcnow().isoformat(),
            ),
        )


#récupérer une découpe par nom mais uniquement si elle appartient à l'utilisateur
"""def get_decoupe_by_name_for_owner(name: str, owner_id: int):
    with get_conn() as c:
        row = c.execute(
            "SELECT id_decoupe, nom_decoupe, id_responsable, mode, date_creation, date_maj FROM decoupe WHERE nom_decoupe=?",
            (name,),
        ).fetchone()
        if not row:
            return None
        did, nm, oid, mode, ca, ua = row
        if oid != owner_id:
            raise PermissionError("Vous n'êtes pas le responsable de cette découpe.")
        return {
            "id": did,
            "name": nm,
            "owner_id": oid,
            "mode": mode,
            "created_at": ca,
            "updated_at": ua,
        }
"""

# Recherche par nom et propriétaire directement dans la table 'subnet_results'
def list_subnet_results(decoupe_name: str, owner_id: int):
    with get_conn() as c:
        cur = c.execute(
            """
            SELECT base_ip, mask, network, broadcast, prefixlen, 
                   first_host, last_host, hosts_count,
                   mode, created_at
            FROM subnet_results 
            WHERE decoupe_name=? AND owner_id=? 
            ORDER BY id ASC
            """,
            (decoupe_name, owner_id),
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

def _pbkdf2_hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITER)


# Dans database.py

def update_decoupe_name(decoupe_id: int, new_name: str, owner_id: int):
    """
    Met à jour le nom d'une découpe, en vérifiant les permissions.
    Lève une ValueError si le nom est déjà pris ou si l'ID n'existe pas.
    Lève une PermissionError si l'utilisateur n'est pas le propriétaire.
    """
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        cur = conn.cursor()

        # 1. Vérifier les permissions
        cur.execute("SELECT id_responsable FROM decoupe WHERE id_decoupe = ?", (decoupe_id,))
        row = cur.fetchone()

        if not row:
            raise ValueError("La découpe n'existe pas.")

        if row[0] != owner_id:
            raise PermissionError("Vous n'êtes pas le propriétaire de cette découpe.")

        try:
            # 2. Tenter la mise à jour
            cur.execute(
                """
                UPDATE decoupe
                SET nom_decoupe = ?,
                    date_maj    = ?
                WHERE id_decoupe = ?
                """,
                (new_name, now, decoupe_id)
            )
        except sqlite3.IntegrityError:
            # Gérer le cas où le nouveau nom existe déjà
            raise ValueError(f"Le nom '{new_name}' est déjà pris.")


# Dans database.py

def get_decoupe_details(decoupe_id: int, owner_id: int):
    """
    Récupère les détails d'une découpe pour la modification.
    Lève une PermissionError si l'utilisateur n'est pas le propriétaire.
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT nom_decoupe, ip_reseau, masque, nombre_sous_reseaux, mode, type_decoupe, id_responsable
            FROM decoupe
            WHERE id_decoupe = ?
            """,
            (decoupe_id,)
        )
        row = cur.fetchone()

        if not row:
            raise ValueError("La découpe n'existe pas.")

        # Unpack
        (nom_decoupe, ip_reseau, masque, nb_sr, mode, type_de, id_resp) = row

        if id_resp != owner_id:
            raise PermissionError("Vous n'êtes pas le propriétaire de cette découpe.")

        return {
            "nom_decoupe": nom_decoupe,
            "ip_reseau": ip_reseau,
            "masque": masque,
            "nombre_sous_reseaux": nb_sr,
            "mode": mode,
            "type_decoupe": type_de,
        }


def update_full_decoupe(decoupe_id: int, owner_id: int, new_data: dict, new_subnets: list):
    """
    Met à jour une découpe et remplace atomiquement ses sous-réseaux.
    Lève une PermissionError si l'utilisateur n'est pas le propriétaire.
    """
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        cur = conn.cursor()

        # 1. Vérifier les permissions (double vérification)
        cur.execute("SELECT id_responsable FROM decoupe WHERE id_decoupe = ?", (decoupe_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError("La découpe n'existe pas.")
        if row[0] != owner_id:
            raise PermissionError("Vous n'êtes pas le propriétaire.")

        try:
            # 2. Mettre à jour l'entrée 'decoupe' principale
            cur.execute(
                """
                UPDATE decoupe
                SET nom_decoupe         = ?,
                    ip_reseau           = ?,
                    masque              = ?,
                    nombre_sous_reseaux = ?,
                    mode                = ?,
                    date_maj            = ?
                WHERE id_decoupe = ?
                """,
                (
                    new_data['nom_decoupe'],
                    new_data['ip_reseau'],
                    new_data['masque'],
                    new_data['nombre_sous_reseaux'],
                    new_data['mode'],
                    now,
                    decoupe_id
                )
            )

            # 3. Supprimer les *anciens* sous-réseaux
            cur.execute("DELETE FROM sous_reseau WHERE id_decoupe = ?", (decoupe_id,))

            # 4. Insérer les *nouveaux* sous-réseaux
            for sr in new_subnets:
                # 'sr' doit être un tuple/liste: (ip_reseau, masque, ip_debut, ip_fin, ip_broadcast, nb_ips)
                cur.execute(
                    """
                    INSERT INTO sous_reseau (id_decoupe, ip_reseau, masque, ip_debut, ip_fin, ip_broadcast, nb_ips)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (decoupe_id, *sr)
                )

        except sqlite3.IntegrityError as e:
            # Gérer le cas où le nouveau nom existe déjà
            conn.rollback()  # Annuler la transaction
            raise ValueError(f"Le nom '{new_data['nom_decoupe']}' est déjà pris.")
        except Exception as e:
            conn.rollback()  # Annuler
            raise e