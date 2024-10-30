from solver import solve
from flask import Flask, render_template, request, redirect, url_for, flash
import pandas as pd
import os
import logging
import json

app = Flask(__name__)
app.secret_key = "secret_key"
UPLOAD_FOLDER = "uploads"
RESULT_FOLDER = "results"
RESULTS_FILE = "results.csv"
SETTINGS_FILE = "settings.txt"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["RESULT_FOLDER"] = RESULT_FOLDER

# Ensure the 'uploads' folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def list_files(path):
    """Lists all files in the uploads folder."""
    return [f for f in os.listdir(path)]

def get_results(path):
    """Retrieves results stored in the 'results.csv' file if it exists, otherwise creates it."""
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
                flash("Le fichier est invalide")
                return redirect(request.url)
            
            # Save the file to the uploads folder            
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)            
            file.save(file_path)
            
            # Check if the file has more than 10 addresses
            df = pd.read_excel(file_path)
            if len(df) > 9:
                logging.warning(f"Excel file lines {len(df)}")
                flash("Le fichier peut contenir maximum 9 adresses à traiter en plus du point de départ")
                os.remove(file_path)
                return redirect(request.url)
            
            flash("File uploaded successfully")
            return redirect(url_for("index"))
        
    result_path = os.path.join(app.config["RESULT_FOLDER"], RESULTS_FILE)
    files = list_files(app.config["UPLOAD_FOLDER"])
    results = get_results(result_path)
    return render_template("index.html", results=results, files=files)

@app.route("/delete/<filename>")
def delete_file(filename):
    """Deletes a specific file from the uploads folder."""
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        flash(f"{filename} deleted successfully.")
    else:
        flash(f"{filename} does not exist.")
    return redirect(url_for("index"))

@app.route("/resolve/<filename>")
def resolve_file(filename):
    """Processes a specific file using parameters from 'settings.txt'."""
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    
    # Get parameters from settings file
    start = ""
    try:
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)
            start = settings.get("start", "")
            mode = settings.get("mode", "duration")
            api_key = settings.get("api_key", "")
    except (FileNotFoundError, json.JSONDecodeError):
        start = ""
    
    if os.path.exists(file_path):
        logging.info(f"Resolving file {filename}")
        
        # Read and process the Excel file
        df = pd.read_excel(file_path)
        
        # Call solve function with provided parameters
        url, errors = solve(df, api_key, start, mode)
        flash(f"{filename} resolved successfully.")
        
        # Store the result in 'results.csv'
        result_path = os.path.join(app.config["RESULT_FOLDER"], RESULTS_FILE)
        with open(result_path, "a") as f:
            f.write("\n" + filename + ";" + url + ";")
            
        results = get_results(result_path)
        if len(errors) > 0:
            flash(f"Unable to find the following addresses: \n{errors}\n\nPlease try with other addresses")
        return render_template("index.html", results=results, files=list_files(app.config["UPLOAD_FOLDER"]))
    else:
        flash(f"{filename} does not exist.")
    return redirect(url_for("index"))

@app.route("/reset")
def reset():
    """Deletes the results file, effectively resetting stored results."""
    result_path = os.path.join(app.config["RESULT_FOLDER"], RESULTS_FILE)
    if os.path.exists(result_path):
        os.remove(result_path)
    flash("Results reset successfully.")
    return redirect(url_for("index"))

@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        api_key = request.form.get("api_key")
        start = request.form.get("start")
        mode = request.form.get("mode")
        settings = {
            "api_key": api_key,
            "start": start,
            "mode": mode
        }
        with open(SETTINGS_FILE, "w") as f:
            f.write(json.dumps(settings))
    else:
        # Load settings from file
        api_key = ""
        start = ""
        mode = ""
        try:
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
                api_key = settings.get("api_key", "")
                start = settings.get("start", "")
                mode = settings.get("mode", "")
        except (FileNotFoundError, json.JSONDecodeError):
            # Handle case where file does not exist or is empty/invalid
            api_key = ""
            start = ""
            mode = ""

    return render_template("settings.html", api_key=api_key, start=start, mode=mode)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8072)
