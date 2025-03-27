# -*- coding: utf-8 -*-
## @namespace graphs
# Created on Wed Feb 28 09:47:22 2018
# Author
# Alejandro Pena-Bello
# alejandro.penabello@unige.ch
# Script used to plot the results for the paper Optimization of PV-coupled battery systems for combining applications: impact of battery technology and location (Pena-Bello et al 2018 to be published).
# The script works in Linux and Windows
# INPUTS
# ------
# OUTPUTS
# -------
# TODO
# ----
# User Interface, including path to save the results and choose countries, load curves, etc.
# Requirements
# ------------
# Pandas, numpy, itertools,sys,glob,multiprocessing, time, math.pi, itertools.group, matplotlib and seaborn

from math import pi
import sys,os
import numpy as np
import pandas as pd
import paper_classes_2 as pc
from itertools import groupby
import itertools
from matplotlib.patches import FancyBboxPatch
import matplotlib.pyplot as plt
import seaborn as sns


title_size=20
large_size=18
normal_size=16
medium_size=14
small_size=12
project_life=15


def add_legend(ax,my_colors):
    '''
    Description
    -----------
    This function adds the legend and puts the rectangles of the corresponding color for both countries

    Inputs
    ----------
    ax: axes;
    my_colors : array; includes the colors to be used

    Returns
    ------

    '''
    cons=['High \n demand',' Medium \ndemand','Low \n demand']
    x=0.25
    y=1.1
    delta_x=.2
    delta_x_text=0.08
    y_text=1.05

    for i in range (3):
        rect=plt.Rectangle((x+delta_x*i, y), width=0.04, height=0.1,
                             transform=ax.transAxes, zorder=3,edgecolor='white',
                             fill=True, facecolor=my_colors[i], clip_on=False)
        rect2=plt.Rectangle((x-.05+delta_x*i, y), width=0.04, height=0.1,
                             transform=ax.transAxes, zorder=3,edgecolor='white',
                             fill=True, facecolor=my_colors[i], clip_on=False,alpha=0.5)
        ax.text(x+delta_x*i+.022, y+.025, 'US', ha='center',size=large_size,color='black',
                            transform=ax.transAxes)
        ax.text(x+delta_x*i-.03, y+.025, 'CH', ha='center',size=large_size,color='black',
                            transform=ax.transAxes)
        ax.text(x+delta_x*i+delta_x_text,y_text, cons[i], ha='center',size=large_size,color='black',
                            transform=ax.transAxes)
        ax.add_patch(rect)
        ax.add_patch(rect2)
def add_line(ax, xpos, ypos,max_ypos,lw):
    '''
    Description
    -----------
    This function adds a line in the corresponding axe and position

    Inputs
    ----------
    ax: axes;
    xpos: float; position in x axis
    ypos: float; position in y axis
    max_ypos: float; maximum position in y axis
    lw: float; line width

    Returns
    ------

    '''
    line = plt.Line2D([xpos, xpos], [ypos+max_ypos, ypos],
                      transform=ax.transAxes, color='black',alpha=0.5,linestyle='--',lw=lw)
    line.set_clip_on(False)
    ax.add_line(line)

def label_len(my_index,level):
    '''
    Description
    -----------

    Inputs
    ----------
    my_index: index;
    level: ; index level

    Returns
    ------


    '''
    labels = my_index.get_level_values(level)
    return [(k, sum(1 for i in g)) for k,g in groupby(labels)]

def label_group_bar_table(ax,ax1, df):
    '''
    Description
    -----------
    This function adds a patch to the graph to include the names of the applications
    Inputs
    ----------
    ax: axis; US axis
    ax1: axis; CH axis
    df: DataFrame; data

    Returns
    ------


    '''
    all_apps_name=['1. PVSC','2. PVSC+DPS','3. PVSC+DLS','PVSC+DLS+DPS',
                   '4. PVSC+PVCT','PVSC+PVCT+DPS','PVSC+PVCT+DLS',
                   '5. PVSC+PVCT+DLS+DPS']
    ypos = -.275
    scale = 1./df.index.size

    pos = 1.125
    i=0

    for label, rpos in label_len(df.index,1):
        lxpos = (pos + (.5 * rpos))*scale

        if (label == 'VRLA') or (label == 'NMC'):
            ydist=.175
        elif label == 'NCA':
            ydist=.17
        else:
            ydist=.16
        if rpos==3:
            #add_line(ax, pos*scale, ypos,.1,2)
            rect=plt.Rectangle((lxpos, ypos), width=0.25, height=0.025,
                     transform=ax.transAxes, zorder=3,edgecolor='white',
                     fill=True, facecolor="silver", clip_on=False,angle=90)
            ax.text(lxpos-.01, ypos+ydist, label, ha='center', size=normal_size,color='white',weight='bold',
                    transform=ax.transAxes,rotation=90)
            ax.add_patch(rect)
        if(i%6==0)&(i>0):
            add_line(ax, (pos-1)*scale, ypos,1.28,2.5)
            add_line(ax1, (pos-1)*scale, ypos+.275,1,2.5)
        i+=1
        pos += rpos
    ypos = -1.42
    scale = 1./df.index.size
    pos = 0
    i=0
    for label, rpos in label_len(df.index,0):
        lxpos = (pos + (.5 * rpos))*scale-.1
        #add_line(ax, pos*scale, ypos,.1,2)
        rect=plt.Rectangle((lxpos+.005, ypos), width=0.195, height=0.1,
                 transform=ax.transAxes, zorder=3,edgecolor='white',
                 fill=True, facecolor="grey", clip_on=False)

        ax1.text(lxpos+.105, ypos+.02, all_apps_name[int(label)], ha='center', size=normal_size,color='white',weight='bold',
                transform=ax.transAxes)
        ax1.add_patch(rect)


        pos += rpos
    ypos -= .1

def plot_col2(df,col,capacity,quartile,save,**kwargs):
    '''
    Description
    -----------
    This function plots according to the column, cpacity and quartile chosen the data contained in df for the selected parameters

    Inputs
    ----------
    df: DataFrame; Data
    col: string; indicator to be plotted
    capacity:float; Battery Capacity
    quartile: float; PV Quartile
    save: boolean; boolean to save in pdf if true.
    **kwargs

    Returns
    ------


    '''
    sns.set_style("white")

    df_US=df[(df.Capacity==capacity)&(df.quartile==quartile)&(df.country=='US')].groupby(['App_comb','Tech','cons']).mean()
    df_CH=df[(df.Capacity==capacity)&(df.quartile==quartile)&(df.country=='CH')].groupby(['App_comb','Tech','cons']).mean()
    all_apps=np.arange(8)
    all_apps_name=['PVSC','PVSC+DPS','PVSC+DLS','PVSC+DLS+DPS','PVSC+PVCT',
                   'PVSC+PVCT+DPS','PVSC+PVCT+DLS','PVSC+PVCT+DLS+DPS']
    Apps=[all_apps_name[all_apps[i]] for i in range(len(all_apps))]
    if kwargs is not None:
        if 'App' in kwargs:
            Apps=[all_apps_name[kwargs['App'][i]] for i in range(len(kwargs['App']))]
            df_US=df[(df.Capacity==capacity)&(df.quartile==quartile)&(df.country=='US')&
                     (df.App_comb.isin(kwargs['App']))].groupby(['App_comb','Tech','cons']).mean()
            df_CH=df[(df.Capacity==capacity)&(df.quartile==quartile)&(df.country=='CH')&
                     (df.App_comb.isin(kwargs['App']))].groupby(['App_comb','Tech','cons']).mean()


    aux=df_US.loc[:,[col]]
    aux2=df_CH.loc[:,[col]]
    if (col=='LCOES') :
        title=' LCOES'
        units=' LCOES [USD/kWh]'
        x_max=max(max(aux[col]),max(aux2[col]))+.1
    elif  (col=='LVOES'):
        units=' LVOES [USD/kWh]'
        cmap='RdYlGn'
        title=' LVOES'
        x_max=max(max(aux[col]),max(aux2[col]))+.1

    elif  (col=='life'):
        units=' years'
        title=' lifetime'
        cmap='RdYlGn'
        x_max=max(max(aux[col]),max(aux2[col]))+.1

    elif  (col=='NPV') or (col=='NPV_F')or (col=='NPV_F_IR'):
        cmap='RdYlGn'
        units=' NPV [thousands of USD]'
        title=' NPV'
        aux=aux/1000
        aux2=aux2/1000
        x_max=(max(max(aux[col]),max(aux2[col]))-.5)
        x_min=(min(min(aux[col]),min(aux2[col]))-.5)
    elif  (col=='EFC_nolifetime'):
        cmap='RdYlGn'
        units=' EFC [full cycles per year]'
        title=' EFC'
        aux=aux*15
        aux2=aux2*15
        x_max=(max(max(aux[col]),max(aux2[col]))-.5)
        x_min=(min(min(aux[col]),min(aux2[col]))-.5)
    elif (col=='TSC'):
        units=' years'
        title=' lifetime'
        cmap='RdYlGn'
        x_max=max(max(aux[col]),max(aux2[col]))+.1


        #vmin=0
#    colors = [ sns.xkcd_rgb["pale red"], sns.xkcd_rgb["faded green"],sns.xkcd_rgb["denim blue"]]
    colors= sns.color_palette('bright',n_colors = 3)
    my_colors = list(itertools.islice(itertools.cycle(colors), None, 3))

    fig=plt.figure(figsize=(20,10))
    ax=fig.add_subplot(2,1,1)

    #df_US[col].plot(kind='bar',color=my_colors, width=1)
    a=[]
    b=[]
    for i in range(120):
        a.append(1+3*i)
        b.append(3+4*i)
    y_pos=np.arange(360)
    y_pos=y_pos[a]
    y_pos=np.delete(y_pos,np.array(b)[:30])
    if col=='NPV':
        plt.bar(y_pos,df_US[col].values/1000,color=my_colors,width=3)
    elif col=='EFC_nolifetime':
        plt.bar(y_pos,df_US[col].values*15,color=my_colors,width=3)
    else:
        plt.bar(y_pos,df_US[col].values,color=my_colors,width=3)
    #Below 3 lines remove default labels
    #ax.grid(axis='y')
    ax1 = fig.add_subplot(212)
    #ax1=ax.twinx()

    #df_CH[col].plot(kind='bar',color=my_colors,alpha=0.5, width=1)
    if col=='NPV':
        plt.bar(y_pos,df_CH[col].values/1000,color=my_colors,width=3,alpha=0.5)

    elif col=='EFC_nolifetime':
        plt.bar(y_pos,df_CH[col].values*15,color=my_colors,width=3,alpha=0.5)
    else:
        plt.bar(y_pos,df_CH[col].values,color=my_colors,width=3,alpha=0.5)
    if col=='TSC':
        plt.bar(y_pos,df_CH[col].values/1000,color=my_colors,width=3,alpha=0.5)
    #ax1.invert_yaxis()
    #Below 3 lines remove default labels
    #ax1.grid(axis='y')

    fig.subplots_adjust(hspace=0.3)
    #fig.suptitle(('US and Swiss'+title+' for battery capacity {} kWh and'
    #              'PV quartile {} \n according to household demand').format(
    #    str(capacity),str(quartile)),size=title_size,y=.99)
    ax.set_ylabel('US\n'+units,size=normal_size)
    ax1.set_ylabel('CH\n'+units,size=normal_size)
    ax.set_xlim([-3,y_pos[-1]+4])
    ax1.set_xlim([-3,y_pos[-1]+4])
    if col=='NPV':
        ax.set_ylim([max(x_max,0),x_min])
        ax1.set_ylim([x_min,max(x_max,0)])
    else:
        ax.set_ylim([0,x_max])
        ax1.set_ylim([x_max,0])

    labels = ['' for item in ax1.get_xticklabels()]
    ax1.set_xticklabels('')
    ax1.set_xlabel('')
    ax.set_xlabel('')
    ax.set_xticklabels('')
    ax.xaxis.set_ticks_position('none')
    ax1.xaxis.set_ticks_position('none')
    ax.grid(axis='y')
    ax1.grid(axis='y')
    label_group_bar_table(ax,ax1, df_US)
    #fig.subplots_adjust(bottom=.1*df_CH[col].index.nlevels)
    ax.set_yticklabels(ax.get_yticks().round(1),size=normal_size)
    ax1.set_yticklabels(ax1.get_yticks().round(1),size=normal_size)
    #plt.rcParams['figure.facecolor'] = 'white'
    ax.tick_params(length =4)
    ax1.tick_params(length =4)

    add_legend(ax,my_colors)
    if save:
        fig.savefig(col+'_'+str(capacity)+'_V2'+'.pdf',format='pdf',transparent=True)

    #plt.show()

def plot_batt2(df,country,quartile,save):
    '''
    Description
    -----------
    This function plots spiders plots for different battery sizes and indicators for two combinations of applications according to the country and quartile indicated as inputs

    Inputs
    ----------
    df: DataFrame; Data
    country: string; Country
    quartile: float; PV Quartile
    save: boolean; boolean to save in pdf if true.

    Returns
    ------


    '''
    # Set data
    df_US=df[(df.quartile==quartile)&
         (df.App_comb==1)].groupby(['Tech','Capacity']).mean().reset_index()
    df_CH=df[(df.quartile==quartile)&
         (df.App_comb==7)].groupby(['Tech','Capacity']).mean().reset_index()
    # ------- PART 1: Create background
    df_US['NPV']=df_US['NPV']/1000
    df_CH['NPV']=df_CH['NPV']/1000
    # number of variable
    categories=df_US.Tech.unique()
    N = len(categories)

    # What will be the angle of each axis in the plot? (we divide the plot / number of variable)
    angles = [n / float(N) * 2 * pi for n in range(N)]
    angles += angles[:1]

    # Initialise the spider plot

    fig,ax=plt.subplots(nrows=3,ncols=3,figsize=(10,10),subplot_kw=dict(projection='polar'))
    ax=ax.flatten('F')
    j=0
    title=['LCOES\n[USD/kWh]','LVOES\n[USD/kWh]','NPV\n[thousand USD]']
    cap=['Small\nsize','Medium\nsize','Large\nsize']
    for i in range(9):
         # If you want the first axis to be on top:
        ax[i].set_theta_offset(pi / 2)
        ax[i].set_theta_direction(-1)

        # Draw one axe per variable + add labels labels yet
        ax[i].set_xticks(angles[:-1])
        ax[i].set_xticklabels(categories,size=small_size)

        # Draw ylabels
        ax[i].set_rlabel_position(0)
        #Columns are LCOES LVOES and NPV
        #Rows are high medium and low consumption

        if i<3:
            col='LCOES'
            ax[i].set_yticks([0.5,1.5,2.5])
            ax[i].set_ylim(0,3)
        elif i<6:
            col='LVOES'
            ax[i].set_yticks([0,0.2,0.4])
            ax[i].set_ylim(0,0.5)
        else:
            col='NPV'
            ax[i].set_yticks([-30,-20,-10,0])
            ax[i].set_ylim(-30,5)

        if (i)%3==0:
            #small batteries

            values=df_CH[(df_CH.Capacity==3)][col].tolist()
            values += values[:1]
            ax[i].plot(angles, values, linewidth=1,color='b', linestyle='solid', label="1")
            ax[i].fill(angles, values, 'b', alpha=0.1)
            values=df_US[(df_US.Capacity==3)][col].tolist()
            values += values[:1]
            ax[i].plot(angles, values, linewidth=1, color='r',linestyle='solid', label="7")
            ax[i].fill(angles, values, 'r', alpha=0.1)

            ax[i].set_title(title[j],y=1.2,size=normal_size,)

            ax[j].text(-.25, .5, cap[j], ha='center',size=normal_size,
                       rotation=90,transform=ax[j].transAxes)
            j+=1
        elif (i+1)%3==0:
            #large batteries
            values=df_CH[(df_CH.Capacity==14)][col].tolist()
            values += values[:1]
            ax[i].plot(angles, values, linewidth=1,color='b', linestyle='solid', label="1")
            ax[i].fill(angles, values, 'b', alpha=0.1)
            values=df_US[(df_US.Capacity==14)][col].tolist()
            values += values[:1]
            ax[i].plot(angles, values, linewidth=1, color='r',linestyle='solid', label="7")
            ax[i].fill(angles, values, 'r', alpha=0.1)
        else:
            # medium batteries
            values=df_CH[(df_CH.Capacity==7)][col].tolist()
            values += values[:1]
            ax[i].plot(angles, values, linewidth=1,color='b', linestyle='solid', label="1")
            ax[i].fill(angles, values, 'b', alpha=0.1)
            values=df_US[(df_US.Capacity==7)][col].tolist()
            values += values[:1]
            ax[i].plot(angles, values, linewidth=1, color='r',linestyle='solid', label="7")
            ax[i].fill(angles, values, 'r', alpha=0.1)



        fig.subplots_adjust(hspace=0.3,wspace=.2)
    ax[i].legend(loc='upper right', ncol=2, bbox_to_anchor=(-.4, -.2))
    #plt.show()
    if save:
        fig.savefig('Batt'+'_new'+'.pdf',format='pdf',transparent=True)

def plot_PV2(df,country,Capacity,save):
    '''
    Description
    -----------
    This function plots spiders plots for different PV sizes and indicators for two combinations of applications according to the country and battery capacity indicated as inputs

    Inputs
    ----------
    df: DataFrame; Data
    country: string; Country
    Capacity: float; Battery capacity
    save: boolean; boolean to save in pdf if true.

    Returns
    ------


    '''
    # Set data
    df_SC=df[(df.Capacity==Capacity)&(df.country==country)&
         (df.App_comb==1)].groupby(['Tech','quartile']).mean().reset_index()
    df_all=df[(df.Capacity==Capacity)&(df.country==country)&
         (df.App_comb==7)].groupby(['Tech','quartile']).mean().reset_index()
    # ------- PART 1: Create background
    df_SC['NPV']=df_SC['NPV']/1000
    df_all['NPV']=df_all['NPV']/1000
    # number of variable
    categories=df.Tech.unique()
    categories=['ALA','    LFP','    LTO','NCA','NMC     ','VRLA     ']
    N = len(categories)

    # What will be the angle of each axis in the plot? (we divide the plot / number of variable)
    angles = [n / float(N) * 2 * pi for n in range(N)]
    angles += angles[:1]

    # Initialise the spider plot

    fig,ax=plt.subplots(nrows=3,ncols=3,figsize=(10,10),subplot_kw=dict(projection='polar'))
    ax=ax.flatten('F')
    j=0
    title=['LCOES\n[USD/kWh]','LVOES\n[USD/kWh]','NPV\n[thousand USD]']
    cap=['Small PV\nsize','Medium PV\nsize','Large PV\nsize']
    for i in range(9):
         # If you want the first axis to be on top:
        ax[i].set_theta_offset(pi / 2)
        ax[i].set_theta_direction(-1)

        # Draw one axe per variable + add labels labels yet
        ax[i].set_xticks(angles[:-1])
        ax[i].set_xticklabels(categories,size=small_size)

        # Draw ylabels
        ax[i].set_rlabel_position(0)
        #Columns are LCOES LVOES and NPV
        #Rows are high medium and low consumption

        if i<3:
            col='LCOES'
            ax[i].set_yticks([0,.5,1,1.5])
            ax[i].set_ylim(0,2)
        elif i<6:
            col='LVOES'
            ax[i].set_yticks([0,0.1,0.2,0.3,0.4])
            ax[i].set_ylim(0,0.5)
        else:
            col='NPV'
            ax[i].set_yticks([-15,-12.5,-10,-7.5,-5,-2.5])
            ax[i].set_ylim(-15,0)

        if (i)%3==0:
            #small PV

            values=df_all[(df_all.quartile==25)][col].tolist()
            values += values[:1]
            ax[i].plot(angles, values, linewidth=1, color='b',linestyle='solid', label="All applications")
            ax[i].fill(angles, values, 'b', alpha=.1)
            values=df_SC[(df_SC.quartile==25)][col].tolist()
            values += values[:1]
            ax[i].plot(angles, values, linewidth=1, color='r',linestyle='solid', label="PVSC")
            ax[i].fill(angles, values, 'r', alpha=0.1)

            ax[i].set_title(title[j],y=1.2,size=normal_size,)

            ax[j].text(-.25, .5, cap[j], ha='center',size=normal_size,
                       rotation=90,transform=ax[j].transAxes)
            j+=1
        elif (i+1)%3==0:
            #large PV
            values=df_all[(df_all.quartile==75)][col].tolist()
            values += values[:1]
            ax[i].plot(angles, values, linewidth=1, color='b',linestyle='solid', label="All applications")
            ax[i].fill(angles, values, 'b', alpha=0.1)
            values=df_SC[(df_SC.quartile==75)][col].tolist()
            values += values[:1]
            ax[i].plot(angles, values, linewidth=1, color='r', linestyle='solid', label="PVSC")
            ax[i].fill(angles, values, 'r', alpha=0.1)
        else:
            # medium PV
            values=df_all[(df_all.quartile==50)][col].tolist()
            values += values[:1]
            ax[i].plot(angles, values, linewidth=1,color='b', linestyle='solid', label="All applications")
            ax[i].fill(angles, values, 'b', alpha=0.1)
            values=df_SC[(df_SC.quartile==50)][col].tolist()
            values += values[:1]
            ax[i].plot(angles, values, linewidth=1, color='r',linestyle='solid', label="PVSC")
            ax[i].fill(angles, values, 'r', alpha=0.1)


        fig.subplots_adjust(hspace=0.3,wspace=.2)
    ax[i].legend(loc='upper right', ncol=2, bbox_to_anchor=(-.4, -.2))
    plt.show()
    if save:
        fig.savefig('PV'+'_'+str(Capacity)+'_new_'+str(country)+'.pdf',format='pdf')

def autolabel(rects,ax):
    '''
    Description
    -----------
    This function attach a text label above each bar displaying its height

    Inputs
    ----------
    ax: axis;
    rects: ;

    Returns
    ------


    '''

    for rect in rects:
        height = rect.get_height()
        ax.text(rect.get_x() + rect.get_width()/2., 1.0*height,
                '%d' % int(height),
                ha='center', va='bottom',size=16)


def Breakeven_point(df,save):
    '''
    Description
    -----------
    This function plots the breakeven point for the two countries and all battery technologies.

    Inputs
    ----------
    df: DataFrame; Data
    save: boolean; boolean to save in pdf if true.

    Returns
    ------


    '''
    colors= sns.color_palette('bright',n_colors = 3)
    my_colors = list(itertools.islice(itertools.cycle(colors), None, 3))
    fig=plt.figure(figsize=(20,15))
    ax=fig.add_subplot(1,1,1)
    sns.set_style("white")
    aux=['ALA','LFP','LTO\n          Switzerland','NCA','NMC','VRLA',
     'ALA','LFP','LTO\n             U.S.','NCA','NMC','VRLA']
    barWidth = 0.3

    bars1=df[df.columns[0]].values
    bars2=df[df.columns[1]].values
    bars3=df[df.columns[2]].values
    r1=np.arange(len(bars1))
    r2 = [x + barWidth for x in r1]
    r3 = [x + 2*barWidth for x in r1]

    rects1=ax.bar(r1, bars1, width = barWidth, color = my_colors[0],
                  edgecolor = 'black', capsize=7, label='Breakeven point with\nPVSC only')

    rects2=ax.bar(r2, bars2, width = barWidth, color = my_colors[1],
                  edgecolor = 'black',capsize=7, label='Breakeven point with\nall applications')
    rects3=ax.bar(r3, bars3, width = barWidth, color = my_colors[2],
                  edgecolor = 'black',capsize=7, label='$/kWh installed\n used in this study')

    ax.set_xticks([r+2*barWidth/3  for r in range(len(bars1))])
    ax.set_xticklabels(aux,size=18)
    ax.set_ylabel('$/kWh installed',size=18)
    ax.set_xlabel('Battery Technology\nCountry',size=18)
    ax.tick_params(axis='both', which='major', labelsize=18)
    add_line(ax, 0.5, 0,1,5)
    ax.legend(fontsize=18)

    autolabel(rects1,ax)
    autolabel(rects2,ax)
    autolabel(rects3,ax)
    if save:
        fig.savefig('breakeven_point_V2_pres'+'.tiff',format='tiff',tranparent=True)

    #plt.show()
    return
def main():
    '''
    Description
    -----------
    Calls all the functions to plot the graphs in the main paper
    '''
    print("########################################################")
    print("Graphics from the paper Optimization of PV-coupled battery systems for combining applications: impact of battery technology and location. Pena-Bello et al. (2019)")
    print("########################################################")

    dfa=pd.read_pickle('dfa_V2.pickle')#aggregated

    print("########################################################")
    print("Plotting")
    #Fig 2
    plot_col2(dfa,'LCOES',7,50,1,App=[0,1,2,4,7])
    #Fig 3
    plot_col2(dfa,'LVOES',7,50,1,App=[0,1,2,4,7])
    #Fig 4
    plot_col2(dfa,'NPV',7,50,1,App=[0,1,2,4,7])
    #Fig 5
    plot_batt(dfa,7,50,1)
    #Fig 6
    df=pd.read_excel('C:/Users/alejandro/Dropbox/0. PhD/2017/Paper 1/writing/price_reductions.xlsx')
    Breakeven_point(df,1)

    print("End plotting main paper")
    print("########################################################")

if __name__== '__main__':
    main()
