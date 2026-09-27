import sqlite3
from io import BytesIO
from datetime import date, datetime
from pathlib import Path
from xml.sax.saxutils import escape
from flask import Flask, abort, render_template, request, redirect, send_file, url_for
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

app = Flask(__name__)
DATABASE_PATH = Path(__file__).resolve().parent / 'base de données' / 'vraie_base.db'

def get_db_connection():
    # Connexion à la base de données
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Ici on pourra ajouter l'authentification avec mot de passe
        return redirect(url_for('statistique'))
    return render_template('connectio.html')

@app.route('/controle', methods=['GET', 'POST'])
def controle():
    conn = get_db_connection()
    try:
        etudiants = conn.execute('SELECT * FROM etudiant ORDER BY nom, prenom').fetchall()

        if request.method == 'POST':
            matiere = request.form.get('matiere', '').strip()
            date_seance = request.form.get('date_seance', '')
            if not matiere:
                erreur = 'Veuillez renseigner la matière.'
            else:
                try:
                    date.fromisoformat(date_seance)
                except ValueError:
                    erreur = 'Veuillez sélectionner une date valide.'
                else:
                    erreur = None

            presences = []
            if not erreur:
                for etudiant in etudiants:
                    statut = request.form.get(f"statut_{etudiant['id']}")
                    if statut not in ('present', 'absent'):
                        erreur = 'Veuillez choisir un statut pour chaque étudiant.'
                        break
                    presences.append((etudiant['id'], statut))

            if erreur:
                return render_template(
                    'controle.html',
                    etudiants=etudiants,
                    date_du_jour=date.today().isoformat(),
                    matiere=matiere,
                    date_seance=date_seance,
                    erreur=erreur,
                ), 400

            heure_debut = datetime.now().strftime('%H:%M')
            with conn:
                seance = conn.execute(
                    'INSERT INTO seance (matiere, date, heure_debut) VALUES (?, ?, ?)',
                    (matiere, date_seance, heure_debut),
                )
                id_seance = seance.lastrowid
                conn.executemany(
                    'INSERT INTO presence (id_seance, id_etudiant, statut) VALUES (?, ?, ?)',
                    [(id_seance, id_etudiant, statut) for id_etudiant, statut in presences],
                )
            return redirect(url_for('statistique'))

        return render_template(
            'controle.html',
            etudiants=etudiants,
            date_du_jour=date.today().isoformat(),
        )
    finally:
        conn.close()

@app.route('/exporter/pdf', methods=['POST'])
def exporter_pdf():
    conn = get_db_connection()
    try:
        etudiants = conn.execute('SELECT * FROM etudiant ORDER BY nom, prenom').fetchall()
    finally:
        conn.close()

    matiere = request.form.get('matiere', '').strip()
    date_seance = request.form.get('date_seance', '')
    if not matiere:
        abort(400, description='Veuillez renseigner la matière avant l’export.')
    try:
        date_export = date.fromisoformat(date_seance)
    except ValueError:
        abort(400, description='Veuillez sélectionner une date valide avant l’export.')
    if not etudiants:
        abort(404, description='Aucun étudiant à exporter.')

    styles = getSampleStyleSheet()
    lignes = [['N°', 'Nom', 'Prénom', 'Statut']]
    for numero, etudiant in enumerate(etudiants, start=1):
        statut = request.form.get(f"statut_{etudiant['id']}")
        if statut not in ('present', 'absent'):
            abort(400, description='Veuillez choisir un statut pour chaque étudiant.')
        lignes.append([
            str(numero),
            Paragraph(escape(etudiant['nom'] or ''), styles['BodyText']),
            Paragraph(escape(etudiant['prenom'] or ''), styles['BodyText']),
            'Présent' if statut == 'present' else 'Absent',
        ])

    pdf = BytesIO()
    document = SimpleDocTemplate(
        pdf,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )
    tableau = Table(lignes, colWidths=[15 * mm, 55 * mm, 70 * mm, 40 * mm], repeatRows=1)
    tableau.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#17436a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#cbd3d9')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f1f4f6')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]))
    contenu = [
        Paragraph('Feuille de présence', styles['Title']),
        Paragraph(f'<b>Matière :</b> {escape(matiere)}', styles['Normal']),
        Paragraph(f'<b>Date :</b> {date_export.strftime("%d/%m/%Y")}', styles['Normal']),
        Spacer(1, 6 * mm),
        tableau,
    ]
    document.build(contenu)
    pdf.seek(0)
    nom_fichier = f"presences_{date_export.isoformat()}.pdf"
    return send_file(pdf, mimetype='application/pdf', as_attachment=True, download_name=nom_fichier)

@app.route('/exporter/excel')
def exporter_excel():
    conn = get_db_connection()
    try:
        lignes = conn.execute(
            """SELECT seance.date, seance.matiere, etudiant.id,
                      etudiant.nom, etudiant.prenom, etudiant.matricule,
                      presence.statut
               FROM etudiant
               LEFT JOIN presence ON presence.id_etudiant = etudiant.id
               LEFT JOIN seance ON seance.id = presence.id_seance
               ORDER BY seance.date DESC, seance.id DESC, etudiant.nom, etudiant.prenom"""
        ).fetchall()
    finally:
        conn.close()

    classeur = Workbook()
    feuille = classeur.active
    feuille.title = 'Présences'
    feuille.append(['Date', 'Matière', 'ID étudiant', 'Nom', 'Prénom', 'Matricule', 'Statut'])
    for cellule in feuille[1]:
        cellule.font = Font(bold=True, color='FFFFFF')
        cellule.fill = PatternFill(fill_type='solid', fgColor='17436A')

    for ligne in lignes:
        statut = {'present': 'Présent', 'absent': 'Absent'}.get(ligne['statut'], '')
        feuille.append([
            ligne['date'] or '',
            ligne['matiere'] or '',
            ligne['id'],
            ligne['nom'] or '',
            ligne['prenom'] or '',
            ligne['matricule'] or '',
            statut,
        ])

    feuille.freeze_panes = 'A2'
    feuille.auto_filter.ref = feuille.dimensions
    for colonne in feuille.columns:
        largeur = max(len(str(cellule.value or '')) for cellule in colonne)
        feuille.column_dimensions[get_column_letter(colonne[0].column)].width = min(largeur + 2, 40)

    fichier = BytesIO()
    classeur.save(fichier)
    fichier.seek(0)
    return send_file(
        fichier,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='export_presences.xlsx',
    )

@app.route('/statistique')
def statistique():
    # Tableau de bord
    return render_template('statistique.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
