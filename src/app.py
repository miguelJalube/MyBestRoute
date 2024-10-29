from solver import solve
from flask import Flask, render_template, request, redirect, url_for, flash
import pandas as pd
import os
import logging

app = Flask(__name__)
app.secret_key = "secret_key"
UPLOAD_FOLDER = "uploads"
RESULT_FOLDER = "results"
RESULTS_FILE = "results.csv"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["RESULT_FOLDER"] = RESULT_FOLDER

# Assurez-vous que le dossier 'uploads' existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def list_files(path):
    """Liste tous les fichiers dans le dossier d'uploads."""
    return [f for f in os.listdir(path) ]

def get_results(path):
    """Récupère les résultats stockés dans le fichier 'results.csv' s'il existe, si non le créé."""
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write("filename;url;")
    df = pd.read_csv(path, sep=";")
    results = []
    for i in range(len(df)):
        results.append({"filename": df.iloc[i, 0], "url": df.iloc[i, 1]})
    return results

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if "file" in request.files:
            file = request.files["file"]
            if file.filename == "" or not file.filename.endswith((".xlsx", ".xls")):
                flash("Veuillez sélectionner un fichier Excel valide")
                return redirect(request.url)
            
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(file_path)
            flash("Fichier uploadé avec succès")
            return redirect(url_for("index"))
        
    result_path = os.path.join(app.config["RESULT_FOLDER"], RESULTS_FILE)
    files = list_files(app.config["UPLOAD_FOLDER"])
    return render_template("index.html", results=get_results(result_path), files=files)

@app.route("/delete/<filename>")
def delete_file(filename):
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        flash(f"{filename} supprimé avec succès.")
    else:
        flash(f"{filename} n'existe pas.")
    return redirect(url_for("index"))

@app.route("/resolve/<filename>")
def resolve_file(filename):
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if os.path.exists(file_path):
        logging.info(f"Résolution du fichier {filename}")
        
        # On peut imaginer un traitement du fichier ici (ex. lecture du fichier)
        df = pd.read_excel(file_path)
        
        # Exemple de prévisualisation des 5 premières lignes
        url = solve(df)
        flash(f"{filename} résolu avec succès.")
        # stocker le résultat dans un fichier txt du même nom mais dans le répertoire 'results'
        result_path = os.path.join(app.config["RESULT_FOLDER"], RESULTS_FILE)
        with open(result_path, "a") as f:
            f.write("\n"+filename+";"+url+";")
        
        return render_template("index.html", results=get_results(result_path), files=list_files(app.config["UPLOAD_FOLDER"]))
    else:
        flash(f"{filename} n'existe pas.")
    return redirect(url_for("index"))


@app.route("/reset")
def reset():
    # remove results file
    result_path = os.path.join(app.config["RESULT_FOLDER"], RESULTS_FILE)
    if os.path.exists(result_path):
        os.remove(result_path)
    flash("Résultats réinitialisés avec succès.")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8072)
