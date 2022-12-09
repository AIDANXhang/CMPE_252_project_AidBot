#importing the required libraries
import requests
from typing import Any, Text, Dict, List
from word2number import w2n
import pandas as pd
import numpy as np
import mysql.connector
import os

from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim

from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk import Action, Tracker, ValidationAction, FormValidationAction

from .db import data_store

#foursquare places api
foursquare_api_key = "fsq3ssFHJclZ2JzzOQ9r8r/sJwRPggft93bPxr/xwGlqWXM="

# leaflet api key
leaflet_api_key = "AAPKf10223e6e21440cfba745c87359941e6YPlQFsdtdpvjAlD5r67eXbDPpBW2FpwRjepKlnKDJ4CPOSYKN-URqffOPUG08FOb"

# geopy - to locate the coordinates of addresses, cities, landmarks, etc
geopy_locator = Nominatim(user_agent = "rasa_chat")
reverse = RateLimiter(geopy_locator.reverse, min_delay_seconds = 0.1)

class beginSearchAction(Action):
    
    def name(self) -> Text:
        return "begin_search_action"

    def run(self, dispatcher:CollectingDispatcher, tracker:Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:        
        dispatcher.utter_message(text=f'AidBot is searching for a {tracker.get_slot("category_place")} in {", ".join(tracker.get_slot("address"))} within {tracker.get_slot("radius")} km. Thanks for waiting!')
        return []

class searchForMedicalCareAction(Action):
    
    def __init__(self) -> None:
        self.code_dict = {'dentist':'15007', 'hospital':'15014', 'psychologist':'15020', 'nursing home':'15022', 'surgeon':'15035', 'veterinarian':'15054'} # giving category IDs for places
    
    def name(self) -> Text:
        return "search_for_medical_care_action"
    
    def run(self, dispatcher: CollectingDispatcher, tracker:Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        foursquare_url = 'https://api.foursquare.com/v3/places/search'
        foursquare_header = {"Accept": "application/json", "Authorization": foursquare_api_key}
        leaflet_header = {"Accept": "application/json", "Authorization": leaflet_api_key}
        
        place_types = self.code_dict[tracker.get_slot('category_place')]
        location = tracker.get_slot('lat_lon')
        radius = int(float(tracker.get_slot('radius'))*1000)      
        
        foursquare_params = {'ll':location, 'radius':radius, 'categories':place_types}

        try:
            foursquare_response = requests.get(foursquare_url, params = foursquare_params, headers = foursquare_header)
            foursquare_result = {'name':[], 'lat':[], 'lon':[], 'distance':[]}
            
            for each_instance in foursquare_response.json()['results']:
                foursquare_result['name'].append(each_instance['name'])
                foursquare_result['lat'].append(each_instance['geocodes']['main']['latitude'])
                foursquare_result['lon'].append(each_instance['geocodes']['main']['longitude'])
                foursquare_result['distance'].append(each_instance['distance'] / 1000)
            
            foursquare_df = pd.DataFrame(foursquare_result) 
            foursquare_df['address'] = foursquare_df.apply(lambda x: reverse((x['lat'], x['lon']) ).address , axis=1) #geopy reverse is used to get address from coordinates
            
            aidbot_response = 'You can seek medical care at: \n\n' + '\n\n'.join(foursquare_df.apply(lambda x: f" ==> {x['name']}. \nIt is located at : {x['address']}", axis=1)) + '\n\nI hope that was helpful!'
        
        except:
            aidbot_response = 'Sorry! No results found! Try again with a different address in a bit.'
        
        dispatcher.utter_message(text = aidbot_response)
        data_store(str(place_types), str(location), str(aidbot_response))
        return []

class checkForSlots(ValidationAction):
    
    def validate_address(self, slot_value: List, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any],) -> Dict[Text, Any]:    
        try:
            location = geopy_locator.geocode(', '.join(slot_value))
            
            if location is None:
                dispatcher.utter_message(template="utter_wrong_address") # address not recognized by geopy
                return {"address": None}
            
            else:
                return {"address": slot_value, 'lat_lon': f'{location.latitude},{location.longitude}'}
        
        except:
            dispatcher.utter_message(text='Cannot process your request at the moment. Please try again in some time. Sorry for the inconvenience.')

    def validate_radius(self, slot_value: Text, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any],) -> Dict[Text, Any]:
        try:
            word2number =  w2n.word_to_num(slot_value)
            
            if word2number < 0.5:
                dispatcher.utter_message(text = 'Searching limit is set to 0.5 km. Proceeding with the search radius of 0.5 km.')
                return {'radius': str(0.5)}

            elif word2number > 80:
                dispatcher.utter_message(text = 'Searching limit is set to 80 km. Proceeding with the search radius of 80 km.')
                return {'radius': str(80)}
            
            else:
                return {'radius': str(word2number)}
        
        except:
            dispatcher.utter_message(template="utter_wrong_radius")
            return {"radius": None}

class checkSearchedPlacesForm(FormValidationAction):
    def name(self) -> Text:
        return 'check_form_search_places'
    
    def validate_address(self, slot_value: List, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any],) -> Dict[Text, Any]:
        try:
            location = geopy_locator.geocode(', '.join(slot_value))
            
            if location is None:
                dispatcher.utter_message(template="utter_wrong_address")
                return {"address": None}
            
            else:
                return {"address": slot_value, 'lat_lon': f'{location.latitude},{location.longitude}'}
        
        except:
            dispatcher.utter_message(text='Cannot process your request at the moment. Please try again in some time. Sorry for the inconvenience.')
    
    def validate_radius(self, slot_value: Text, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any],) -> Dict[Text, Any]:
        try:
            word2number =  w2n.word_to_num(slot_value)
            
            if word2number < 0.5:
                dispatcher.utter_message(text = 'Searching limit is set to 0.5 km. Proceeding with the search radius of 0.5 km.')
                return {'radius': str(0.5)}

            elif word2number > 80:
                dispatcher.utter_message(text = 'Searching limit is set to 80 km. Proceeding with the search radius of 80 km.')
                return {'radius': str(80)}
            
            else:
                return {'radius': str(word2number)}
        
        except:
            dispatcher.utter_message(template="utter_wrong_radius")
            return {"radius": None}