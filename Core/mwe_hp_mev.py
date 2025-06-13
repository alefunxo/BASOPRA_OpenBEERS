"""
This script defines a minimum working example and defines
the input data required for running an energy optimization model.
The data includes configuration parameters, time settings, energy demand and supply,
pricing, battery storage, EV charging, and thermal storage properties.

Data Structure:
---------------
- conf (list[bool]): Flags for enabling/disabling components in the optimization:
    - E_storage (bool): Enable/disable electrical storage.
    - heating (bool): Enable/disable heating system.
    - T_storage (bool): Enable/disable thermal storage.
    - DHW (bool): Enable/disable domestic hot water system.

- Time & Simulation Parameters:
    - Set_declare (set): Time indices for optimization.
    - delta_t (int): Time step resolution (e.g., hourly).
    - dayofyear (int): Specifies the simulation day (valid range: 120-274).
    - toy (int): Indicator affecting conditional model branching.

- Energy Supply & Demand:
    - E_PV (dict[int, float]): Solar power generation profile (kW) for each time step.
    - E_demand (dict[int, float]): Household electricity consumption (kW) per time step.
    - Req_kWh (dict[int, float]): Space heating energy demand (kWh).
    - Req_kWh_DHW (dict[int, float]): Domestic hot water energy demand (kWh).
    - hp_sh_cons, hp_tank_cons, hp_dhw_cons (dict[int, float]): Available power for heat pumps (kW).
    - Temp_supply (dict[int, float]): Supply temperature for heating (K).
    - Set_T (dict[int, float]): Target room temperature (K).
    - COP_SH, COP_DHW, COP_tank (dict[int, float]): Coefficients of performance for heat pumps.

- Electricity Pricing:
    - retail_price (dict[int, float]): Electricity purchase price (€/kWh).
    - Export_price (dict[int, float]): Revenue from selling electricity to the grid (€/kWh).
    - Capacity_tariff (float): Cost associated with peak power usage (€/kW).
    - public_charging_price (float): Cost of charging an EV at a public station (€/kWh).

- Battery Storage Parameters:
    - Batt (object): Battery model containing capacity and efficiency properties.
    - Converter_Efficiency_Batt (float): Efficiency of battery charge/discharge cycles.
    - SOC_max (float): Maximum state of charge (SOC) for battery storage.
    - Max_inj (float): Maximum allowable grid injection power (kW).
    - Inv_power (float): Inverter power capacity (kW).
    - Inverter_eff (float): Efficiency of the inverter.

- EV Charging & V2G Parameters:
    - Batt_EV- conf (list[bool]): Flags for enabling/disabling components in the optimization:
    - E_storage (bool): Enable/disable electrical storage.
    - heating (bool): Enable/disable heating system.
    - T_storage (bool): Enable/disable thermal storage.
    - DHW (bool): Enable/disable domestic hot water system.

- Time & Simulation Parameters:
    - Set_declare (set): Time indices for optimization.
    - delta_t (int): Time step resolution (e.g., hourly).
    - dayofyear (int): Specifies the simulation day (valid range: 120-274).
    - toy (int): Indicator affecting conditional model branching.

- Energy Supply & Demand:
    - E_PV (dict[int, float]): Solar power generation profile (kW) for each time step.
    - E_demand (dict[int, float]): Household electricity consumption (kW) per time step.
    - Req_kWh (dict[int, float]): Space heating energy demand (kWh).
    - Req_kWh_DHW (dict[int, float]): Domestic hot water energy demand (kWh).
    - hp_sh_cons, hp_tank_cons, hp_dhw_cons (dict[int, float]): Available power for heat pumps (kW).
    - Temp_supply (dict[int, float]): Supply temperature for heating (K).
    - Set_T (dict[int, float]): Target room temperature (K).
    - COP_SH, COP_DHW, COP_tank (dict[int, float]): Coefficients of performance for heat pumps.

- Electricity Pricing:
    - retail_price (dict[int, float]): Electricity purchase price (€/kWh).
    - Export_price (dict[int, float]): Revenue from selling electricity to the grid (€/kWh).
    - Capacity_tariff (float): Cost associated with peak power usage (€/kW).
    - public_charging_price (float): Cost of charging an EV at a public station (€/kWh).

- Battery Storage Parameters:
    - Batt (object): Battery model containing capacity and efficiency properties.
    - Converter_Efficiency_Batt (float): Efficiency of battery charge/discharge cycles.
    - SOC_max (float): Maximum state of charge (SOC) for battery storage.
    - Max_inj (float): Maximum allowable grid injection power (kW).
    - Inv_power (float): Inverter power capacity (kW).
    - Inverter_eff (float): Efficiency of the inverter.

- EV Charging & V2G Parameters:
    - Batt_EV (object): Electric vehicle battery model.
    - SOC_max_EV (float): Maximum SOC for EV battery.
    - E_EV_start (float): Initial stored energy in the EV battery (kWh).
    - EV_P_max_home, EV_P_max_away (float): Max charging power at home/away (kW).
    - EV_V2G (bool): Flag for enabling/disabling vehicle-to-grid (V2G) functionality.
    - EV_home, EV_away (dict[int, bool]): Defines EV availability at home/away over time.
    - E_EV_trip (dict[int, float]): Energy required for EV trips (kWh).
    - EV_minSOC (float): Minimum SOC level for EV to ensure usability.

- Thermal Storage:
    - tank_dhw, tank_sh (object): Storage models for domestic hot water and space heating.
    - T_aux_supply (dict[int, float]): Auxiliary supply temperature for heating (K).
    - T_init (float): Initial storage temperature (K).
    - Backup_heater (float): Backup heating power capacity (kW). (object): Electric vehicle battery model.
    - SOC_max_EV (float): Maximum SOC for EV battery.
    - E_EV_start (float): Initial stored energy in the EV battery (kWh).
    - EV_P_max_home, EV_P_max_away (float): Max charging power at home/away (kW).
    - EV_V2G (bool): Flag for enabling/disabling vehicle-to-grid (V2G) functionality.
    - EV_home, EV_away (dict[int, bool]): Defines EV availability at home/away over time.
    - E_EV_trip (dict[int, float]): Energy required for EV trips (kWh).
    - EV_minSOC (float): Minimum SOC level for EV to ensure usability.

- Thermal Storage:
    - tank_dhw, tank_sh (object): Storage models for domestic hot water and space heating.
    - T_aux_supply (dict[int, float]): Auxiliary supply temperature for heating (K).
    - T_init (float): Initial storage temperature (K).
    - Backup_heater (float): Backup heating power capacity (kW).

This dataset serves as input for the energy optimization model, ensuring a structured representation
of energy flows, cost parameters, and operational constraints.
"""
import pyomo.environ as en
from pyomo.opt import SolverFactory
import paper_classes as pp
import LP_mEV as LP

import matplotlib.pyplot as plt
import pandas as pd
from pyomo.core import Var

import threading
import numpy as np
import os
import csv
def Get_output(instance):
    

    # 1) Dump raw rows
    lock = threading.Lock()
    while lock.locked():
        pass
    lock.acquire()
    fname = f"out{np.random.randint(1,1e9)}.csv"
    with open(fname, 'w', newline='') as f:
        writer = csv.writer(f, delimiter=';')
        for v in instance.component_objects(Var, active=True):
            varobj = getattr(instance, str(v))
            for idx in varobj:
                writer.writerow([idx, varobj[idx].value, str(v)])
    lock.release()

    # 2) Read back
    df = pd.read_csv(
        fname, sep=';', names=['index','val','var'], dtype={'index': str}
    )
    os.remove(fname)

    # 3) Parse index strings into Python objects
    def parse_idx(s):
        try:
            return eval(s)
        except:
            return s  # fallback

    parsed = df['index'].apply(parse_idx)

    # 4) Split into ev and time
    def split_idx(x):
        if isinstance(x, tuple) and len(x) == 2:
            return x[0], x[1]
        elif isinstance(x, tuple) and len(x) == 1:
            return None, x[0]
        else:
            # not a tuple: assume 1-D var over time
            return None, x

    ev_time = parsed.apply(split_idx)
    df['ev']   = ev_time.apply(lambda t: t[0])
    df['time'] = ev_time.apply(lambda t: t[1])

    # 5) Pivot into wide form
    pivot = df.pivot_table(
        index='time',
        columns=['var','ev'],
        values='val',
        aggfunc='first'
    )

    # 6) Flatten column names
    pivot.columns = [
        f"{var}_{ev}" if ev is not None else var
        for var, ev in pivot.columns
    ]

    pivot = pivot.sort_index()

    # 7) Extract P_max_day if present
    P_max = getattr(instance, 'P_max_day', None)

    return pivot, P_max

# -- Create two EV battery instances --
batt = pp.Battery_tech(Capacity=10, Technology='NMC')
EV_Batt1 = pp.Battery_tech(Capacity=75, Technology='NMC')
EV_Batt2 = pp.Battery_tech(Capacity=60, Technology='NMC')
EV_Batt3 = pp.Battery_tech(Capacity=20, Technology='NMC')
EV_Batt4 = pp.Battery_tech(Capacity=120, Technology='NMC')
EV_Batt5 = pp.Battery_tech(Capacity=80, Technology='NMC')


# -- Thermal tank instances --
tank_dhw = pp.heat_storage_tank(mass=100, surface=0.41)
tank_dhw.t_max = 333.15
tank_dhw.t_min = 293.15

tank_sh = pp.heat_storage_tank(mass=1000, surface=0.41)
tank_sh.U_value = 0.5
tank_sh.specific_heat = 0.00116

# -- Time set from -1 to 23 --
time_set = list(range(-1, 24))
# -- Define EV list and single battery instance --
EV_list = ['EV1', 'EV2','EV3', 'EV4','EV5']
Batt_EV = {
    'EV1': EV_Batt1,
    'EV2': EV_Batt2,
    'EV3': EV_Batt3,
    'EV4': EV_Batt4,
    'EV5': EV_Batt5,
}
# -- Build Data dictionary for one EV --
Data = {
    'conf': [False, True, False, False],
    'Set_declare': time_set,
    'delta_t': 1,
    'dayofyear': 150,
    'toy': 0,
    'App_comb_mod': [0, 1, 1, 0],
    'retail_price': {t: 0.2 for t in range(24)},
    'E_PV': {t: 10 if 8 <= t <= 16 else 0.0 for t in range(24)},
    'E_demand': {t: 1 for t in range(24)},
    'Export_price': {t: 0.09 for t in range(24)},
    'Capacity_tariff': 5,
    'Inverter_power': 7,
    'Inverter_efficiency': 0.95,
    'Converter_efficiency_batt': 0.98,
    'Max_inj': 5,
    'Batt': batt,
    'Req_kWh': {t: 5 for t in range(24)},
    'Req_kWh_DHW': {t: 2 for t in range(24)},
    'hp_sh_cons': {t: 100 for t in range(24)},
    'hp_tank_cons': {t: 100 for t in range(24)},
    'hp_dhw_cons': {t: 100 for t in range(24)},
    'Temp_supply': {t: 303.82 for t in range(24)},
    'Set_T': {t: 293.15 for t in range(24)},
    'COP_SH': {t: 4.0 for t in range(24)},
    'COP_DHW': {t: 4.0 for t in range(24)},
    'COP_tank': {t: 4.0 for t in range(24)},
    'T_aux_supply': {t: 333.15 for t in range(24)},
    'tank_dhw': tank_dhw,
    'T_init': 293.15,
    'tank_sh': tank_sh,
    'Backup_heater': 100,
    'SOC_max': batt.SOC_max,

    # -- EV parameters indexed by EV --
    'EV_list': EV_list,
    'Batt_EV': Batt_EV,

    # maximum SOC per EV
    'SOC_max_EV':   { ev: Batt_EV[ev].SOC_max    for ev in EV_list },

    # initial SOC (10% of capacity for all EVs)
    'E_EV_start':   { ev: Batt_EV[ev].Capacity * 1 for ev in EV_list },

    # home/away charging power limits
    'EV_P_max_home':{ ev: 7   for ev in EV_list },
    'EV_P_max_away':{ ev: 22  for ev in EV_list },

    # V2G enabled for all
    'EV_V2G':       { ev: 1   for ev in EV_list },

    # availability at home (1) vs away (0)
    'EV_home': {
        ev: { t: 1 if not (8 <= t <= 12) else 0
              for t in range(24) }
        for ev in EV_list
    },
    'EV_away': {
        ev: { t: 1 if   8 <= t <= 12 else 0
              for t in range(24) }
        for ev in EV_list
    },

    # trip energy consumption (5 kWh during away hours)
    'E_EV_trip': {
        ev: { t: 5 if   8 <= t <= 12 else 0
              for t in range(24) }
        for ev in EV_list
    },

    # common across all EVs
    'public_charging_price': 0.5,
    'EV_minSOC':           0.5
}

# -- Instantiate and solve --
model = LP.Concrete_model(Data)
'''
from pyomo.environ import SolverFactory
for v in model.component_data_objects(en.Var, active=True):
    if v.lb == 0 and v.ub == -30:
        print("Offender:", v.name)
solver = SolverFactory('gurobi_persistent')
solver.set_instance(model)

# solve without loading solutions
solver.solve(load_solutions=False)

# now you can call computeIIS() on the underlying Gurobi model
solver._solver_model.computeIIS()
solver._solver_model.write("infeasible.ilp")'''
solver = SolverFactory('gurobi')
result = solver.solve(model, tee=True)
result.write(num=1)


# -- Extract outputs --
df, P_max = Get_output(model)
# Optionally concatenate additional data
additional = pd.DataFrame({
    'E_demand': Data['E_demand'],
    'Export_price': Data['Export_price'],
    'retail_price': Data['retail_price'],
    **{
        f"E_EV_trip_{ev}": Data['E_EV_trip'][ev]
        for ev in Data['EV_list']
    }
})
df = pd.concat([df, additional], axis=1)

df.to_csv('test_mwe_24h_twoEVs.csv')
# -- Print summary --
print("Objective value:", en.value(model.total_cost))
for t in sorted(model.Time):
    prints = [f"Hour {t}:"]
    prints.append(f"Grid cons = {en.value(model.E_cons[t]):.3f} kWh")
    for ev in EV_list:
        soc = en.value(model.SOC_EV[ev, t]) if (ev, t) in model.SOC_EV.index_set() else None
        char_away = en.value(model.E_char_away[ev, t])
        char_home = en.value(model.E_char_EV[ev, t])
        prints.append(f"{ev} SOC = {soc:.3f}")
        prints.append(f"{ev} Away‐charge = {char_away:.3f} kWh")
        prints.append(f"{ev} Home‐charge = {char_home:.3f} kWh")
    print(', '.join(prints))

# -- Plot EV SOC for both vehicles --
print(df.head())
plt.figure(figsize=(8, 4))
for ev in EV_list:
    plt.plot(df[f'SOC_EV_{ev}'], label=f"SOC {ev}")
plt.title('EV State of Charge')
plt.ylabel('kWh')
plt.xlabel('Hour')
plt.legend()
plt.show()
