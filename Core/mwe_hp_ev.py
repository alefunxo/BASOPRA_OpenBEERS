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
import LP_EV as LP
from Core import Get_output
import matplotlib.pyplot as plt
import pandas as pd


# Create instances with minimal values
batt = pp.Battery_tech(Capacity=10,Technology='NMC')
EV_Batt= pp.Battery_tech(Capacity=75,Technology='NMC')


tank_dhw = pp.heat_storage_tank(mass=100, surface=0.41)
tank_dhw.t_max = 333.15  # K
tank_dhw.t_min = 293.15  # K

tank_sh = pp.heat_storage_tank(mass=1000, surface=0.41)
tank_sh.U_value = 0.5      # kW/(m²·K)
tank_sh.specific_heat = 0.00116  # kWh/(K·L)


# Create a time set from -1 to 23 (with -1 as the initial condition)
time_set = list(range(-1, 24))

# Build the Data dictionary with minimal parameters for a full day.
# In this example storage, heating and DHW are active but without thermal storage .
Data = {
    'conf': [False, True, False, False],  # [E_storage, heating, T_storage, DHW]


    'Set_declare': time_set,
    'delta_t': 1,
    'dayofyear': 150,  # within 120-274
    'toy': 0,  # a value not equal to 1,2,3 to take the "else" branch when needed
    
    'App_comb_mod': [0, 1, 1, 0],  # [PVAC, PVSC, DLS, DPS]
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
    'hp_sh_cons': {t: 100 for t in range(24)},  # available power for space heating
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
    'SOC_max':batt.SOC_max,

    'E_EV_start':EV_Batt.Capacity*.1,# max the Capacity of the Batt
    'Batt_EV': EV_Batt,
    'SOC_max_EV':EV_Batt.SOC_max,
    'finalEnergyStoredValuation':1, # not important yet
    'EV_P_max_home':7, # kW
    'EV_P_max_away':22, # kW
    'EV_V2G':1,
    'EV_home':{t: 1 if not (8 <= t <= 12) else 0.0 for t in range(24)},
    'EV_away':{t: 1 if 8 <= t <= 12 else 0.0 for t in range(24)},
    'E_EV_trip':{t: 5 if 8 <= t <= 12 else 0.0 for t in range(24)}, #kWh consomption of the EVs
    'public_charging_price':0.5,
    'EV_minSOC':0.5,
}


# Import the Concrete_model function from your script.
# It is assumed that the provided script with Concrete_model and all constraints is in scope.
model = LP.Concrete_model(Data)

# Create and run the solver (using GLPK as an example)

solver = SolverFactory('gurobi')
result = solver.solve(model, tee=True)
result.write(num=1)
[df,P_max]=Get_output(model)
df_1 = pd.DataFrame({'E_demand': Data['E_demand'],'EV_away': Data['EV_away'],
    'EV_home': Data['EV_home'],'E_PV': Data['E_PV'],'Export_price': Data['Export_price'],
    'retail_price': Data['retail_price']})

df = pd.concat([df, df_1], ignore_index=True)

df.to_csv('test_mwe_24h.csv')

# Display a few results: objective value, grid consumption, PV injection, and battery SOC.
print("Objective value:", en.value(model.total_cost))
for t in sorted(model.Time):
    demand = en.value(model.E_demand_el[t])
    pv = en.value(model.E_PV[t])

    pv_inj = en.value(model.E_PV_grid[t])
 
    grid_cons = en.value(model.E_cons[t])
    # Battery SOC is defined over m.tm (which includes the initial time -1)
    soc = en.value(model.SOC[t]) if t in model.SOC else None
    E_hp = en.value(model.E_hp[t]) if t in model.E_hp else None
    print(f"Hour {t}: Grid consumption = {grid_cons:.3f} kWh, PV production = {pv:.3f} kWh, Battery SOC = {soc:.3f}, E_hp = {E_hp:.3f}")


# Assume df is your DataFrame containing the columns
fig, axs = plt.subplots(3, 3, figsize=(18, 18), constrained_layout=True)
axs = axs.flatten()

# Subplot 1: Main PV Production (usage and curtailment)
axs[0].plot(df['E_PV_load'], label='PV Load')
axs[0].plot(df['E_PV_grid'], label='PV Grid Injection')
axs[0].plot(df['E_PV_curt'], label='PV Curtailment')
axs[0].set_title('Main PV Production')
axs[0].set_ylabel('kWh')	
axs[0].legend()

# Subplot 2: PV Allocation to Battery and HP
axs[1].plot(df['E_PV_batt'], label='PV to Battery')
axs[1].plot(df['E_PV_batt_EV'], label='PV to EV')

axs[1].plot(df['E_PV_hp'], label='PV to Heat Pump')

axs[1].set_title('PV to EV,Batt and HP')
axs[1].set_ylabel('kWh')	
axs[1].legend()

# Subplot 3: Battery Operation (non-EV)
axs[2].plot(df['E_char'], label='Battery Charge')
axs[2].plot(df['E_dis'], label='Battery Discharge')
axs[2].plot(df['SOC'], label='Battery SOC')
axs[2].set_title('Battery Operation')
axs[2].set_ylabel('kWh')
axs[2].legend()

# Subplot 4: EV-Related Flows
axs[3].plot(df['E_batt_EV_load'], label='EV Load')
axs[3].plot(df['E_char_EV'], label='EV Charge')
axs[3].plot(df['E_dis_EV'], label='EV Discharge')
axs[3].plot(df['SOC_EV'], label='EV SOC')
axs[3].set_title('EV Flows')
axs[3].set_ylabel('kWh')
axs[3].legend()

# Subplot 5: Grid Interaction
axs[4].plot(df['E_cons'], label='Grid Consumption')
axs[4].plot(df['E_grid_batt'], label='Grid to Battery')
axs[4].plot(df['E_grid_load'], label='Grid to Load')
axs[4].set_title('Grid Interaction')
axs[4].set_ylabel('kWh')
axs[4].legend()

# Subplot 6: Heat Pump Performance
axs[5].plot(df['E_hp'], label='HP Energy')
axs[5].plot(df['E_hpdhw'], label='HP DHW Energy')
axs[5].set_title('Heat Pump Performance')
axs[5].set_ylabel('kWh')
axs[5].legend()

# Subplot 7: Backup Heater Flows
axs[6].plot(df['E_bu'], label='Backup Heater')
axs[6].plot(df['E_budhw'], label='Backup DHW')
axs[6].set_title('Backup Heater Flows')
axs[6].set_ylabel('kWh')
axs[6].legend()

# Subplot 8: Thermal Temperatures
axs[7].plot(df['T_ts'], label='Tank Temperature')
axs[7].plot(df['T_dhwst'], label='DHW Tank Temperature')
axs[7].set_title('Thermal Temperatures')
axs[7].set_ylabel('K')
axs[7].legend()

# Subplot 9: Thermal Energy Flows
axs[8].plot(df['Q_hp_sh'], label='HP Space Heating')
axs[8].plot(df['Q_hp_ts'], label='HP Tank Charging')
axs[8].plot(df['Q_dhwst_hd'], label='DHW Demand Heating')
axs[8].set_title('Thermal Energy Flows')
axs[8].set_ylabel('kWh')
axs[8].legend()

plt.tight_layout()
plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05, wspace=0.3, hspace=0.4)

plt.show()
pass