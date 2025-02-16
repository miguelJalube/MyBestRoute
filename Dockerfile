# Utilise une image Python officielle comme image de base
FROM python:3.9-slim

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Copier le fichier requirements.txt dans le répertoire de travail
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt
RUN ls

# Copier le reste de l'application dans le répertoire de travail
COPY ./src .

# Créer /src/results/results.csv
RUN mkdir -p /results
RUN touch /results/results.csv
RUN touch settings.txt

# Exposer le port sur lequel l'application s'exécute
EXPOSE 8072

# Définir la commande pour exécuter l'application
CMD ["python", "app.py"]