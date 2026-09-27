import sqlite3
from pathlib import Path

database_path = Path(__file__).resolve().with_name('vraie_base.db')
conn = sqlite3.connect(database_path)

cur = conn.cursor()

classe = [
    (id_etudiant, 'Étudiant', f'Anonyme {id_etudiant:02d}', f'ANON-{id_etudiant:03d}')
    for id_etudiant in range(1, 47)
]

cur.executemany(
    """INSERT INTO etudiant (id, nom, prenom, matricule) VALUES (?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        nom = excluded.nom,
        prenom = excluded.prenom""",
    classe,
)

conn.commit()

conn.close()

print("Les étudiants ont été ajoutés ou étaient déjà présents.")