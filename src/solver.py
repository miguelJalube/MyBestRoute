import time
from pprint import pprint
import googlemaps  # type: ignore
import os
from helpers import log
from dotenv import load_dotenv
from python_tsp.heuristics import solve_tsp_local_search  # type: ignore
from flask import Flask, jsonify  # type: ignore
import numpy as np
import requests
from geopy.geocoders import Photon, Nominatim  # type: ignore
# Create a Flask app
app = Flask(__name__)

TSP_PROCESSING_TIME =       5
OSM_DELAY =                 0.5

def get_coordinates(adresses):
    # Initialiser le géocodeur Nominatim
    geolocator = Photon(user_agent="measurements")
    geolocator = Nominatim(user_agent="measurements")

    result = []

    for address in adresses:
        
        print(f"Getting coordinates for address: {address}")
        
        # Faire une requête pour obtenir les coordonnées
        location = geolocator.geocode(address)
        print(location)

        if location:
            # Extraire les coordonnées
            latitude = location.latitude
            longitude = location.longitude
            result.append({"latitude":latitude, "longitude": longitude})
        else:
            return None
        # wait 1 second
        time.sleep(OSM_DELAY)
        
    return result

# Get geometric distance between two points
def dist(orig, dest):
    x1 = orig['latitude']
    y1 = orig['longitude']
    x2 = dest['latitude']
    y2 = dest['longitude']
    
    dist = ((x2 - x1)**2 + (y2 - y1)**2)**0.5
    return dist

def get_dm_coordinates(coordinates):
    # construct a numpy matrix with the distances between each pair of activities
    n = len(coordinates)
    dm = np.zeros((n, n))
    for i in range(n):
        for j in range(i, n):
            dm[i, j] = dist((coordinates[i]), (coordinates[j]))
            dm[j, i] = dm[i, j]
    return dm

def get_dm_osm(coordinates):
    n = len(coordinates)
    dm = np.zeros((n, n))

    # Construire la chaîne pour les origines
    origins = ';'.join([f"{lat},{lon}" for lat, lon in coordinates])
    
    # Construire la chaîne pour les destinations
    destinations = origins  # Pour la matrice de distances, les destinations sont les mêmes que les origines
    
    # Appel à l'API OSRM
    url = f"http://router.project-osrm.org/table/v1/driving/{origins}?destinations={destinations}&annotations=distance"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        result = response.json()
        
        for i in range(n):
            for j in range(n):
                dm[i, j] = result['durations'][i][j]  # Durée, peut être changé à distance si nécessaire
    else:
        print(f"Erreur lors de l'appel à l'API: {response.status_code}")
    
    return dm

def solve_tsp(distance_matrix):
    print(distance_matrix)
    permutation, distance = solve_tsp_local_search(distance_matrix, max_processing_time=TSP_PROCESSING_TIME)
    return permutation, distance

def generate_google_maps_link(waypoints):
    base_url = "https://www.google.com/maps/dir/"
    
    for waypoint in waypoints:
        if waypoint != None:
            if waypoint['latitude'] != 0 and waypoint['longitude'] != 0:
                base_url += str(waypoint['latitude']) + "," + str(waypoint['longitude']) + "/"
    
    return base_url

def solve(addresses):
    coordinates = get_coordinates(addresses)
    dm = get_dm_coordinates(coordinates)
    optimal_order, _ = solve_tsp(dm)
    return generate_google_maps_link([coordinates[i] for i in optimal_order])

if __name__ == '__main__':
    addresses = [
        "Paris",
        "Lyon",
        "Marseille",
        "Toulouse",
        "Nice",
        "Nantes",
        "Strasbourg",
        "Montpellier",
        "Bordeaux",
        "Lille",
        "Rennes",
        "Reims",
        "Le Havre",
        "Saint-Étienne",
        "Toulon",
        "Grenoble"
    ]

    
    print(solve(addresses))
