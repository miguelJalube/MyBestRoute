import time
from pprint import pprint
import googlemaps  # type: ignore
import os
from dotenv import load_dotenv
from python_tsp.heuristics import solve_tsp_local_search  # type: ignore
from flask import Flask, jsonify  # type: ignore
import numpy as np
import requests
from geopy.geocoders import Photon, Nominatim  # type: ignore
# logger
import logging
import json


# Create a Flask app

TSP_PROCESSING_TIME =       5
OSM_DELAY =                 0.5
MAX_GMAPS_DEST =            10

# write json in log file
def write_json_log(log_file, data):
    with open(log_file, 'a') as f:
        f.write(data)

def get_coordinates(addresses):
    # Initialiser le géocodeur Nominatim
    geolocator = Photon(user_agent="measurements")
    geolocator = Nominatim(user_agent="measurements")

    result = []
    errors = []

    for address in addresses:
        logging.info(f"Getting coordinates for address: {address}")
        
        # Faire une requête pour obtenir les coordonnées
        location = geolocator.geocode(address)

        if location:
            # Extraire les coordonnées
            latitude = location.latitude
            longitude = location.longitude
            result.append({"latitude":latitude, "longitude": longitude})
        else:
            logging.warning(f"Could not find coordinates for address: {address}")
            errors.append(address)
        time.sleep(OSM_DELAY)
        
    return result, errors

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

def get_dm_gm(addresses, api_key):
    gmaps = googlemaps.Client(key=api_key)
    origins = addresses
    destinations = origins

    matrix = gmaps.distance_matrix(origins, destinations, mode="driving")

    return matrix

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

def transform_to_tsp_format(gmaps_response, mode="duration"):
    # Load JSON if it's not already a dictionary
    if isinstance(gmaps_response, str):
        gmaps_response = json.loads(gmaps_response)
    
    # Get destination and origin addresses
    destinations = gmaps_response['destination_addresses']
    origins = gmaps_response['origin_addresses']
    n = len(destinations)
    
    # Initialize a distance matrix with infinity
    distance_matrix = np.full((n, n), float('inf'))
    
    # Fill the distance matrix
    for i, row in enumerate(gmaps_response['rows']):
        for j, element in enumerate(row['elements']):
            if element['status'] == 'OK':
                distance_matrix[i][j] = element['duration']['value']  # Use duration for TSP
            else:
                distance_matrix[i][j] = float('inf')  # Indicate no route available

    return distance_matrix

def reorder_addresses(addresses, order):
    """
    Reorder a list of addresses based on a specified order.

    Parameters:
    addresses (list): The original list of addresses.
    order (list): A list of indices representing the new order.

    Returns:
    list: The reordered list of addresses.
    """
    reordered_addresses = [addresses[i] for i in order if i < len(addresses)]
    return reordered_addresses

def generate_google_maps_link(addresses):
    base_url = "https://www.google.com/maps/dir/"
    
    for address in addresses:
        if address:
            # Encode the address to make it URL-safe
            base_url += f"{address}/"
    
    return base_url

def solve(df, api_key, start="", mode="duration"):
    # get a list of adresses, code postal, ville
    
    # remove rows with missing addresses
    df = df.dropna(subset=["Adresse 1"])
    
    addresses = df["Adresse 1"].tolist()
    postal_codes = df["Code postal"].tolist()
    cities = df["Ville"].tolist()
    
    postal_codes = [str(int(float(code))) for code in postal_codes if not np.isnan(code) and code != ""]
    
    # concatenate the address, postal code and city
    addresses = [f"{address}, {postal_code} {city}" for address, postal_code, city in zip(addresses, postal_codes, cities)]
    
    if start != "":
        addresses.insert(0, start)
    
    errors = []
    
    # Get gmaps distance matrix
    dm = get_dm_gm(addresses[:MAX_GMAPS_DEST], api_key)
    
    # Change the format to fit tsp library
    tsp_matrix = transform_to_tsp_format(dm, mode)
    
    # Solve tsp
    optimal_order, _ = solve_tsp_local_search(tsp_matrix, max_processing_time=TSP_PROCESSING_TIME)
    
    # Reorder destinations
    reordered_addresses = reorder_addresses(addresses, optimal_order)
    
    return generate_google_maps_link(reordered_addresses), errors
