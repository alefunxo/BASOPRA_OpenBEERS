library(dplyr)
library(ggplot2)
library(ggpubr)
library(ggtern)
library(ggrepel)
library(adklakedata)
library(ade4)
library(adegraphics)
getwd()
#read the dataframe

df1<-read.table('LCOE_sens.csv',sep=',',header=TRUE)
#post_proc_R
#df1<-read.table('post_proc_R.csv',sep=',',header=TRUE)
df1$ht=factor(df1$house_type,levels=c("SFH15","SFH45","SFH100"))
summary(df1~df1$discount_rate)
p_p <- ggplot(data=df1) 
p_p <- p_p + geom_boxplot(aes(x=factor(df1$discount_rate),
                              y=df1$LCOE),outlier.size = 0.2,
                          coef=1, lwd=0.3, alpha=1)

p_p <- p_p + theme(axis.text.x = element_text(size = 14, angle = 45, hjust = 1))
p_p <- p_p + xlab('Discount rate\n[%]')
p_p <- p_p + ylab('LCOE\n[%]')
p_p
#############################################################################
library(tidyverse)
library(scales)

df1<-read.table('CAPEX_sens.csv',sep=',',header=TRUE)
df1$ht=factor(df1$house_type,levels=c("SFH15","SFH45","SFH100"))
head(df1)
df1 <- df1[,c('CAPEX_PV', 'CAPEX_hp', 'CAPEX_batt','CAPEX_tank',
       'CAPEX_DHW','conf','App_comb','ht')]
apply(df1[,c('CAPEX_PV', 'CAPEX_hp', 'CAPEX_batt','CAPEX_tank',
             'CAPEX_DHW','App_comb','conf')], 2, function(x) max(x, na.rm = TRUE))

df1 <- subset(df1,df1$App_comb==3)
df2 <- gather(data=df1,'key', 'value', -c('conf','ht'))
df2$key <- factor(df2$key, levels = c('CAPEX_DHW','CAPEX_tank','CAPEX_batt',
                                      'CAPEX_PV', 'CAPEX_hp','conf','App_comb','ht'))

head(df2)
ks <- function (x) { number_format(accuracy = 1,
                                   scale = 1/1000,
                                   suffix = "k",
                                   big.mark = ",")(x) }
p_p <- ggplot(data=df2,aes(x=conf,y=value)) 
p_p <- p_p +  geom_bar(position="stack", stat="identity",aes(fill = key))
#p_p <- p_p +  scale_y_continuous()
p_p <- p_p +  facet_grid(~ht,
                         labeller=as_labeller(c("SFH15"="SFH15","SFH45"="SFH45","SFH100"="SFH100")))

p_p <- p_p + xlab('Configuration')
p_p <- p_p + ylab('CAPEX\n[USD]')
p_p <- p_p + theme_bw()
p_p <- p_p + scale_x_continuous(breaks=c(0,1, 2, 3,4,5,6,7),
                                label=c("Baseline","DHW","TS","TS & DHW",
                                       "Batt","Batt & DHW","Batt & TS",
                                       "Batt & TS & DHW"))
p_p <- p_p + scale_y_continuous(label = ks,limits=c(0,75000))
p_p <- p_p + theme(axis.text.x = element_text(size = 14, angle = 90, hjust = 1))

p_p

library(dplyr)
# From http://stackoverflow.com/questions/1181060
stocks <- tibble(
  time = as.Date('2009-01-01') + 0:9,
  X = rnorm(10, 0, 1),
  Y = rnorm(10, 0, 2),
  Z = rnorm(10, 0, 4)
)
head(stocks)
gather(stocks, "stock", "price", -time)

