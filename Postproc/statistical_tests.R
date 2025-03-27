library(dplyr)
library(ggplot2)
library(ggpubr)
library(ggtern)
library(ggrepel)
library(adklakedata)
library(ade4)
library(adegraphics)
getwd()
# In this script we follow the same steps as in the paper results

df1<-read.table('df_wilcox_paired_2.csv',sep=',',header=TRUE)
df1 <- subset(df1,(df1$conf!=7))

factor(df1$conf)
#################################################################
#test for Application DLS
df_app2<-subset(df1,df1$App_comb==2)
df_app3<-subset(df1,df1$App_comb==3)
#LCOE proves

df_app2$DHW_present <- ifelse((df_app2$conf%%2==1), TRUE, FALSE)
df_app2_DHW<-subset(df_app2,df_app2$DHW_present==TRUE)
df_app2_noDHW<-subset(df_app2,df_app2$DHW_present==FALSE)

df_app3$DHW_present <- ifelse((df_app3$conf%%2==1), TRUE, FALSE)
df_app3_DHW<-subset(df_app3,df_app3$DHW_present==TRUE)
df_app3_noDHW<-subset(df_app3,df_app3$DHW_present==FALSE)

#LCOE
#Proves among house types and DHW presence
#Normality tests
if (length(df_app2_noDHW$LCOE)>5000){
shapiro.test(sample(df_app2_noDHW$LCOE,5000))
}else{shapiro.test(df_app2_noDHW$LCOE)}

if (length(df_app2_DHW$LCOE)>5000){
  shapiro.test(sample(df_app2_DHW$LCOE,5000))
}else{shapiro.test(df_app2_DHW$LCOE)}

if (length(df_app3_noDHW$LCOE)>5000){
  shapiro.test(sample(df_app3_noDHW$LCOE,5000))
}else{shapiro.test(df_app3_noDHW$LCOE)}

if (length(df_app3_DHW$LCOE)>5000){
  shapiro.test(sample(df_app3_DHW$LCOE,5000))
}else{shapiro.test(df_app3_DHW$LCOE)}


#wilcoxon tests
# First, in households with very high energetic quality (SFH15), such as Swiss Minergie-P or German Passivhaus, the LCOE is significantly higher
pairwise.wilcox.test(df_app2_DHW$LCOE,df_app2_DHW$house_type,paired=TRUE)
pairwise.wilcox.test(df_app2_noDHW$LCOE,df_app2_noDHW$house_type,paired=TRUE)
pairwise.wilcox.test(df_app3_DHW$LCOE,df_app3_DHW$house_type,paired=TRUE)
pairwise.wilcox.test(df_app3_noDHW$LCOE,df_app3_noDHW$house_type,paired=TRUE)

# Now we test among configurations, so division per house type
#Second, DHW provision reduces significantly LCOE values when compared within the same type of houses
#subset by type of house
df_app2_15<-subset(df_app2,df_app2$house_type=='SFH15')
df_app2_45<-subset(df_app2,df_app2$house_type=='SFH45')
df_app2_100<-subset(df_app2,df_app2$house_type=='SFH100')

df_app3_15<-subset(df_app3,df_app3$house_type=='SFH15')
df_app3_45<-subset(df_app3,df_app3$house_type=='SFH45')
df_app3_100<-subset(df_app3,df_app3$house_type=='SFH100')


tapply(df_app2_15$P_drained_max, df_app2_15$conf, median)-4.8
tapply(df_app2_45$P_drained_max, df_app2_45$conf, median)-4.8
tapply(df_app2_100$P_drained_max, df_app2_100$conf, median)-4.8

tapply(df_app3_15$P_drained_max, df_app3_15$conf, median)
tapply(df_app3_45$P_drained_max, df_app3_45$conf, median)
tapply(df_app3_100$P_drained_max, df_app3_100$conf, median)



#Prove of normality for LCOES:
shapiro.test(df_app2_15$LCOE)
shapiro.test(df_app2_45$LCOE)
shapiro.test(df_app2_100$LCOE)
shapiro.test(df_app3_15$LCOE)
shapiro.test(df_app3_45$LCOE)
shapiro.test(df_app3_100$LCOE)

#wilcoxon tests
pairwise.wilcox.test(df_app2_15$LCOE,df_app2_15$conf,paired=TRUE)
pairwise.wilcox.test(df_app2_45$LCOE,df_app2_45$conf,paired=TRUE)
pairwise.wilcox.test(df_app2_100$LCOE,df_app2_100$conf,paired=TRUE)

pairwise.wilcox.test(df_app3_15$LCOE,df_app3_15$conf,paired=TRUE)
pairwise.wilcox.test(df_app3_45$LCOE,df_app3_45$conf,paired=TRUE)
pairwise.wilcox.test(df_app3_100$LCOE,df_app3_100$conf,paired=TRUE)

max(tapply(df_app2_15$LCOE, df_app2_15$conf, median)-
      tapply(df_app2_100$LCOE, df_app2_100$conf, median))

median(tapply(((df_app3_45$E_hp)+(df_app3_45$E_hpdhw)+(df_app3_45$E_demand)
           +(df_app3_45$E_bu)+(df_app3_45$E_budhw)), df_app3_45$conf, median)-
      tapply(((df_app3_100$E_hp)+(df_app3_100$E_hpdhw)+(df_app3_100$E_demand)
              +(df_app3_100$E_bu)+(df_app3_100$E_budhw)), df_app3_100$conf, median))


max(tapply(df_app3_15$LCOE, df_app3_15$conf, median)
    -tapply(df_app3_100$LCOE, df_app3_100$conf, median))
tapply(df_app2_15$LCOE, df_app2_15$conf, median)
tapply(df_app2_45$LCOE, df_app2_45$conf, median)
tapply(df_app2_100$LCOE, df_app2_100$conf, median)
tapply(df_app3_15$LCOE, df_app3_15$conf, median)
tapply(df_app3_45$LCOE, df_app3_45$conf, median)
tapply(df_app3_100$LCOE, df_app3_100$conf, median)


#Third, the addition of batteries to the PV-coupled heat pump system
#significantly increases the LCOE 
df_app2$Batt_present <- ifelse((df_app2$conf>=4), TRUE, FALSE)
df_app2_Batt<-subset(df_app2,df_app2$Batt_present==TRUE)
df_app2_noBatt<-subset(df_app2,df_app2$Batt_present==FALSE)
pairwise.wilcox.test(df_app2$LCOE,df_app2$Batt_present,paired=TRUE)

df_app3$Batt_present <- ifelse((df_app3$conf>=4), TRUE, FALSE)
df_app3_Batt<-subset(df_app3,df_app3$Batt_present==TRUE)
df_app3_noBatt<-subset(df_app3,df_app3$Batt_present==FALSE)
pairwise.wilcox.test(df_app3$LCOE,df_app3$Batt_present,paired=TRUE)

(tapply(df_app2_noBatt$LCOE, df_app2_noBatt$conf, median)-
    tapply(df_app2_Batt$LCOE, df_app2_Batt$conf, median))

(tapply(df_app3_noBatt$LCOE, df_app3_noBatt$conf, median)-
  tapply(df_app3_Batt$LCOE, df_app3_Batt$conf, median))



#test of the inclusion of the capacity tariff 
#Finally, the inclusion of the capacity tariff entails a significant increase of the LCOE 
dim(subset(df1,df1$App_comb==2))
dim(subset(df1,df1$App_comb==3))

pairwise.wilcox.test(df1$LCOE,df1$App_comb,paired=TRUE)

mean(tapply(df_app3_15$LCOE, df_app3_15$conf, median)-tapply(df_app2_15$LCOE, df_app2_15$conf, median))
mean(tapply(df_app3_45$LCOE, df_app3_45$conf, median)-tapply(df_app2_45$LCOE, df_app2_45$conf, median))
mean(tapply(df_app3_100$LCOE, df_app3_100$conf, median)-tapply(df_app2_100$LCOE, df_app2_100$conf, median))

(tapply(df_app2$E_grid_batt,df_app2$conf,median)-
tapply(df_app3$E_grid_batt,df_app3$conf,median))
mean(tapply(df_app2$Bill,df_app2$conf,median)-
    tapply(df_app3$Bill,df_app3$conf,median))
#Now the same when there is capacity tariff

#Power
#Proves among house types and DHW presence
#the peak power demand is significantly higher ($p-values \le  0.05$) in households with low energetic quality (SFH100), compared to households with high (SFH45) and very high energetic quality (SFH15)


#Prove of normality for P_drained_max:
shapiro.test(df_app2_15$P_drained_max)
shapiro.test(df_app2_45$P_drained_max)
shapiro.test(df_app2_100$P_drained_max)
shapiro.test(df_app3_15$P_drained_max)
shapiro.test(df_app3_45$P_drained_max)
shapiro.test(df_app3_100$P_drained_max)

#wilcoxon tests
pairwise.wilcox.test(df_app2_15$P_drained_max,df_app2_15$conf,paired=TRUE)
pairwise.wilcox.test(df_app2_45$P_drained_max,df_app2_45$conf,paired=TRUE)
pairwise.wilcox.test(df_app2_100$P_drained_max,df_app2_100$conf,paired=TRUE)

pairwise.wilcox.test(df_app3_15$P_drained_max,df_app3_15$conf,paired=TRUE)
pairwise.wilcox.test(df_app3_45$P_drained_max,df_app3_45$conf,paired=TRUE)
pairwise.wilcox.test(df_app3_100$P_drained_max,df_app3_100$conf,paired=TRUE)

max(tapply(df_app2_15$P_drained_max, df_app2_15$conf, median)-
      tapply(df_app2_100$P_drained_max, df_app2_100$conf, median))

max(tapply(df_app3_15$P_drained_max, df_app3_15$conf, median)
    -tapply(df_app3_100$P_drained_max, df_app3_100$conf, median))
tapply(df_app2_15$P_drained_max, df_app2_15$conf, median)
tapply(df_app2_45$P_drained_max, df_app2_45$conf, median)
tapply(df_app2_100$P_drained_max, df_app2_100$conf, median)
tapply(df_app3_15$P_drained_max, df_app3_15$conf, median)
tapply(df_app3_45$P_drained_max, df_app3_45$conf, median)
tapply(df_app3_100$P_drained_max, df_app3_100$conf, median)-4.8


#Normality tests
if (length(df_app3_noDHW$LCOE)>5000){
  shapiro.test(sample(df_app3_noDHW$LCOE,5000))
}else{shapiro.test(df_app3_noDHW$LCOE)}

if (length(df_app3_DHW$LCOE)>5000){
  shapiro.test(sample(df_app3_DHW$LCOE,5000))
}else{shapiro.test(df_app3_DHW$LCOE)}


#wilcoxon tests
pairwise.wilcox.test(df_app2_DHW$P_drained_max,df_app2_DHW$house_type,paired=TRUE)
pairwise.wilcox.test(df_app2_noDHW$P_drained_max,df_app2_noDHW$house_type,paired=TRUE)
pairwise.wilcox.test(df_app3_DHW$P_drained_max,df_app3_DHW$house_type,paired=TRUE)
pairwise.wilcox.test(df_app3_noDHW$P_drained_max,df_app3_noDHW$house_type,paired=TRUE)

#the peak power demand is significantly lower ($p-values \le  0.05$) when the capacity tariff is included 
pairwise.wilcox.test(df1$P_drained_max,df1$App_comb,paired=TRUE)


# Now we test among configurations, so division per house type
#Third, the peak power demand does not significantly change when DHW is provided using the heat pump in low energetic quality households
#subset by type of house

#Prove of normality for Power:
shapiro.test(df_app3_15$P_drained_max)
shapiro.test(df_app3_45$P_drained_max)
shapiro.test(df_app3_100$P_drained_max)

#wilcoxon tests
pairwise.wilcox.test(df_app2_15$P_drained_max,df_app2_15$conf,paired=TRUE)
pairwise.wilcox.test(df_app2_45$P_drained_max,df_app2_45$conf,paired=TRUE)
pairwise.wilcox.test(df_app2_100$P_drained_max,df_app2_100$conf,paired=TRUE)

pairwise.wilcox.test(df_app3_15$P_drained_max,df_app3_15$conf,paired=TRUE)
pairwise.wilcox.test(df_app3_45$P_drained_max,df_app3_45$conf,paired=TRUE)
pairwise.wilcox.test(df_app3_100$P_drained_max,df_app3_100$conf,paired=TRUE)

pairwise.wilcox.test(df_app2_15$TSC,df_app2_15$conf,paired=TRUE)
pairwise.wilcox.test(df_app2_45$TSC,df_app2_45$conf,paired=TRUE)
pairwise.wilcox.test(df_app2_100$TSC,df_app2_100$conf,paired=TRUE)

pairwise.wilcox.test(df_app3_15$SS,df_app3_15$conf,paired=TRUE)
pairwise.wilcox.test(df_app3_45$SS,df_app3_45$conf,paired=TRUE)
pairwise.wilcox.test(df_app3_100$SS,df_app3_100$conf,paired=TRUE)


(tapply(df_app2_15$P_drained_max, df_app2_15$conf, median)
  -tapply(df_app2_45$P_drained_max, df_app2_45$conf, median))
(tapply(df_app2_15$P_drained_max, df_app2_15$conf, median)
  -tapply(df_app2_100$P_drained_max, df_app2_100$conf, median))

(tapply(df_app3_15$P_drained_max, df_app3_15$conf, median)
  -tapply(df_app3_45$P_drained_max, df_app3_45$conf, median))
(tapply(df_app3_15$P_drained_max, df_app3_15$conf, median)
  -tapply(df_app3_100$P_drained_max, df_app3_100$conf, median))

#the use of batteries when capacity tariffs are included in the electricity tariff, may significantly reduce ($p-values \le  0.05$) the peak power demand

df_app2$Batt_present <- ifelse((df_app2$conf>=4), TRUE, FALSE)
df_app2_Batt<-subset(df_app2,df_app2$Batt_present==TRUE)
df_app2_noBatt<-subset(df_app2,df_app2$Batt_present==FALSE)
pairwise.wilcox.test(df_app2$P_drained_max,df_app2$Batt_present,paired=TRUE)


df_app3$Batt_present <- ifelse((df_app3$conf>=4), TRUE, FALSE)
df_app3_Batt<-subset(df_app3,df_app3$Batt_present==TRUE)
df_app3_noBatt<-subset(df_app3,df_app3$Batt_present==FALSE)
pairwise.wilcox.test(df_app3$P_drained_max,df_app3$Batt_present,paired=TRUE)

#######################################################################

#Graphical indicators
#TSC vs SS
# Only Baseline, SH tank and Battery cases for cases with capacity tariff
df_gi<-subset(df1,((df1$conf==0)|(df1$conf==2)|(df1$conf==4))&(df1$App_comb==3))
#The increases in self-consumption and self-sufficiency under the inclusion of thermal storage for space heating are statistically significant 
shapiro.test(df_gi$TSC)
shapiro.test(df_gi$SS)

pairwise.wilcox.test(df_gi$TSC,df_gi$conf,paired=TRUE)
pairwise.wilcox.test(df_gi$SS,df_gi$conf,paired=TRUE)
#The increase in self-consumption and self-sufficiency due to the inclusion of DHW are as well statistically significant

df_gi_DHW<-subset(df1,((df1$conf==1)|(df1$conf==3)|(df1$conf==5))&(df1$App_comb==3))
shapiro.test(df_gi_DHW$TSC)
shapiro.test(df_gi_DHW$SS)

pairwise.wilcox.test(df_gi_DHW$TSC,df_gi$conf,paired=TRUE)
pairwise.wilcox.test(df_gi_DHW$SS,df_gi$conf,paired=TRUE)

#LCOE vs Power
shapiro.test(df_gi$LCOE)
shapiro.test(df_gi$P_drained_max)

pairwise.wilcox.test(df_gi$LCOE,df_gi$conf,paired=TRUE)
pairwise.wilcox.test(df_gi$P_drained_max,df_gi$conf,paired=TRUE)

######################################################################################
#Sensitivity analysis
#LCOE
df_lcoe<-read.table('LCOE_sens.csv',sep=',',header=TRUE)
df_lcoe <- subset(df_lcoe,((df_lcoe$conf==0)|(df_lcoe$conf==2)|(df_lcoe$conf==4))&(df_lcoe$App_comb==3))
head(df_lcoe)

df_lcoe_15 <- subset(df_lcoe,(df_lcoe$house_type=='SFH15'))
df_lcoe_45 <- subset(df_lcoe,(df_lcoe$house_type=='SFH45'))
df_lcoe_100 <- subset(df_lcoe,(df_lcoe$house_type=='SFH100'))

shapiro.test(sample(df_lcoe_15$LCOE,5000))
shapiro.test(sample(df_lcoe_45$LCOE,5000))
shapiro.test(sample(df_lcoe_100$LCOE,5000))

pairwise.wilcox.test(df_lcoe_15$LCOE,df_lcoe_15$discount_rate,paired=TRUE)
pairwise.wilcox.test(df_lcoe_45$LCOE,df_lcoe_45$discount_rate,paired=TRUE)
pairwise.wilcox.test(df_lcoe_100$LCOE,df_lcoe_100$discount_rate,paired=TRUE)

df_lcoe_hh<-rbind(tapply(df_lcoe_15$LCOE,df_lcoe_15$conf,median),
                  tapply(df_lcoe_45$LCOE,df_lcoe_45$conf,median),
                  tapply(df_lcoe_100$LCOE,df_lcoe_100$conf,median))

aggregate(LCOE~house_type+conf+discount_rate,df_lcoe,median)

#CAPEX
df_orig<-read.table('df_wilcox_paired_2.csv',sep=',',header=TRUE)
df_batt<-read.table('df_batt_half.csv',sep=',',header=TRUE)
df_hp<-read.table('df_hp_half.csv',sep=',',header=TRUE)
df_PV<-read.table('df_PV_half.csv',sep=',',header=TRUE)

df_orig <- subset(df_orig,((df_orig$conf==0)|(df_orig$conf==2)|(df_orig$conf==4))&(df_orig$App_comb==3))
df_batt <- subset(df_batt,((df_batt$conf==0)|(df_batt$conf==2)|(df_batt$conf==4))&(df_batt$App_comb==3))
df_hp <- subset(df_hp,((df_hp$conf==0)|(df_hp$conf==2)|(df_hp$conf==4))&(df_hp$App_comb==3))
df_PV <- subset(df_PV,((df_PV$conf==0)|(df_PV$conf==2)|(df_PV$conf==4))&(df_PV$App_comb==3))

df_orig$reduction_device<-'None'
df_batt$reduction_device<-'Battery'
df_hp$reduction_device<-'HP'
df_PV$reduction_device<-'PV'

df_orig_15 <- subset(df_orig,(df_orig$house_type=='SFH15'))
df_orig_45 <- subset(df_orig,(df_orig$house_type=='SFH45'))
df_orig_100 <- subset(df_orig,(df_orig$house_type=='SFH100'))
                  
df_batt_15 <- subset(df_batt,(df_batt$house_type=='SFH15'))
df_batt_45 <- subset(df_batt,(df_batt$house_type=='SFH45'))
df_batt_100 <- subset(df_batt,(df_batt$house_type=='SFH100'))

df_hp_15 <- subset(df_hp,(df_hp$house_type=='SFH15'))
df_hp_45 <- subset(df_hp,(df_hp$house_type=='SFH45'))
df_hp_100 <- subset(df_hp,(df_hp$house_type=='SFH100'))

df_PV_15 <- subset(df_PV,(df_PV$house_type=='SFH15'))
df_PV_45 <- subset(df_PV,(df_PV$house_type=='SFH45'))
df_PV_100 <- subset(df_PV,(df_PV$house_type=='SFH100'))

df_capex_15<-rbind(df_orig_15,df_batt_15,df_hp_15,df_PV_15)
df_capex_45<-rbind(df_orig_45,df_batt_45,df_hp_45,df_PV_45)
df_capex_100<-rbind(df_orig_100,df_batt_100,df_hp_100,df_PV_100)

shapiro.test(sample(df_capex_15$LCOE,5000))
shapiro.test(sample(df_capex_45$LCOE,5000))
shapiro.test(sample(df_capex_100$LCOE,5000))

pairwise.wilcox.test(df_capex_15$LCOE,df_capex_15$reduction_device,paired=TRUE)
pairwise.wilcox.test(df_capex_45$LCOE,df_capex_45$reduction_device,paired=TRUE)
pairwise.wilcox.test(df_capex_100$LCOE,df_capex_100$reduction_device,paired=TRUE)

df_orig_hh<-rbind(tapply(df_orig_15$LCOE,df_orig_15$conf,median),
                  tapply(df_orig_45$LCOE,df_orig_45$conf,median),
                  tapply(df_orig_100$LCOE,df_orig_100$conf,median))

df_batt_hh<-rbind(tapply(df_batt_15$LCOE,df_batt_15$conf,median),
                  tapply(df_batt_45$LCOE,df_batt_45$conf,median),
                  tapply(df_batt_100$LCOE,df_batt_100$conf,median))

df_hp_hh<-rbind(tapply(df_hp_15$LCOE,df_hp_15$conf,median),
                tapply(df_hp_45$LCOE,df_hp_45$conf,median),
                tapply(df_hp_100$LCOE,df_hp_100$conf,median))

df_PV_hh<-rbind(tapply(df_PV_15$LCOE,df_PV_15$conf,median),
                tapply(df_PV_45$LCOE,df_PV_45$conf,median),
                tapply(df_PV_100$LCOE,df_PV_100$conf,median))

df_orig_hh-df_batt_hh
df_orig_hh-df_hp_hh
df_orig_hh-df_PV_hh

t(rbind(df_orig_hh,df_batt_hh,df_hp_hh,df_PV_hh))



############################################################################################
df_nm<-read.table('df_wilcox_paired_normalCT.csv',sep=',',header=TRUE)
df_db<-read.table('df_wilcox_paired_doubleCT.csv',sep=',',header=TRUE)
df_hf<-read.table('df_wilcox_paired_halfCT.csv',sep=',',header=TRUE)
df_q<-read.table('df_wilcox_paired_quarterCT.csv',sep=',',header=TRUE)
df_nm_zero<-subset(df_nm,((df_nm$conf==2)|(df_nm$conf==4))&(df_nm$App_comb==2))
df_nm<-subset(df_nm,((df_nm$conf==2)|(df_nm$conf==4))&(df_nm$App_comb==3))


df_nm_zero$cap<-'zero'
df_nm$cap<-'normal'
df_db$cap<-'double'
df_hf$cap<-'half'
df_q$cap<-'quarter'

list_hh<-intersect(intersect(intersect(intersect(factor(df_nm$hh),factor(df_db$hh)),factor(df_hf$hh)),factor(df_nm_zero$hh)),factor(df_q$hh))
df_nm_zero<-df_nm_zero[is.element(df_nm_zero$hh,list_hh),]
df_nm<-df_nm[is.element(df_nm$hh,list_hh),]
df_hf<-df_hf[is.element(df_hf$hh,list_hh),]
df_db<-df_db[is.element(df_db$hh,list_hh),]
df_q<-df_q[is.element(df_q$hh,list_hh),]
factor(df_nm$hh)
factor(df_db$hh)
factor(df_hf$hh)

df_nm_zero_15 <- subset(df_nm_zero,(df_nm_zero$house_type=='SFH15'))
df_nm_zero_45 <- subset(df_nm_zero,(df_nm_zero$house_type=='SFH45'))
df_nm_zero_100 <- subset(df_nm_zero,(df_nm_zero$house_type=='SFH100'))

df_nm_15 <- subset(df_nm,(df_nm$house_type=='SFH15'))
df_nm_45 <- subset(df_nm,(df_nm$house_type=='SFH45'))
df_nm_100 <- subset(df_nm,(df_nm$house_type=='SFH100'))

df_db_15 <- subset(df_db,(df_db$house_type=='SFH15'))
df_db_45 <- subset(df_db,(df_db$house_type=='SFH45'))
df_db_100 <- subset(df_db,(df_db$house_type=='SFH100'))

df_hf_15 <- subset(df_hf,(df_hf$house_type=='SFH15'))
df_hf_45 <- subset(df_hf,(df_hf$house_type=='SFH45'))
df_hf_100 <- subset(df_hf,(df_hf$house_type=='SFH100'))

df_q_15 <- subset(df_q,(df_q$house_type=='SFH15'))
df_q_45 <- subset(df_q,(df_q$house_type=='SFH45'))
df_q_100 <- subset(df_q,(df_q$house_type=='SFH100'))

df_15<-smartbind(df_nm_15,df_db_15,df_hf_15,df_nm_zero_15,df_q_15)
df_45<-smartbind(df_nm_45,df_db_45,df_hf_45,df_nm_zero_45,df_q_45)
df_100<-smartbind(df_nm_100,df_db_100,df_hf_100,df_nm_zero_100,df_q_100)

pairwise.wilcox.test(df_15$LCOE,df_15$cap,paired=TRUE)
pairwise.wilcox.test(df_45$LCOE,df_45$cap,paired=TRUE)
pairwise.wilcox.test(df_100$LCOE,df_100$cap,paired=TRUE)



df_15_tank<-subset(df_15,df_15$conf==2)
df_45_tank<-subset(df_45,df_45$conf==2)
df_100_tank<-subset(df_100,df_100$conf==2)

df_15_batt<-subset(df_15,df_15$conf==4)
df_45_batt<-subset(df_45,df_45$conf==4)
df_100_batt<-subset(df_100,df_100$conf==4)
pairwise.wilcox.test(df_15_tank$P_drained_max,df_15_tank$cap,paired=TRUE)
pairwise.wilcox.test(df_45_tank$P_drained_max,df_45_tank$cap,paired=TRUE)
pairwise.wilcox.test(df_100_tank$P_drained_max,df_100_tank$cap,paired=TRUE)
pairwise.wilcox.test(df_15_batt$P_drained_max,df_15_batt$cap,paired=TRUE)
pairwise.wilcox.test(df_45_batt$P_drained_max,df_45_batt$cap,paired=TRUE)
pairwise.wilcox.test(df_100_batt$P_drained_max,df_100_batt$cap,paired=TRUE)

tapply(df_15_batt$P_drained_max, df_15_batt$cap, median)
tapply(df_45_batt$P_drained_max, df_45_batt$cap, median)
tapply(df_100_batt$P_drained_max, df_100_batt$cap, median)
tapply(df_15_tank$P_drained_max, df_15_tank$cap, median)
tapply(df_45_tank$P_drained_max, df_45_tank$cap, median)
tapply(df_100_tank$P_drained_max, df_100_tank$cap, median)

df_all<-rbind(df_15,df_45,df_100)
df_all$ht=factor(df_all$house_type,levels=c("SFH15","SFH45","SFH100"))


p_p <- ggplot(data=df_all) 
p_p <- p_p + geom_boxplot(aes(x=factor(df_all$conf),
                              y=df_all$P_drained_max),outlier.size = 0.2,
                          coef=1, lwd=0.3, alpha=1)
p_p <- p_p +  facet_grid(df_all$ht~df_all$cap, scales = "free_y",
                         labeller=as_labeller(c("2"="PVSC and DLS","3"="PVSC, DLS and DPS","SFH15"="SFH15",
                                                "SFH45"="SFH45","SFH100"="SFH100",
                                                "normal"="CT=9.39 USD/kW",'double'='CT=18.78 USD/kW','half'='CT=4.695 USD/kW')))
p_p <- p_p +scale_x_discrete(breaks=c(2,4),
                             labels=c('Tank SH','Batt'))
p_p <- p_p + theme_bw(base_size = 16)+labs(x= 'System configuration',y="Peak power\n[kW]")
p_p <- p_p +theme(axis.text.x=element_text(angle=90,hjust=1,vjust=.5))
p_p<-p_p + scale_y_continuous(limits=c(0,20))

p_p <- p_p  + theme_bw()
p_p


p_p <- ggplot(data=df_45) 
p_p <- p_p + geom_boxplot(aes(x=factor(df_45$conf),
                              y=df_45$P_drained_max),outlier.size = 0.2,
                          coef=1, lwd=0.3, alpha=1)
p_p <- p_p +  facet_grid(df_45$cap~df_45$App_comb, scales = "free_y",
                         labeller=as_labeller(c("2"="PVSC and DLS","3"="PVSC, DLS and DPS","SFH15"="SFH15",
                                                "SFH45"="SFH45","SFH100"="SFH100",
                                                "normal"="normal",'double'='double','half'='half')))
p_p <- p_p +scale_x_discrete(breaks=c(0,1,2,3,4,5,6,7),
                             labels=c('Baseline','DHW','TS','TS &\n DHW','Batt','Batt &\nDHW','Batt &\n TS','Batt &\n TS & DHW'))
p_p <- p_p + theme_bw(base_size = 16)+labs(x= 'System configuration',y="Peak power\n[kW]")
p_p <- p_p +theme(axis.text.x=element_text(angle=90,hjust=1,vjust=.5))
p_p<-p_p + scale_y_continuous(limits=c(0,15))

p_p <- p_p  + theme_bw()
p_p

p_p <- ggplot(data=df_100) 
p_p <- p_p + geom_boxplot(aes(x=factor(df_100$conf),
                              y=df_100$P_drained_max),outlier.size = 0.2,
                          coef=1, lwd=0.3, alpha=1)
p_p <- p_p +  facet_grid(df_100$cap~df_100$App_comb, scales = "free_y",
                         labeller=as_labeller(c("2"="PVSC and DLS","3"="PVSC, DLS and DPS","SFH15"="SFH15",
                                                "SFH45"="SFH45","SFH100"="SFH100",
                                                "normal"="normal",'double'='double','half'='half')))
p_p <- p_p +scale_x_discrete(breaks=c(0,1,2,3,4,5,6,7),
                             labels=c('Baseline','DHW','TS','TS &\n DHW','Batt','Batt &\nDHW','Batt &\n TS','Batt &\n TS & DHW'))
p_p <- p_p + theme_bw(base_size = 16)+labs(x= 'System configuration',y="Peak power\n[kW]")
p_p <- p_p +theme(axis.text.x=element_text(angle=90,hjust=1,vjust=.5))
#p_p<-p_p + scale_y_continuous(limits=c(0,15))

p_p <- p_p  + theme_bw()
p_p



