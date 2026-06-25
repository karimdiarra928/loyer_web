import os
import sqlite3
import io
from flask import Flask, render_template_string, request, redirect, url_for, make_response
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)

# Sur Vercel, le seul dossier où on a le droit d'écrire est /tmp
CHEMIN_BDD = "/tmp/gestion_loyers.db"

def initialiser_bdd():
    conn = sqlite3.connect(CHEMIN_BDD)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            locataire TEXT,
            montant REAL,
            periode TEXT,
            date_paiement TEXT,
            statut TEXT DEFAULT 'Payé'
        )
    """)
    conn.commit()
    conn.close()

def generer_pdf_en_memoire(id_recu, locataire, montant, periode, date_paiement):
    tampon = io.BytesIO()
    c = canvas.Canvas(tampon, pagesize=letter)
    c.setLineWidth(1)
    c.rect(40, 40, 532, 712)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(306, 700, "REÇU DE PAIEMENT DE LOYER")
    c.setFont("Helvetica", 11)
    c.drawString(60, 650, f"Reçu N° : {id_recu}")
    c.drawString(60, 635, f"Date d'émission : {date_paiement}")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, 580, f"Bailleur : Gestion Immobilière PC")
    c.setFont("Helvetica", 12)
    c.drawString(60, 540, f"Certifie avoir reçu de Monsieur / Madame  {locataire}")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, 500, f"La somme de :  {montant:,} Francs CFA".replace(',', ' '))
    c.setFont("Helvetica", 12)
    c.drawString(60, 460, f"Période concernée : Mois de {periode}")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(400, 300, "Signature du bailleur")
    c.line(400, 230, 530, 230)
    c.save()
    tampon.seek(0)
    return tampon

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Gestion de Loyer Pro - Cloud</title>
    <style>
        body { font-family: sans-serif; background-color: #f4f6f9; padding: 20px; }
        .container { max-width: 1000px; margin: 0 auto; }
        .dashboard { display: flex; gap: 20px; margin-bottom: 20px; }
        .card { flex: 1; padding: 20px; border-radius: 8px; color: white; font-weight: bold; }
        .card-ca { background-color: #27ae60; }
        .card-impaye { background-color: #e74c3c; }
        .card-total { background-color: #2980b9; }
        .form-section { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .form-row { display: flex; gap: 15px; align-items: flex-end; }
        .form-group { flex: 1; }
        .form-group label { display: block; margin-bottom: 5px; font-size: 12px; font-weight: bold; }
        .form-group input, .form-group select { width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; }
        .btn-submit { background-color: #2c3e50; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; height: 35px; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; }
        th, td { padding: 12px; border-bottom: 1px solid #ddd; text-align: left; }
        th { background-color: #f8f9fa; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .badge-paye { background-color: #d4edda; color: #155724; }
        .badge-impaye { background-color: #f8d7da; color: #721c24; }
        .actions-cell { display: flex; gap: 8px; }
        .btn-download { background-color: #27ae60; color: white; text-decoration: none; padding: 5px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .btn-action { background-color: #2980b9; color: white; text-decoration: none; padding: 5px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .btn-delete { background-color: #c0392b; color: white; text-decoration: none; padding: 5px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏠 Gestion de Loyer Pro (En Ligne)</h1>
        <div class="dashboard">
            <div class="card card-ca"><h3>💰 Total Encaissé</h3><p>{{ "{:,.0f}".format(total_ca).replace(",", " ") }} FCFA</p></div>
            <div class="card card-impaye"><h3>⚠️ Total Impayés</h3><p>{{ "{:,.0f}".format(total_impaye).replace(",", " ") }} FCFA</p></div>
            <div class="card card-total"><h3>📝 Total Dossiers</h3><p>{{ total_dossiers }}</p></div>
        </div>
        <div class="form-section">
            <form action="/ajouter" method="POST" class="form-row">
                <div class="form-group"><label>Nom du Locataire</label><input type="text" name="locataire" required></div>
                <div class="form-group"><label>Montant du loyer</label><input type="number" name="montant" required></div>
                <div class="form-group"><label>Période / Mois</label><input type="text" name="periode" required></div>
                <div class="form-group">
                    <label>Statut</label>
                    <select name="statut">
                        <option value="Payé">Payé (Générer PDF)</option>
                        <option value="Impayé">Impayé</option>
                    </select>
                </div>
                <button type="submit" class="btn-submit">Enregistrer</button>
            </form>
        </div>
        <table>
            <thead>
                <tr>
                    <th>ID</th><th>Locataire</th><th>Montant</th><th>Période</th><th>Date</th><th>Statut</th><th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for r in recus %}
                <tr>
                    <td>{{ r[0] }}</td>
                    <td><strong>{{ r[1] }}</strong></td>
                    <td>{{ "{:,.0f}".format(r[2]).replace(",", " ") }} FCFA</td>
                    <td>{{ r[3] }}</td>
                    <td>{{ r[4] }}</td>
                    <td>
                        {% if r[5] == 'Payé' %}
                            <span class="badge badge-paye">✔ Payé</span>
                        {% else %}
                            <span class="badge badge-impaye">❌ Impayé</span>
                        {% endif %}
                    </td>
                    <td>
                        <div class="actions-cell">
                            {% if r[5] == 'Payé' %}
                                <a href="/telecharger/{{ r[0] }}" class="btn-download" target="_blank">📄 PDF</a>
                            {% else %}
                                <a href="/marquer-paye/{{ r[0] }}" class="btn-action">👉 Régler</a>
                            {% endif %}
                            <a href="/supprimer/{{ r[0] }}" class="btn-delete" onclick="return confirm('Supprimer ce dossier ?');">🗑 Supprimer</a>
                        </div>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    initialiser_bdd()
    conn = sqlite3.connect(CHEMIN_BDD)
    cursor = conn.cursor()
    cursor.execute("SELECT id, locataire, montant, periode, date_paiement, statut FROM recus ORDER BY id DESC")
    tous_recus = cursor.fetchall()
    cursor.execute("SELECT SUM(montant) FROM recus WHERE statut='Payé'")
    res_ca = cursor.fetchone()[0]
    total_ca = res_ca if res_ca is not None else 0
    cursor.execute("SELECT SUM(montant) FROM recus WHERE statut='Impayé'")
    res_imp = cursor.fetchone()[0]
    total_impaye = res_imp if res_imp is not None else 0
    total_dossiers = len(tous_recus)
    conn.close()
    return render_template_string(HTML_TEMPLATE, recus=tous_recus, total_ca=total_ca, total_impaye=total_impaye, total_dossiers=total_dossiers)

@app.route('/ajouter', methods=['POST'])
def ajouter():
    locataire = request.form['locataire']
    montant = float(request.form['montant'])
    periode = request.form['periode']
    statut = request.form['statut']
    date_jour = datetime.now().strftime("%d/%m/%Y")
    conn = sqlite3.connect(CHEMIN_BDD)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO recus (locataire, montant, periode, date_paiement, statut) VALUES (?, ?, ?, ?, ?)", (locataire, montant, periode, date_jour, statut))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/marquer-paye/<int:id_dossier>')
def marquer_paye(id_dossier):
    conn = sqlite3.connect(CHEMIN_BDD)
    cursor = conn.cursor()
    date_jour = datetime.now().strftime("%d/%m/%Y")
    cursor.execute("UPDATE recus SET statut='Payé', date_paiement=? WHERE id=?", (date_jour, id_dossier))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/supprimer/<int:id_dossier>')
def supprimer(id_dossier):
    conn = sqlite3.connect(CHEMIN_BDD)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM recus WHERE id=?", (id_dossier,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/telecharger/<int:id_dossier>')
def telecharger(id_dossier):
    conn = sqlite3.connect(CHEMIN_BDD)
    cursor = conn.cursor()
    cursor.execute("SELECT locataire, montant, periode, date_paiement FROM recus WHERE id=?", (id_dossier,))
    dossier = cursor.fetchone()
    conn.close()
    if dossier:
        pdf_data = generer_pdf_en_memoire(id_dossier, dossier[0], dossier[1], dossier[2], dossier[3])
        response = make_response(pdf_data.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=Recu_{id_dossier}.pdf'
        return response
    return "Introuvable", 404

if __name__ == '__main__':
    initialiser_bdd()
    app.run(debug=True)