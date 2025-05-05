m.Balance_hp_demand_r=en.Constraint(m.Time,rule=Balance_hp_demand_rule)
m.Balance_space_heat_demand_r=en.Constraint(m.Time,
								rule=Balance_space_heat_demand)
m.Balance_hp_supply_r=en.Constraint(m.Time,rule=Balance_hp_supply_rule)#*


m.def_ts_state_r=en.Constraint(m.tm,rule=def_ts_state_rule)
m.Ts_losses_r=en.Constraint(m.Time,rule=Ts_losses)
m.Change_tank_thermal_energy_rule_r=en.Constraint(m.Time,rule=Change_tank_thermal_energy_rule)
m.Available_tank_thermal_energy_rule_r=en.Constraint(m.Time,rule=Available_tank_thermal_energy_rule)






def Balance_hp_demand_rule(m,i):
    '''
    Description
    -------
    Balance demand HP1 in electricity terms (HP consumption = Electricity from PV, battery and grid). Constraint for E_hp if heating and for E_hp_cooling if cooling. Constraint is desactivated if no heating.
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.Cooling==False:
            return (m.E_hp[i],m.E_PV_hp[i]+m.E_batt_hp[i]+m.E_grid_hp[i])
        else:
            return (m.E_hp_cooling[i],m.E_PV_hp[i]+m.E_batt_hp[i]+m.E_grid_hp[i])


def Balance_space_heat_demand(m,i):
    '''
    Description
    -------
    Balance demand in heating terms (heat production [kWh] = heat demand). Constraint changes on production side, if there is thermal storage, cooling or heating. In the demand side is always the required energy in thermal terms.
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.T_storage==False:
                return(m.Q_hp_sh[i],m.Req_kWh[i])
        else:
            if m.Cooling==False:
                return(m.Q_ts_sh[i],m.Req_kWh[i])
            else:
                return(-m.Q_ts_sh[i],m.Req_kWh[i])


def Balance_hp_supply_rule2(m,i):
    '''
    Description
    -------
    Balance supply DHWST (storage tank for DHW) in thermal terms (HP supply (backup heater included) = heat supplied to the DHWST). Skip if not DHW.
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.DHW==False:
            return en.Constraint.Skip
        else:
            return ((m.E_hp2[i])*m.COP_DHW[i]+m.E_bu2[i],((m.T_dhwst[i]-m.T_dhwst[i-1])*m.m_dhw*m.c_p_dhw)+m.Q_dhwst_hd[i]+m.Q_loss_dhwst[i])#Q_char

def Balance_hp_supply_rule(m,i):
    '''
    Description
    -------
    Balance of thermal energy supplied by the HP and the backup heater according to the COP. If there is no storage the electricity consumed by the HP times the COP plus the electricity consumed by the backup heater times the COP of the backup heater (i.e. 1) must be equal to the heat provided for space heating (or cooling).
    If there is storage, the electricity supplied times COP must be equal to the delta Q supplied to the tank plus the heat provided for space heating (cooling) plus the losses of the tank. It can be assimiled as Q_char. For cooling signs and COP change.

    TODO
    -------
    Change COP_SH for cooling by COP for cooling (parameter).
    Finish the transitions and the no heating periods
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.T_storage==False:
            if m.Cooling==False:
                return((m.E_hp[i])*m.COP_SH[i]+m.E_bu[i],(m.Q_hp_sh[i]))
            else:
                return((m.E_hp_cooling[i])*(m.COP_SH[i]-1),(m.Q_hp_sh[i]))
        else:
            if m.Cooling==False:
                if m.toy==0:
                    #heating season
                    return ((m.E_hp[i])*m.COP_SH[i]+m.E_bu[i],m.Q_ts_delta[i]+m.Q_ts_sh[i]+m.Q_loss_ts[i])
                elif m.toy==1:
                    #transition towards no heating
                    return ((m.E_hp[i])*m.COP_SH[i]+m.E_bu[i],0)
                elif m.toy==2:
                    #No heating
                    return ((m.E_hp[i])*m.COP_SH[i]+m.E_bu[i],0)
                elif m.toy==3:
                    #transition towards heating Have to increase the tank temp up to 40C
                    return en.Constraint.Skip
            else:
                #Si hay cooling el tanque debe bajar a 20 grados y moverse entre 10 y 20 durante el verano.
                if m.toy==0:
                    #heating season
                    return ((m.E_hp[i])*m.COP_SH[i]+m.E_bu[i],m.Q_ts_delta[i]+m.Q_ts_sh[i]+m.Q_loss_ts[i])
                elif m.toy==1:
                    #transition towards no heating
                    return ((m.E_hp_cooling[i])*(m.COP_SH[i]-1),m.Q_ts_delta[i]-m.Q_ts_sh[i]+m.Q_loss_ts[i])
                elif m.toy==2:
                    #Cooling season
                    return ((m.E_hp_cooling[i])*(m.COP_SH[i]-1),m.Q_ts_delta[i]-m.Q_ts_sh[i]+m.Q_loss_ts[i])
                elif m.toy==3:
                    #transition towards heating
                    return en.Constraint.Skip


def def_ts_state_rule(m, t):
    '''
    Description
    -------
    Temperature of the tank must be lower than T_min (??) when cooling
    TODO
    -------
    It is needed. Adjust nomenclature
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.T_storage==False:
            return en.Constraint.Skip
        else:
            if t==-1:
                return(m.T_ts[t],m.T_init)
            else:
                if m.Cooling==False:
                    return en.Constraint.Skip
                else:
                    return en.Constraint.Skip
                    #return(m.T_ts[t]<=m.T_min)


def Ts_losses(m,i):
    '''
    Description
    -------
    Calcultes tank losses as a function of the temperature difference between the tank and the room temperature (Set_T) times the U_value, the tank surface and delta t (since losses are per hour).
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.T_storage==False:
            return en.Constraint.Skip
        else:
            if i==0:
                return(m.Q_loss_ts[i],0)
            else:
                if m.Cooling==False:
                    return(m.Q_loss_ts[i],m.dt*m.U*m.A*(m.T_ts[i]-(m.Set_T[i])))
                else:
                    return(m.Q_loss_ts[i],m.dt*m.U*m.A*(m.T_ts[i]-(m.Set_T[i])))


def Change_tank_thermal_energy_rule(m,i):
    '''
    Description
    -------
    Change in tank thermal energy (Q_ts_delta [kWh]) is given by the change in tank temperature times the mass times the specific heat of water.
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.T_storage==False:
                return en.Constraint.Skip
        else:
            if m.Cooling==False:
                return(m.Q_ts_delta[i],((m.T_ts[i]-m.T_ts[i-1])*m.m*m.c_p))
            else:
                return(m.Q_ts_delta[i],(-(m.T_ts[i]-m.T_ts[i-1])*m.m*m.c_p))


def Available_tank_thermal_energy_rule(m,i):
    '''
    Description
    -------
    Thermal energy available in the tank (Q_ts [kWh]) is given by the temperature of the tank at time t (T_ts) and the minimum temperature accepted in the tank (T_min) times the mass times the specific heat of water. If cooling T_min is 293.15 K (20°C).
    TODO
    -------
    Check if toy is needed here.
    '''
    if m.heating==False:
        return en.Constraint.Skip
    else:
        if m.T_storage==False:
                return en.Constraint.Skip
        else:
            if m.Cooling==False:
                return(m.Q_ts[i],((m.T_ts[i]-m.T_min)*m.m*m.c_p))
            else:
                return(m.Q_ts_cooling[i],((m.T_ts[i]-(273.15+20))*m.m*m.c_p))
