import sqlite3
from pathlib import Path

database_path = Path(__file__).resolve().with_name('vraie_base.db')
conn = sqlite3.connect(database_path)

cur = conn.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS etudiant(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT,
            prenom TEXT,
            matricule VARCHAR(17) UNIQUE)
            """)
cur.execute("""CREATE TABLE IF NOT EXISTS seance(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matiere TEXT,
            date TEXT,
            heure_debut TEXT,
            heure_fin TEXT)
            """)
cur.execute("""CREATE TABLE IF NOT EXISTS presence(
            id_presence INTEGER PRIMARY KEY AUTOINCREMENT,
            id_seance INTEGER,
            id_etudiant INTEGER,
            statut TEXT,
            FOREIGN KEY (id_seance) REFERENCES seance(id),  
            FOREIGN KEY (id_etudiant) REFERENCES etudiant(id))
            """)
conn.commit()
conn.close()
