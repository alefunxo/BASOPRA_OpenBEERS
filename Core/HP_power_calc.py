# Copyright © 2025 HES-SO Valais-Wallis <alejandro.penabello@hevs.ch>
# SPDX-FileContributor: Alejandro Penabello <alejandro.penabello@hevs.ch>
# SPDX-FileContributor: Lucien Troillet <lucien.troillet@hevs.ch>
#
# SPDX-License-Identifier: Apache-2.0

import sys
import os
import traceback

import pandas as pd
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config.loader import config
from utils.utils import pickle_load, dataframe_save

def get_simulation_hp_data(simulation_extraction_dir:str):
    building_extraction_files = os.listdir(simulation_extraction_dir)
    buildings_loaded_data = [
        pickle_load(os.path.join(simulation_extraction_dir, bf))
        for bf in building_extraction_files
    ]
    buildings_data = {
        next(iter(bd.keys())): next(iter(bd.values()))
        for bd in buildings_loaded_data
    }
    tot_hp_capacity = 0
    for b in buildings_data.values():
        b_hp = b.get('heat_pump')
        if b_hp:
            hp_capacity = b_hp.attributes.hp
            tot_hp_capacity += hp_capacity
    return tot_hp_capacity

def get_hp_power():
    hp_pkl_dir = config.simulation_extraction_dir
    extraction_files = os.listdir(hp_pkl_dir)
    extraction_dirs = [
        f for f in extraction_files 
        if not os.path.isfile(os.path.join(hp_pkl_dir, f))
        and 'sierre' in f
        and 'noHP' not in f
    ]
    hp_per_sim = {
        'simulation': [],
        'hp_capacity': [],
    }
    for d in extraction_dirs:
        tot_hp_capacity = get_simulation_hp_data(os.path.join(hp_pkl_dir, d))
        hp_per_sim['simulation'].append(d)
        hp_per_sim['hp_capacity'].append(tot_hp_capacity)
    df = pd.DataFrame.from_dict(hp_per_sim, orient='index')
    dataframe_save(os.path.join(config.output_dir, 'hp_power.csv'), df.T)


if __name__ == "__main__":
    get_hp_power()