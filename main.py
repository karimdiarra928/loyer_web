import os
import io
from flask import Flask, render_template_string, request, redirect, url_for, send_file
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from supabase import create_client

app = Flask(__name__)

# Configuration Supabase
SUPABASE_URL = "https://flfseahnmrthgowvnxjd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZsZnNlYWhubXJ0aGdvd3ZueGpkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODIzOTYwMDgsImV4cCI6MjA5Nzk3MjAwOH0.gMSL7eJwc7cbQahRV2Ff7-Fp3_StGdXBCbgWWjS66aw"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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
    <title>Gestion de Loyer Pro</title>
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
        .btn-submit { background-color: #2c3e50; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; height: 35px; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; }
        th, td { padding: 12px; border-bottom: 1px solid #ddd; text-align: left; }
        .btn-action { background-color: #2980b9; color: white; text-decoration: none; padding: 5px 10px; border-radius: 4px; font-size: 12px; }
        .btn-pdf { background-color: #27ae60; color: white; text-decoration: none; padding: 5px 10px; border-radius: 4px; font-size: 12px; }
        .btn-delete { background-color: #c0392b; color: white; text-decoration: none; padding: 5px 10px; border-radius: 4px; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏠 Gestion de Loyer Pro</h1>
        <div class="form-section">
            <form action="/ajouter" method="POST" class="form-row">
                <div class="form-group"><label>Locataire</label><input type="text" name="locataire" required></div>
                <div class="form-group"><label>Montant</label><input type="number" name="montant" required></div>
                <div class="form-group"><label>Période</label><input type="text" name="periode" required></div>
                <div class="form-group"><label>Statut</label><select name="statut"><option value="Payé">Payé</option><option value="Impayé">Impayé</option></select></div>
                <button type="submit" class="btn-submit">Enregistrer</button>
            </form>
        </div>
        <table>
            <thead><tr><th>ID</th><th>Locataire</th><th>Montant</th><th>Période</th><th>Statut</th><th>Actions</th></tr></thead>
            <tbody>
                {% for r in recus %}
                <tr>
                    <td>{{ r.id }}</td>
                    <td>{{ r.locataire }}</td>
                    <td>{{ "{:,.0f}".format(r.montant).replace(",", " ") }} FCFA</td>
                    <td>{{ r.periode }}</td>
                    <td>{{ r.statut }}</td>
                    <td>
                        {% if r.statut != 'Payé' %}<a href="/marquer-paye/{{ r.id }}" class="btn-action">Régler</a>{% endif %}
                        <a href="/telecharger-pdf/{{ r.id }}" class="btn-pdf">📄 PDF</a>
                        <a href="/supprimer/{{ r.id }}" class="btn-delete" onclick="return confirm('Confirmer ?');">🗑</a>
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
    response = supabase.table("recus").select("*").order("id", desc=True).execute()
    recus = response.data
    return render_template_string(HTML_TEMPLATE, recus=recus)

@app.route('/ajouter', methods=['POST'])
def ajouter():
    data = {
        "locataire": request.form['locataire'],
        "montant": float(request.form['montant']),
        "periode": request.form['periode'],
        "statut": request.form['statut'],
        "date_paiement": datetime.now().strftime("%Y-%m-%d")
    }
    supabase.table("recus").insert(data).execute()
    return redirect(url_for('index'))

@app.route('/telecharger-pdf/<int:id_dossier>')
def telecharger_pdf(id_dossier):
    response = supabase.table("recus").select("*").eq("id", id_dossier).single().execute()
    r = response.data
    pdf_buffer = generer_pdf_en_memoire(r['id'], r['locataire'], r['montant'], r['periode'], r['date_paiement'])
    return send_file(pdf_buffer, as_attachment=True, download_name=f"recu_{r['locataire']}.pdf", mimetype='application/pdf')

@app.route('/marquer-paye/<int:id_dossier>')
def marquer_paye(id_dossier):
    supabase.table("recus").update({"statut": "Payé"}).eq("id", id_dossier).execute()
    return redirect(url_for('index'))

@app.route('/supprimer/<int:id_dossier>')
def supprimer(id_dossier):
    supabase.table("recus").delete().eq("id", id_dossier).execute()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)