import time
from pprint import pprint
import googlemaps # type: ignore
import os
from dotenv import load_dotenv
from python_tsp.heuristics import solve_tsp_local_search, solve_tsp_simulated_annealing
from python_tsp.exact import solve_tsp_dynamic_programming
from flask import Flask, jsonify
import numpy as np
import requests
# logger
import logging
import json


# Create a Flask app

TSP_PROCESSING_TIME =       20
OSM_DELAY =                 0.5
MAX_GMAPS_DEST =            10

# write json in log file
def write_json_log(data,log_file="log.txt"):
    with open(log_file, 'a') as f:
        f.write(data)

def get_coordinates(address, api_key):
    # Initialiser le client Google Maps
    gmaps = googlemaps.Client(key=api_key)

    # Effectuer le geocoding de l'adresse
    geocode_result = gmaps.geocode(address)

    # Vérifier si des résultats ont été trouvés
    if geocode_result:
        # Récupérer la première coordonnée (latitude, longitude)
        location = geocode_result[0]['geometry']['location']
        return {"lat":location['lat'],"lng": location['lng']}
    else:
        print("Aucun résultat trouvé pour l'adresse donnée.")
        return None
    
# Get geometric distance between two points
def dist(orig, dest):
    x1 = orig['lat']
    y1 = orig['lng']
    x2 = dest['lat']
    y2 = dest['lng']
    
    dist = ((x2 - x1)**2 + (y2 - y1)**2)**0.5
    return dist

def get_dm_coordinates(coordinates):
    # construct a numpy matrix with the distances between each pair of activities
    n = len(coordinates)
    dm = np.zeros((n, n))
    for i in range(n):
        for j in range(i, n):
            if coordinates[i] != None and coordinates[j] != None:
                dm[i, j] = dist((coordinates[i]), (coordinates[j]))
                dm[j, i] = dm[i, j]
    return dm

def get_dm_gm(addresses, api_key):
    gmaps = googlemaps.Client(key=api_key)
    origins = addresses
    destinations = origins

    matrix = gmaps.distance_matrix(origins, destinations, mode="driving")
    
    errors = []
    
    # check for errors for each address
    for i, row in enumerate(matrix['rows']):
        for j, element in enumerate(row['elements']):
            if element['status'] != 'OK':
                error = f"Error for address {i} -> {j}"
                logging.error(error)
                errors.append(error)

    return matrix, errors

def transform_to_tsp_format(distance_matrix, mode="duration"):
    # Si `distance_matrix` est déjà une matrice NumPy, on la retourne directement.
    if isinstance(distance_matrix, np.ndarray):
        return distance_matrix
    else:
        # Si la matrice est encore dans un format brut (par exemple, sous forme de réponse JSON), on traite comme avant.
        destinations = distance_matrix['destination_addresses']
        origins = distance_matrix['origin_addresses']
        n = len(destinations)
        
        # Initialiser une matrice de distances avec infini par défaut
        full_distance_matrix = np.full((n, n), float('inf'))
        
        # Remplir la matrice de distances
        for i, row in enumerate(distance_matrix['rows']):
            for j, element in enumerate(row['elements']):
                if element['status'] == 'OK':
                    full_distance_matrix[i][j] = element['duration']['value']
        
        return full_distance_matrix

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
    
    # If adresses exceed MAX_GMAPS_DEST, use coordinates
    if len(addresses) > MAX_GMAPS_DEST:
        
        # Get distances using coordinates
        coordinates = []
        for address in addresses:
            coordinates.append(get_coordinates(address, api_key))
        write_json_log(json.dumps(coordinates))
        dm = get_dm_coordinates(coordinates)
    else:
        
        # Get gmaps distance matrix
        dm, errors = get_dm_gm(addresses, api_key)
    
    # Change the format to fit tsp library
    tsp_matrix = transform_to_tsp_format(dm, mode)
    
    # Solve tsp
    optimal_order, _ = solve_tsp_local_search(tsp_matrix, max_processing_time=TSP_PROCESSING_TIME)
    #optimal_order, _ = solve_tsp_simulated_annealing(tsp_matrix, max_processing_time=TSP_PROCESSING_TIME)
    #optimal_order, _ = solve_tsp_dynamic_programming(tsp_matrix)
    
    # Reorder destinations
    reordered_addresses = reorder_addresses(addresses, optimal_order)
    
    logging.warning(generate_google_maps_link(addresses))
    
    return generate_google_maps_link(reordered_addresses), errors
