import sqlite3
import hashlib

DB_NAME = "reseau.db"


def get_connection():
    """Crée la connexion vers la base SQLite"""
    return sqlite3.connect(DB_NAME)


def init_db():
    """Crée les tables si elles n'existent pas"""
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS utilisateur (
        id_utilisateur INTEGER PRIMARY KEY AUTOINCREMENT,
        nom_utilisateur TEXT UNIQUE NOT NULL,
        mot_de_passe_hash TEXT NOT NULL,
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
        id_responsable INTEGER NOT NULL,
        FOREIGN KEY(id_responsable) REFERENCES utilisateur(id_utilisateur)
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

    CREATE TABLE IF NOT EXISTS connexion_log (
        id_log INTEGER PRIMARY KEY AUTOINCREMENT,
        id_utilisateur INTEGER,
        statut TEXT CHECK(statut IN ('succès','échec')),
        date_connexion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        adresse_ip_client TEXT,
        FOREIGN KEY(id_utilisateur) REFERENCES utilisateur(id_utilisateur)
    );
    """)

    conn.commit()
    conn.close()


# --- FONCTIONS UTILISATEUR ---

def hash_password(password: str) -> str:
    """Retourne le hash SHA256 du mot de passe"""
    return hashlib.sha256(password.encode()).hexdigest()


def ajouter_utilisateur(nom, mot_de_passe):
    """Ajoute un utilisateur à la base"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO utilisateur (nom_utilisateur, mot_de_passe_hash) VALUES (?, ?)",
            (nom, hash_password(mot_de_passe)),
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False


def verifier_identifiants(nom, mot_de_passe):
    """Vérifie si le nom et mot de passe sont valides"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT mot_de_passe_hash FROM utilisateur WHERE nom_utilisateur = ?",
        (nom,),
    )
    row = cur.fetchone()
    conn.close()
    if row and row[0] == hash_password(mot_de_passe):
        return True
    return False
