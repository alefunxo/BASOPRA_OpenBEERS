import pyomo.environ as en
from pyomo.opt import SolverFactory
import paper_classes as pp
import LP as LP
from Core_LP import Get_output


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
# In this example heating is active but without thermal storage and DHW.
Data = {
    'conf': [True, True, True, True],  # [E_storage, heating, T_storage, DHW]


    'Set_declare': time_set,
    'delta_t': 1,
    'dayofyear': 150,  # within 120-274
    'toy': 0,  # a value not equal to 1,2,3 to take the "else" branch when needed
    
    'App_comb_mod': [0, 1, 0, 0],  # [PVAC, PVSC, DLS, DPS]
    'retail_price': {t: 0.2 for t in range(24)},
    'E_PV': {t: 10 if 8 <= t <= 16 else 0.0 for t in range(24)},
    'E_demand': {t: 1 for t in range(24)},
    'Export_price': {t: 0.09 for t in range(24)},
    'Capacity_tariff': 0.05,
    'Inv_power': 10,
    'Inverter_eff': 0.95,
    'Converter_Efficiency_Batt': 0.98,
    'Max_inj': 100,
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

}


# Import the Concrete_model function from your script.
# It is assumed that the provided script with Concrete_model and all constraints is in scope.
model = LP.Concrete_model(Data)

# Create and run the solver (using GLPK as an example)

solver = SolverFactory('gurobi')
result = solver.solve(model, tee=True)
result.write(num=1)
[df_1,P_max]=Get_output(model)
df_1.to_csv('test_mwe_hp_24h.csv')

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

import matplotlib.pyplot as plt

# Extract data for plotting
times_grid = [t for t in model.Time if t in model.E_cons]
grid_values = [en.value(model.E_cons[t]) for t in times_grid]
demand_values = [en.value(model.E_demand_el[t]) for t in times_grid]

pv_inj_values = [en.value(model.E_PV_grid[t]) for t in times_grid]
pv_values = [en.value(model.E_PV[t]) for t in times_grid]

soc_values = [en.value(model.SOC[t]) for t in times_grid]

hp_values = [en.value(model.E_hp[t]) for t in times_grid]
hpdhw_values = [en.value(model.E_hpdhw[t]) for t in times_grid]
bu_values = [en.value(model.E_bu[t]) for t in times_grid]

budhw_values = [en.value(model.E_budhw[t]) for t in times_grid]
q_ts_values = [en.value(model.Q_ts[t]) for t in times_grid]

req_kWh_values = [en.value(model.Req_kWh[t]) for t in times_grid]
req_kWh_DHW_values = [en.value(model.Req_kWh_DHW[t]) for t in times_grid]

# Create a 2x2 subplot figure
fig, axs = plt.subplots(2, 3, figsize=(10, 8))

axs[0, 0].plot(times_grid, grid_values, label='grid')
axs[0, 0].plot(times_grid, demand_values, label='demand')

axs[0, 0].plot(times_grid, pv_values, label='PV')
axs[0, 0].set_title("demand and gen")
axs[0, 0].set_xlabel("Hour")
axs[0, 0].set_ylabel("Consumption (kWh)")
axs[0, 0].legend()

axs[0, 1].plot(times_grid, pv_inj_values, label='injection')
axs[0, 1].plot(times_grid, hp_values, label='hp')
axs[0, 1].plot(times_grid, hpdhw_values, label='hp_dhw')
axs[0, 1].set_title("hp and injection")

axs[0, 1].set_xlabel("Hour")
axs[0, 1].set_ylabel("Injection (kWh)")
axs[0, 1].legend()

axs[1, 0].plot(times_grid, soc_values, label='soc')
axs[1, 0].set_title("Battery SOC")
axs[1, 0].set_xlabel("Hour")
axs[1, 0].set_ylabel("SOC")
axs[1, 0].legend()

axs[1, 1].plot(times_grid, req_kWh_values, label='heat demand')
axs[1, 1].plot(times_grid, req_kWh_DHW_values, label='DHW demand')

axs[1, 1].set_title("Heat demand")
axs[1, 1].set_xlabel("Hour")
axs[1, 1].set_ylabel("Energy (kWh)")
axs[1, 1].legend()

axs[0, 2].plot(times_grid, q_ts_values, label='Thermal SOC')

axs[0, 2].plot(times_grid, bu_values, label='backup heater' )
axs[0, 2].set_title("backup")

axs[0, 2].set_xlabel("Hour")
axs[0, 2].set_ylabel("Energy (kWh)")
axs[0, 2].legend()

axs[1, 2].plot(times_grid, budhw_values, label='DHW backup heater')

axs[1, 2].plot(times_grid, bu_values, label='backup heater' )

axs[1, 2].set_xlabel("Hour")
axs[1, 2].set_ylabel("Energy (kWh)")
axs[1, 2].legend()

plt.legend()

plt.tight_layout()
plt.show()
pass