import bisect
import pandas as pd
from pandas import DataFrame
from typing import List

INPUT_PATH = "Input/"
OUTPUT_PATH = "Output/"

MUNICIPALITIES_FILE = 'municipalities-data-2025.csv'
TARIFS_FILE = 'elcom-data-2025.csv'

# Profils de consommation de ménages types:
# H1: 1600 kWh/an: logement de 2 pièces avec cuisinière électrique
# H2: 2500 kWh/an: logement de 4 pièces avec cuisinière électrique
# H3: 4500 kWh/an: logement de 4 pièces avec cuisinière électrique et chauffe-eau électrique
# H4: 4500 kWh/an: logement de 5 pièces avec cuisinière électrique et sèche-linge (sans chauffe-eau électrique)
# H5: 7500 kWh/an: maison individuelle de 5 pièces avec cuisinière électrique , chauffe-eau électrique et sèche-linge
# H6: 25 000 kWh/an: maison individuelle de 5 pièces avec cuisinière électrique , chauffe-eau électrique, sèche-linge et chauffage électrique à résistance
# H7: 13 000 kWh/an: maison individuelle de 5 pièces avec cuisinière électrique , chauffe-eau électrique, sèche-linge et pompe à chaleur de 5 kW pour le chauffage
# H8: 7500 kWh/an: grand logement en propriété, avec large utilisation de l'électricité
# Profils de consommation pour les entreprises artisanales et industrielles:
# C1: 8000 kWh/an: très petite entreprise, puissance max.: 8 kW
# C2: 30 000 kWh/an: petite entreprise, puissance max.: 15 kW
# C3: 150 000 kWh/an: entreprise moyenne, puissance max.: 50 kW
# C4: 500 000 kWh/an: grande entreprise, puissance max.: 150 kW, courant basse tension
# C5: 500 000 kWh/an: grande entreprise, puissance max.: 150 kW, courant moyenne tension, propre station de transformation
# C6: 1 500 000 kWh/an: grande entreprise, puissance max.: 400 kW, courant moyenne tension, propre station de transformation
# C7: 7 500 000 kWh/an: grande entreprise, puissance max.: 1630 kW, courant moyenne tension, propre station de transformation


# Possible activity types from simulation.xml
residential_types = ['1']
activity_types = {
    "1": "Residential", 
    "2": "Office", 
    "3": "Garage", 
    "4": "Commercial", 
    "5": "Restaurant", 
    "6": "Hotel", 
    "7": "Hospital", 
    "8": "Education", 
    "9": "Industry", 
    "10": "Other", 
}

residential_consumptions = [0, 1600, 2500, 4500, 4500, 7500, 7500, 13_000, 25_000]
residential_labels = ['H1', 'H2', 'H3', 'H4', 'H5', 'H8', 'H7', 'H6']
other_consumptions = [8000, 30_000, 150_000, 500_000, 500_000, 1_500_000, 7_500_000]
other_labels = ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7']

def get_category(value:float, upper_bounds:List[float], labels:List[str])->str:
    index = bisect.bisect_right(upper_bounds, value)
    if index >= len(labels):
        return "Out of range"
    return labels[index]

def is_residential_consumption(activity_type:str)->bool:
    if activity_type in residential_types:
        return True
    return False

def get_consumption_category(activity_type:str, consumption:float)->str:
    consumption_limits = other_consumptions
    consumption_labels = other_labels
    dummy_resullt = "C2"
    if is_residential_consumption(activity_type):
        consumption_limits = residential_consumptions
        consumption_labels = residential_labels
        dummy_result = "H4"
    # return get_category(consumption, consumption_limits, consumption_labels)
    return dummy_result

class ElectricityPricer:
    def __init__(self):
        self.municipality_listings = pd.read_csv(INPUT_PATH+MUNICIPALITIES_FILE)
        self.tarifs_listings = pd.read_csv(INPUT_PATH+TARIFS_FILE)

    def get_municipality_entries(self, municipality:str)->DataFrame:
        filtered_df = self.municipality_listings[self.municipality_listings['municipalityName'] == municipality]
        return filtered_df

    def get_municipality_provider(self, municipality:str)->str:
        municipality_entries = self.get_municipality_entries(municipality)
        operator = municipality_entries['operator'].to_list()[0]
        return operator
        # column_list = ['column_name'].tolist()

    def get_electricity_price(self, municipality:str, price_category:str)->float:
        operator = self.get_municipality_provider(municipality)
        operator_entries = self.tarifs_listings[(self.tarifs_listings[' operatorLabel'] == operator) & (self.tarifs_listings[' category'] == price_category)]
        operator_entries.sort_values(by=' total (cts./kWh)')
        return float(operator_entries.iloc[1][' total (cts./kWh)'])

if __name__ == '__main__':
    pricer = ElectricityPricer()
    # print(pricer.municipality_listings.head())
    # print(pricer.tarifs_listings.head())
    # print(pricer.get_municipality_entries("Val de Bagnes").head())
    operator = pricer.get_municipality_provider("Val de Bagnes")
    print(operator)
    # print(pricer.tarifs_listings.keys())
    # operator_entries = pricer.tarifs_listings[pricer.tarifs_listings[' operatorLabel'] == operator]
    # print(operator_entries)
    print(pricer.get_electricity_price('Val de Bagnes', 'C2'))