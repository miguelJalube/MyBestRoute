import time
from pprint import pprint
import googlemaps # type: ignore
import os
from dotenv import load_dotenv
from python_tsp.heuristics import solve_tsp_local_search, solve_tsp_simulated_annealing
from flask import Flask, jsonify
import numpy as np
import requests
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
    
    # Get gmaps distance matrix
    dm, errors = get_dm_gm(addresses[:MAX_GMAPS_DEST], api_key)
    
    # Change the format to fit tsp library
    tsp_matrix = transform_to_tsp_format(dm, mode)
    
    # Solve tsp
    #optimal_order, _ = solve_tsp_local_search(tsp_matrix, max_processing_time=TSP_PROCESSING_TIME)
    optimal_order, _ = solve_tsp_simulated_annealing(tsp_matrix, max_processing_time=TSP_PROCESSING_TIME)
    
    # Reorder destinations
    reordered_addresses = reorder_addresses(addresses, optimal_order)
    
    logging.warning(generate_google_maps_link(addresses))
    
    return generate_google_maps_link(reordered_addresses), errors
