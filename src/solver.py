from pprint import pprint
import googlemaps # type: ignore
import os
import numpy as np
from helpers import log
from dotenv import load_dotenv
from python_tsp.heuristics import solve_tsp_simulated_annealing # type: ignore
from flask import jsonify # type: ignore

# example data
adresses = [
    "Piazza Castello, 6600 Locarno",
    "Mythen Center Schwyz, 6438 Ibach",
    "Stabile gorelle, 6592 San Antonio",
    "Baselstrasse 10, 4222 Zwingen",
    "Comercialstrasse 32, 7000 Chur",
    "Stauffacherstrasse 1, 6020 Emmenbrücke",
    "im Oberland-Shopping, 3800 Interlaken",
    "Rheinfelsstrasse 3b, 7000 Chur",
    "Etzelpark, 8808 Pfäffikon",
    "COOP-Center, 8132 Egg",
    "Schlosserstrasse 4, 8180 Bülach",
    "Moosmattstrasse 29, 8953 Dietikon",
    "Schinhuetweg 10, 5036 Oberentfelden"
]
    
def get_distance_matrix(api_key, addresses):
    """
    Obtain a complete distance matrix for a list of addresses using multiple requests.

    :param api_key: The Google Maps API key.
    :param addresses: A list of addresses to include in the distance matrix.
    :return: A matrix containing distances and durations.
    """
    # Initialize Google Maps client
    gmaps = googlemaps.Client(key=api_key)

    # Number of points to include in a single request
    max_points = 10

    # Split addresses into chunks of max_points
    address_chunks = [addresses[i:i + max_points] for i in range(0, len(addresses), max_points)]

    # Initialize matrices
    distances = []
    durations = []

    for i, chunk in enumerate(address_chunks):
        for j, chunk2 in enumerate(address_chunks):
            # Request the distance matrix for the current pair of chunks
            result = gmaps.distance_matrix(origins=chunk, destinations=chunk2, units='metric')
            
            if i == 0 and j == 0:
                # Initialize matrices with appropriate size
                num_origins = len(addresses)
                num_destinations = len(addresses)
                distances = np.empty((num_origins, num_destinations), dtype=object)
                durations = np.empty((num_origins, num_destinations), dtype=object)
            
            # Populate matrices
            for x, origin in enumerate(chunk):
                for y, destination in enumerate(chunk2):
                    if result['rows'][x]['elements'][y]['status'] == 'OK':
                        distances[addresses.index(origin)][addresses.index(destination)] = result['rows'][x]['elements'][y]['distance']['text']
                        durations[addresses.index(origin)][addresses.index(destination)] = result['rows'][x]['elements'][y]['duration']['text']
                    else:
                        # log error message with the addresses that caused the error
                        log(f"Status : {result['rows'][x]['elements'][y]['status']} for {origin} to {destination}", 'error')

    return {
        'distances': distances.tolist(),
        'durations': durations.tolist()
    }



def solve():
    gmaps_api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    
    pprint(get_distance_matrix(gmaps_api_key, adresses))
    return jsonify({"message": "Hello, World!"})
