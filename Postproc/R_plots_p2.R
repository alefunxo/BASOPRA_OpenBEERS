library(dplyr)
library(ggplot2)
library(ggpubr)
library(ggtern)
library(ggrepel)
library(adklakedata)
library(ade4)
library(adegraphics)
library(grid)
library(gtools)

getwd()
#read the dataframe

df<-read.table('df_wilcox_paired_original.csv',sep=',',header=TRUE,stringsAsFactors = FALSE)
head(df)
#post_proc_R
#df1<-read.table('post_proc_R.csv',sep=',',header=TRUE)
#df1 <- subset(df1,df1$conf%%2==0)

df_crem<-read.table('original_peaks.csv',sep=',',header=FALSE,stringsAsFactors = FALSE)
df_crem$conf<-8
df_crem$App_comb<-2
df_crem2<-read.table('original_peaks.csv',sep=',',header=FALSE,stringsAsFactors = FALSE)
df_crem2$conf<-8
df_crem2$App_comb<-3

df_crem<-rbind(df_crem,df_crem2)
df_crem1<-data.frame(df_crem)
df_crem2<-data.frame(df_crem)
df_crem3<-data.frame(df_crem)
df_crem1$house_type<-"SFH15"
df_crem2$house_type<-"SFH45"
df_crem3$house_type<-"SFH100"
df_crem<-rbind(df_crem1,df_crem2,df_crem3)
names(df_crem)
names(df_crem)<-c("hh",'P_drained_max','conf','App_comb','house_type')

head(df_crem)
df1<-smartbind(df,df_crem)
lapply(df1, class)

df1$ht=factor(df1$house_type,levels=c("SFH15","SFH45","SFH100"))
df1$conf=factor(df1$conf,levels=c('8','0','1','2','3','4','5','6','7'))
df1<-transform(df1, comb_power = pmax(P_drained_max, P_injected_max))

dummy1 <- data.frame(expand.grid(X = seq(1, dim(df1)[1], by=1) ,
                                 P_drained_max = 4.84,
                                 P_max=17.12))
#Now plot the power data for power




p_p <- ggplot(data=df1) 
p_p <- p_p + geom_boxplot(aes(x=factor(df1$conf),
                              y=df1$comb_power),outlier.size = 0.2,
                          coef=1, lwd=0.3, alpha=1)

p_p <- p_p + geom_hline(aes(yintercept=dummy1$P_drained_max ),
                        colour='red',linetype = "dashed",size=0.5, alpha=0.4)

p_p <- p_p +  facet_grid(df1$ht~df1$App_comb, scales = "free_y",
                         labeller=as_labeller(c("2"="PVSC and DLS","3"="PVSC, DLS and DPS","SFH15"="SFH15",
                                                "SFH45"="SFH45","SFH100"="SFH100")))
p_p <- p_p +scale_x_discrete(breaks=c(8,0,1,2,3,4,5,6,7),
                             labels=c('No HP &\n No PV','Baseline','DHW tank','Tank SH',
                                      'Tank SH &\n DHW','Batt',
                                      'Batt &\n tank DHW','Batt &\n tank SH','Batt & tank SH\n & DHW'))
p_p <- p_p + theme_bw(base_size = 14)+labs(x= 'System configuration',y="Peak grid import\n[kW]")
p_p <- p_p +theme(axis.text.x=element_text(angle=90,hjust=1,vjust=.5))
p_p<-p_p + scale_y_continuous(limits=c(0,25))


p_p
g1 <- ggplot_gtable(ggplot_build(p_p))
strip_r <- which(grepl('strip-r', g1$layout$name))
fills <- c("#00AFBB", "#E7B800", "#FC4E07")
k <- 1
for (i in strip_r) {
  j <- which(grepl('rect', g1$grobs[[i]]$grobs[[1]]$childrenOrder))
  g1$grobs[[i]]$grobs[[1]]$children[[j]]$gp$fill <- fills[k]
  k <- k+1
}
grid.draw(g1)
ggsave('Img/peak_plot.pdf',plot=grid.draw(g1))
#,outlier.shape = NA
df1<-subset(df1,df1$conf!=8)


p_lc <- ggplot(data=df1) 
p_lc <- p_lc + geom_boxplot(aes(x=factor(df1$conf),
                                y=df1$LCOE),outlier.size = 0.2,
                            coef=1, lwd=0.3, alpha=1)
p_lc <- p_lc + facet_grid(df1$ht~df1$App_comb,scales = "free_y",
                          labeller=as_labeller(c("2"="PVSC and DLS","3"="PVSC, DLS and DPS","SFH15"="SFH15",
                                                 "SFH45"="SFH45","SFH100"="SFH100")))
p_lc <- p_lc + scale_x_discrete(breaks=c(0,1,2,3,4,5,6,7),
                                labels=c('Baseline','DHW tank','Tank SH',
                                         'Tank SH &\n DHW','Batt','Batt &\n tank DHW',
                                         'Batt &\n tank SH','Batt & tank SH\n & DHW'))
p_lc <- p_lc + scale_y_continuous(limits=c(0.3,1.2))

p_lc <- p_lc + theme_bw(base_size = 14)+labs(x= 'System configuration',y="LCOE\n[USD/kWh]")
p_lc <- p_lc + theme(axis.text.x=element_text(angle=90,hjust=1,vjust=.5))

g <- ggplot_gtable(ggplot_build(p_lc))
strip_r <- which(grepl('strip-r', g$layout$name))
fills <- c("#00AFBB", "#E7B800", "#FC4E07")
k <- 1
for (i in strip_r) {
  j <- which(grepl('rect', g$grobs[[i]]$grobs[[1]]$childrenOrder))
  g$grobs[[i]]$grobs[[1]]$children[[j]]$gp$fill <- fills[k]
  k <- k+1
}
grid.draw(g)
ggsave('Img/lcoe_plot.pdf',plot=grid.draw(g))

tapply(df1$LCOE, df1$conf, summary)



################################################################################################


#Plot for the poster

df1<-read.table('df_wilcox_paired_original.csv',sep=',',header=TRUE)
#post_proc_R
#df1<-read.table('post_proc_R.csv',sep=',',header=TRUE)
#df1 <- subset(df1,df1$conf%%2==0)

df_crem<-read.table('original_peaks.csv',sep=',',header=FALSE)
df_crem$conf<-8
df_crem$App_comb<-2
df_crem2<-read.table('original_peaks.csv',sep=',',header=FALSE)
df_crem2$conf<-8
df_crem2$App_comb<-3

df_crem<-rbind(df_crem,df_crem2)
df_crem1<-data.frame(df_crem)
df_crem2<-data.frame(df_crem)
df_crem3<-data.frame(df_crem)
df_crem1$house_type<-'SFH15'
df_crem2$house_type<-'SFH45'
df_crem3$house_type<-'SFH100'
df_crem<-rbind(df_crem1,df_crem2,df_crem3)
names(df_crem)
names(df_crem)<-c("hh",'P_drained_max','conf','App_comb','house_type')

df1<-smartbind(df1,df_crem)
df1$ht=factor(df1$house_type,levels=c("SFH15","SFH45","SFH100"))
df1$conf=factor(df1$conf,levels=c('8','0','1','2','3','4','5','6','7'))

dummy1 <- data.frame(expand.grid(X = seq(1, dim(df1)[1], by=1) ,
                                 P_drained_max = 4.84,
                                 P_max=17.12))
p_p<-p_p+labs(subtitle = "A")

g1 <- ggplot_gtable(ggplot_build(p_p))
strip_r <- which(grepl('strip-r', g1$layout$name))
fills <- c("#00AFBB", "#E7B800", "#FC4E07")
k <- 1
for (i in strip_r) {
  j <- which(grepl('rect', g1$grobs[[i]]$grobs[[1]]$childrenOrder))
  g1$grobs[[i]]$grobs[[1]]$children[[j]]$gp$fill <- fills[k]
  k <- k+1
}
df1<-subset(df1,df1$conf!=8)
p_lc<-p_lc+labs(subtitle = "B")


g <- ggplot_gtable(ggplot_build(p_lc))
strip_r <- which(grepl('strip-r', g$layout$name))
fills <- c("#00AFBB", "#E7B800", "#FC4E07")
k <- 1
for (i in strip_r) {
  j <- which(grepl('rect', g$grobs[[i]]$grobs[[1]]$childrenOrder))
  g$grobs[[i]]$grobs[[1]]$children[[j]]$gp$fill <- fills[k]
  k <- k+1
}
p_tss<-p_tss+labs(subtitle = "C",face="bold")
p<-p+labs(subtitle = "D",face="bold")
grid.arrange(g1,g,p_tss,p)


ggsave('Img/poster_plot.eps',plot=grid.arrange(g1,g,p_tss,p),width=15, height=8.5)









################################################################################################
#Now we concentrate in comparison of Tank for space heating and battery trade-offs (only when PS)


df_c3<-subset(df1 , df1$App_comb== 3 & (df1$conf==2|df1$conf==4|df1$conf==0))
df_c31<-subset(df_c3,df_c3$ht=='SFH15')
df_c32<-subset(df_c3,df_c3$ht=='SFH45')
df_c33<-subset(df_c3,df_c3$ht=='SFH100')
centroids <- aggregate(cbind(df_c3$LCOE,df_c3$P_drained_max)~df_c3$conf+df_c3$ht,df_c3,median)



ncol(df_c3)
df.temp <- df_c3[1:9,]
df.temp$LCOE <- centroids$V1
df.temp$P_drained_max <- centroids$V2
df.temp$conf <- centroids$`df_c3$conf`
df.temp$ht<-centroids$`df_c3$ht`
df.temp$centroids <- TRUE
df_c3$centroids<-rep(FALSE,nrow(df_c3))
df_c3_modif <- rbind(df_c3,df.temp)
df_c3_modif$jit<-with(df_c3_modif, ifelse(ht == "SFH45", 0.2, 0))

p <- ggplot(df_c3_modif,
            aes(x=LCOE, y=P_drained_max,fill=factor(ht),colour=factor(ht),shape=factor(ht)))
p <- p + geom_point(data=subset(df_c3_modif,centroids==FALSE),size=0.7)
p <- p + geom_point(data=subset(df_c3_modif,centroids==TRUE),size=5,colour="black")
#p <- p + geom_text
p <- p + geom_text_repel(data=subset(df_c3_modif,centroids==TRUE),
                         hjust=-0.5,
                         nudge_y=1,
                         force=10,
                         aes(label = paste("(",
                                           paste(round(LCOE,2), round(P_drained_max,1), sep = ",")
                                           ,")",sep=""),fontface = 'bold'),color='black')
p <- p +  scale_shape_manual(values=c(21, 22, 23))
p <- p + scale_colour_manual(values = c("#00AFBB", "#E7B800", "#FC4E07")) 
p <- p + scale_fill_manual(values = c("#00AFBB", "#E7B800", "#FC4E07")) 
p <- p + facet_grid(~conf,
                    labeller=as_labeller(c('0'='Baseline','1'='DHW','2'='Tank SH','3'='TS &\n DHW',
                                           '4'='Batt','5'='Batt &\nDHW','6'='Batt &\n TS',
                                           '7'='Batt &\n TS & DHW',
                                           "SFH15"="SFH15","SFH45"="SFH45","SFH100"="SFH100")))
p <- p + labs(fill = "Type of house",shape="Type of house",colour="Type of house")
p <- p + xlab('LCOE [USD/kWh]')
p <- p + ylab('Peak grid import\n[kW]')
p <- p + theme_bw()
p <- p + theme(axis.text=element_text(size=14),
               axis.title=element_text(size=14,face="bold"))

p

ggsave('Img/lcoe_p_nodhw_plot.pdf')
#now we do the same with TSC and SS

centroids <- aggregate(cbind(df_c3$SS,df_c3$TSC)~df_c3$conf+df_c3$ht,df_c3,median)



ncol(df_c3)
df.temp <- df_c3[1:9,]
df.temp$TSC <- centroids$V2
df.temp$SS <- centroids$V1
df.temp$conf <- centroids$`df_c3$conf`
df.temp$ht<-centroids$`df_c3$ht`
df.temp$centroids <- TRUE
df_c3$centroids<-rep(FALSE,nrow(df_c3))
df_c3_modif <- rbind(df_c3,df.temp)


p_tss <- ggplot(df_c3_modif, aes(x=TSC, y=SS,fill=factor(ht),colour=factor(ht),shape=factor(ht)))
p_tss <- p_tss + geom_point(data=subset(df_c3_modif,centroids==FALSE),size=0.7)
p_tss <- p_tss + geom_point(data=subset(df_c3_modif,centroids==TRUE),size=5,colour="black")
p_tss <- p_tss + geom_text_repel(data=subset(df_c3_modif,centroids==TRUE),
                                 hjust = -1.3, nudge_y = 0.5,
                                 aes(label = paste("(",
                                                   paste(round(TSC,0), round(SS,0), sep = ",")
                                                   ,")",sep=""),fontface = 'bold'),color='black')
p_tss <- p_tss + scale_shape_manual(values=c(21, 22, 23))
p_tss <- p_tss + scale_colour_manual(values = c("#00AFBB", "#E7B800", "#FC4E07")) 
p_tss <- p_tss + scale_fill_manual(values = c("#00AFBB", "#E7B800", "#FC4E07")) 
p_tss <- p_tss + facet_grid(~conf,
                            labeller=as_labeller(c('0'='Baseline','1'='Tank DHW','2'='Tank SH','3'='Tank SH &\n DHW',
                                                   '4'='Batt','5'='Batt &\ntank DHW','6'='Batt &\ntank SH',
                                                   '7'='Batt &\ntank SH & DHW',
                                                   "SFH15"="SFH15","SFH45"="SFH45","SFH100"="SFH100")))
p_tss <- p_tss + labs(fill = "Type of house",shape="Type of house",colour="Type of house")
p_tss <- p_tss + xlab('SC [%]')
p_tss <- p_tss + ylab('SS\n[%]')
p_tss <- p_tss + theme_bw()
p_tss <- p_tss + geom_abline(aes(intercept = 0,slope=1))
p_tss <- p_tss + scale_y_continuous(limits=c(0,100))
p_tss <- p_tss + scale_x_continuous(limits=c(0,100))
p_tss <- p_tss + theme(axis.text=element_text(size=14),
                       axis.title=element_text(size=14,face="bold"))

p_tss

ggsave('Img/tsc_ss_nodhw_plot.pdf')

################################################################################################




median(df1$P_injected_max)
max(df1$P_injected_max)
min(df1$P_injected_max)

p_ip <- ggplot(data=df1) 
p_ip <- p_ip + geom_boxplot(aes(x=factor(df1$conf),
                                y=df1$P_injected_max),outlier.size = 0.2,
                            coef=1, lwd=0.3, alpha=1)
p_ip <- p_ip + facet_grid(df1$ht~df1$App_comb,scales = "free_y",
                          labeller=as_labeller(c("2"="PVSC and DLS","3"="PVSC, DLS and DPS","SFH15"="SFH15",
                                                 "SFH45"="SFH45","SFH100"="SFH100")))
p_ip <- p_ip + scale_x_discrete(breaks=c(0,1,2,3,4,5,6,7),
                                labels=c('Baseline','DHW tank','Tank SH',
                                         'Tank SH &\n DHW','Batt','Batt &\n tank DHW',
                                         'Batt &\n tank SH','Batt & tank SH\n & DHW'))

p_ip <- p_ip + theme_bw(base_size = 14)+labs(x= 'System configuration',y="Injected power\n[kW]")
p_ip <- p_ip + theme(axis.text.x=element_text(angle=90,hjust=1,vjust=.5))

g2 <- ggplot_gtable(ggplot_build(p_ip))
strip_r <- which(grepl('strip-r', g2$layout$name))
fills <- c("#00AFBB", "#E7B800", "#FC4E07")
k <- 1
for (i in strip_r) {
  j <- which(grepl('rect', g2$grobs[[i]]$grobs[[1]]$childrenOrder))
  g2$grobs[[i]]$grobs[[1]]$children[[j]]$gp$fill <- fills[k]
  k <- k+1
}
grid.draw(g2)
ggsave('Img/power_inj_plot.pdf',plot=grid.draw(g2))



p_lc <- ggplot(data=df1) 
p_lc <- p_lc + geom_boxplot(aes(x=factor(df1$conf),
                                y=df1$E_grid_batt),outlier.size = 0.2,
                            coef=1, lwd=0.3, alpha=1)
p_lc <- p_lc + facet_grid(df1$ht~df1$App_comb,scales = "free_y",
                          labeller=as_labeller(c("2"="PVSC and DLS","3"="PVSC, DLS and DPS","SFH15"="SFH15",
                                                 "SFH45"="SFH45","SFH100"="SFH100")))
p_lc <- p_lc + scale_x_discrete(breaks=c(0,1,2,3,4,5,6,7),
                                labels=c('Baseline','DHW tank','Tank SH',
                                         'Tank SH &\n DHW','Batt','Batt &\n tank DHW',
                                         'Batt &\n tank SH','Batt & tank SH\n & DHW'))
#p_lc <- p_lc + scale_y_continuous(limits=c(0.3,1.2))

p_lc <- p_lc + theme_bw(base_size = 14)+labs(x= 'System configuration',y="LCOE\n[USD/kWh]")
p_lc <- p_lc + theme(axis.text.x=element_text(angle=90,hjust=1,vjust=.5))

p_lc



p_lc <- ggplot(data=df1) 
p_lc <- p_lc + geom_boxplot(aes(x=factor(df1$conf),
                                y=df1$Bill),outlier.size = 0.2,
                            coef=1, lwd=0.3, alpha=1)
p_lc <- p_lc + facet_grid(df1$ht~df1$App_comb,scales = "free_y",
                          labeller=as_labeller(c("2"="PVSC and DLS","3"="PVSC, DLS and DPS","SFH15"="SFH15",
                                                 "SFH45"="SFH45","SFH100"="SFH100")))
p_lc <- p_lc + scale_x_discrete(breaks=c(0,1,2,3,4,5,6,7),
                                labels=c('Baseline','DHW tank','Tank SH',
                                         'Tank SH &\n DHW','Batt','Batt &\n tank DHW',
                                         'Batt &\n tank SH','Batt & tank SH\n & DHW'))
#p_lc <- p_lc + scale_y_continuous(limits=c(0.3,1.2))

p_lc <- p_lc + theme_bw(base_size = 14)+labs(x= 'System configuration',y="LCOE\n[USD/kWh]")
p_lc <- p_lc + theme(axis.text.x=element_text(angle=90,hjust=1,vjust=.5))

p_lc




df2<-subset(df1,df1$conf!=7)
factor(df1$conf)
df_c3<-subset(df2 , df2$App_comb== 3 & (df2$conf==0|df2$conf==1|df2$conf==3|df2$conf==5))
df_c31<-subset(df_c3,df_c3$ht=='SFH15')
df_c32<-subset(df_c3,df_c3$ht=='SFH45')
df_c33<-subset(df_c3,df_c3$ht=='SFH100')
centroids <- aggregate(cbind(df_c3$LCOE,df_c3$P_drained_max)~df_c3$conf+df_c3$ht,df_c3,median)



ncol(df_c3)
df.temp <- df_c3[1:12,]
df.temp$LCOE <- centroids$V1
df.temp$P_drained_max <- centroids$V2
df.temp$conf <- centroids$`df_c3$conf`
df.temp$ht<-centroids$`df_c3$ht`
df.temp$centroids <- TRUE
df_c3$centroids<-rep(FALSE,nrow(df_c3))
df_c3_modif <- rbind(df_c3,df.temp)
df_c3_modif$jit<-with(df_c3_modif, ifelse(ht == "SFH45", 0.2, 0))

p <- ggplot(df_c3_modif,
            aes(x=LCOE, y=P_drained_max,fill=factor(ht),colour=factor(ht),shape=factor(ht)))
p <- p + geom_point(data=subset(df_c3_modif,centroids==FALSE),size=0.7)
p <- p + geom_point(data=subset(df_c3_modif,centroids==TRUE),size=5,colour="black")
#p <- p + geom_text
p <- p + geom_text_repel(data=subset(df_c3_modif,centroids==TRUE),
                         hjust=-1.4,
                         aes(label = paste("(",
                                           paste(round(LCOE,2), round(P_drained_max,1), sep = ",")
                                           ,")",sep=""),fontface = 'bold'),color='black')
p <- p +  scale_shape_manual(values=c(21, 22, 23))
p <- p + scale_colour_manual(values = c("#00AFBB", "#E7B800", "#FC4E07")) 
p <- p + scale_fill_manual(values = c("#00AFBB", "#E7B800", "#FC4E07")) 
p <- p + facet_grid(~conf,
                    labeller=as_labeller(c('0'='Baseline','1'='Tank DHW','2'='Tank SH','3'='Tank SH &\n DHW',
                                           '4'='Batt','5'='Batt &\ntank DHW','6'='Batt &\ntank SH',
                                           '7'='Batt &\ntank SH & DHW',
                                           "SFH15"="SFH15","SFH45"="SFH45","SFH100"="SFH100")))
p <- p + labs(fill = "Type of house",shape="Type of house",colour="Type of house")
p <- p + xlab('LCOE [USD/kWh]')
p <- p + ylab('Power drained\n[kW]')
p <- p + theme_bw()
p <- p + theme(axis.text=element_text(size=14),
               axis.title=element_text(size=14,face="bold"))

p
ggsave('Img/tsc_ss_dhw_plot.pdf')

#now we do the same with TSC and SS

centroids <- aggregate(cbind(df_c3$SS,df_c3$TSC)~df_c3$conf+df_c3$ht,df_c3,median)



ncol(df_c3)
df.temp <- df_c3[1:12,]
df.temp$TSC <- centroids$V2
df.temp$SS <- centroids$V1
df.temp$conf <- centroids$`df_c3$conf`
df.temp$ht<-centroids$`df_c3$ht`
df.temp$centroids <- TRUE
df_c3$centroids<-rep(FALSE,nrow(df_c3))
df_c3_modif <- rbind(df_c3,df.temp)


p_tss <- ggplot(df_c3_modif, aes(x=TSC, y=SS,fill=factor(ht),colour=factor(ht),shape=factor(ht)))
p_tss <- p_tss + geom_point(data=subset(df_c3_modif,centroids==FALSE),size=0.7)
p_tss <- p_tss + geom_point(data=subset(df_c3_modif,centroids==TRUE),size=5,colour="black")
p_tss <- p_tss + geom_text_repel(data=subset(df_c3_modif,centroids==TRUE),
                                 hjust = -1.3, nudge_y = 0.5,
                                 aes(label = paste("(",
                                                   paste(round(TSC,0), round(SS,0), sep = ",")
                                                   ,")",sep=""),fontface = 'bold'),color='black')
p_tss <- p_tss + scale_shape_manual(values=c(21, 22, 23))
p_tss <- p_tss + scale_colour_manual(values = c("#00AFBB", "#E7B800", "#FC4E07")) 
p_tss <- p_tss + scale_fill_manual(values = c("#00AFBB", "#E7B800", "#FC4E07")) 
p_tss <- p_tss + facet_grid(~conf,
                            labeller=as_labeller(c('0'='Baseline','1'='Tank DHW','2'='Tank SH','3'='Tank SH &\n DHW',
                                                   '4'='Batt','5'='Batt &\ntank DHW','6'='Batt &\ntank SH',
                                                   '7'='Batt &\ntank SH & DHW',
                                                   "SFH15"="SFH15","SFH45"="SFH45","SFH100"="SFH100")))
p_tss <- p_tss + labs(fill = "Type of house",shape="Type of house",colour="Type of house")
p_tss <- p_tss + xlab('SC [%]')
p_tss <- p_tss + ylab('SS\n[%]')
p_tss <- p_tss + theme_bw()
p_tss <- p_tss + geom_abline(aes(intercept = 0,slope=1))
p_tss <- p_tss + scale_y_continuous(limits=c(0,100))
p_tss <- p_tss + scale_x_continuous(limits=c(0,100))
p_tss <- p_tss + theme(axis.text=element_text(size=14),
                       axis.title=element_text(size=14,face="bold"))

p_tss

ggsave('Img/tsc_ss_dhw_plot.pdf')


################################################################################################

df_orig <- read.table('original_peaks.csv',sep=',',header=FALSE)

head(df_orig)
names(df_orig)<-c('hh','P_drained_max')
df_orig$App_comb=3
df_orig$conf=8.
df1_aux<-rbind.fill(df1,df_orig)
df_c3<-subset(df1 , df1$App_comb== 3 & (df1$conf==0|df1$conf==2|df1$conf==4))

df_c31<-subset(df_c3,df_c3$ht=='SFH15')
df_c32<-subset(df_c3,df_c3$ht=='SFH45')
df_c33<-subset(df_c3,df_c3$ht=='SFH100')

centroids <- aggregate(cbind(df_c3$LCOE,df_c3$P_drained_max)~df_c3$conf+df_c3$ht,df_c3,median)



ncol(df_c3)
df.temp <- df_c3[1:9,]
df.temp$LCOE <- centroids$V1
df.temp$P_drained_max <- centroids$V2
df.temp$conf <- centroids$`df_c3$conf`
df.temp$ht<-centroids$`df_c3$ht`
df.temp$centroids <- TRUE
df_c3$centroids<-rep(FALSE,nrow(df_c3))
df_c3_modif <- rbind(df_c3,df.temp)
df_c3_modif$jit<-with(df_c3_modif, ifelse(ht == "SFH45", 0.2, 0))

p <- ggplot(df_c3_modif,
            aes(x=LCOE, y=P_drained_max,fill=factor(conf),colour=factor(conf),shape=factor(conf)))
p <- p + geom_point(data=subset(df_c3_modif,centroids==FALSE),size=0.7)
p <- p + geom_point(data=subset(df_c3_modif,centroids==TRUE),size=5,colour="black")
#p <- p + geom_text
p <- p + geom_text_repel(data=subset(df_c3_modif,centroids==TRUE),
                         hjust=-1.4,
                         aes(label = paste("(",
                                           paste(round(LCOE,2), round(P_drained_max,1), sep = ",")
                                           ,")",sep=""),fontface = 'bold'),color='black')
p <- p +  scale_shape_manual(values=c(21, 22, 23,24))
p <- p + scale_colour_manual(values = c("#00AFBB", "#E7B800", "#FC4E07")) 
p <- p + scale_fill_manual(values = c("#00AFBB", "#E7B800", "#FC4E07")) 
p <- p + facet_grid(~ht,
                    labeller=as_labeller(c('0'='Baseline','1'='Tank DHW','2'='Tank SH','3'='Tank SH &\n DHW',
                                           '4'='Batt','5'='Batt &\ntank DHW','6'='Batt &\ntank SH',
                                           '7'='Batt &\ntank SH & DHW',
                                           "SFH15"="SFH15","SFH45"="SFH45","SFH100"="SFH100")))
p <- p + labs(fill = "Type of house",shape="Type of house",colour="Type of house")
p <- p + xlab('LCOE [USD/kWh]')
p <- p + ylab('Power drained\n[kW]')
p <- p + theme_bw()
p <- p + theme(axis.text=element_text(size=14),
               axis.title=element_text(size=14,face="bold"))

p
##ggsave('Img/tsc_ss_dhw_plot.pdf')

#now we do the same with TSC and SS

centroids <- aggregate(cbind(df_c3$SS,df_c3$TSC)~df_c3$conf+df_c3$ht,df_c3,median)



ncol(df_c3)
df.temp <- df_c3[1:9,]
df.temp$TSC <- centroids$V2
df.temp$SS <- centroids$V1
df.temp$conf <- centroids$`df_c3$conf`
df.temp$ht<-centroids$`df_c3$ht`
df.temp$centroids <- TRUE
df_c3$centroids<-rep(FALSE,nrow(df_c3))
df_c3_modif <- rbind(df_c3,df.temp)


p_tss <- ggplot(df_c3_modif, aes(x=TSC, y=SS,fill=factor(conf),colour=factor(conf),shape=factor(conf)))
p_tss <- p_tss + geom_point(data=subset(df_c3_modif,centroids==FALSE),size=0.7)
p_tss <- p_tss + geom_point(data=subset(df_c3_modif,centroids==TRUE),size=5,colour="black")
p_tss <- p_tss + geom_text_repel(data=subset(df_c3_modif,centroids==TRUE),
                                 hjust = -1.3, nudge_y = 0.5,
                                 aes(label = paste("(",
                                                   paste(round(TSC,0), round(SS,0), sep = ",")
                                                   ,")",sep=""),fontface = 'bold'),color='black')
p_tss <- p_tss + scale_shape_manual(values=c(21, 22, 23,24))
p_tss <- p_tss + scale_colour_manual(values = c("#00AFBB", "#E7B800", "#FC4E07","black"),
                                     labels=c('0'='Baseline','1'='Tank DHW','2'='Tank SH','3'='Tank SH &\n DHW',
                                              '4'='Batt','5'='Batt &\ntank DHW','6'='Batt &\ntank SH',
                                              '7'='Batt &\ntank SH & DHW'))
p_tss <- p_tss + scale_fill_manual(values = c("#00AFBB", "#E7B800", "#FC4E07","black")) 
p_tss <- p_tss + facet_grid(~ht,
                            labeller=as_labeller(c("SFH15"="SFH15","SFH45"="SFH45","SFH100"="SFH100")))
p_tss <- p_tss + labs(fill = "Configuration",shape="Configuration",colour="Configuration")
p_tss <- p_tss + xlab('SC [%]')
p_tss <- p_tss + ylab('SS\n[%]')
p_tss <- p_tss + theme_bw()
p_tss <- p_tss + geom_abline(aes(intercept = 0,slope=1))
p_tss <- p_tss + scale_y_continuous(limits=c(0,100))
p_tss <- p_tss + scale_x_continuous(limits=c(0,100))
p_tss <- p_tss + theme(axis.text=element_text(size=14),
                       axis.title=element_text(size=14,face="bold"))

p_tss
##############################################################################################
p_tsc<- ggplot(data=df1)
p_tsc<-p_tsc + geom_boxplot(aes(x=factor(df1$conf),
                                y=df1$TSC),outlier.size = 0.2,
                            coef=1, lwd=0.3, alpha=1)
p_tsc<-p_tsc + facet_grid(df1$ht~df1$App_comb, 
                          labeller=as_labeller(c("2"="PVSC and DLS","3"="PVSC, DLS and DPS","SFH15"="SFH15",
                                                 "SFH45"="SFH45","SFH100"="SFH100")))
p_tsc<-p_tsc + scale_x_discrete(breaks=c(0,1,2,3,4,5,6,7),
                                labels=c('Baseline','Tank DHW','Tank SH','Tank SH &\n DHW','Batt','Batt &\ntank DHW','Batt &\ntank SH','Batt &\ntank SH & DHW'))
p_tsc<-p_tsc + scale_y_continuous(limits=c(0,100))

p_tsc<-p_tsc + theme_bw(base_size = 16)+labs(x= 'System configuration',y="SC\n[%]")
p_tsc<-p_tsc + theme(axis.text.x=element_text(angle=90,hjust=1,vjust=.5))
p_tsc<-p_tsc + theme_bw()

g <- ggplot_gtable(ggplot_build(p_tsc))
strip_r <- which(grepl('strip-r', g$layout$name))
fills <- c("#00AFBB", "#E7B800", "#FC4E07")
k <- 1
for (i in strip_r) {
  j <- which(grepl('rect', g$grobs[[i]]$grobs[[1]]$childrenOrder))
  g$grobs[[i]]$grobs[[1]]$children[[j]]$gp$fill <- fills[k]
  k <- k+1
}
grid.draw(g)

ggsave('Img/tsc_plot.pdf')

#SS
p_ss<- ggplot(data=df1)
p_ss<-p_ss + geom_boxplot(aes(x=factor(df1$conf),
                              y=df1$SS),outlier.size = 0.2,
                          coef=1, lwd=0.3, alpha=1)
p_ss<-p_ss + facet_grid(df1$ht~df1$App_comb, 
                        labeller=as_labeller(c("2"="PVSC and DLS","3"="PVSC, DLS and DPS","SFH15"="SFH15",
                                               "SFH45"="SFH45","SFH100"="SFH100")))
p_ss<-p_ss + scale_x_discrete(breaks=c(0,1,2,3,4,5,6,7),
                              labels=c('Baseline','Tank DHW','Tank SH','Tank SH &\n DHW','Batt','Batt &\ntank DHW','Batt &\ntank SH','Batt &\ntank SH & DHW'))
p_ss<-p_ss + scale_y_continuous(limits=c(0,100))

p_ss<-p_ss + theme_bw(base_size = 16)+labs(x= 'System configuration',y="SS\n[%]")
p_ss<-p_ss + theme(axis.text.x=element_text(angle=90,hjust=1,vjust=.5))
p_ss<-p_ss + theme_bw()

g <- ggplot_gtable(ggplot_build(p_ss))
strip_r <- which(grepl('strip-r', g$layout$name))
fills <- c("#00AFBB", "#E7B800", "#FC4E07")
k <- 1
for (i in strip_r) {
  j <- which(grepl('rect', g$grobs[[i]]$grobs[[1]]$childrenOrder))
  g$grobs[[i]]$grobs[[1]]$children[[j]]$gp$fill <- fills[k]
  k <- k+1
}
grid.draw(g)
p_ss
#ggsave('Img/ss_plot.pdf')

#Total demand
p_td<-ggplot(data=df1) 
p_td<-p_td + geom_boxplot(aes(x=factor(df1$conf),
                              y=df1$E_demand+df1$E_hp+df1$E_hpdhw+df1$E_bu+df1$E_budhw),
                          outlier.size = 0.2,coef=1, lwd=0.3, alpha=1)
p_td<-p_td + facet_grid(df1$ht~df1$App_comb,
                        labeller=as_labeller(c("2"="PVSC and DLS","3"="PVSC, DLS and DPS","SFH15"="SFH15",
                                               "SFH45"="SFH45","SFH100"="SFH100")))
p_td<-p_td + scale_x_discrete(breaks=c(0,1,2,3,4,5,6,7),
                              labels=c('Baseline','Tank DHW','Tank SH','Tank SH &\n DHW','Batt','Batt &\ntank DHW','Batt &\ntank SH','Batt &\ntank SH & DHW'))
p_td<-p_td + scale_y_continuous(limits=c(0,15000))
p_td<-p_td + theme_bw(base_size = 16)+labs(x= 'System configuration',y="Energy consumption\n[kWh/a]")
p_td<-p_td + theme(axis.text.x=element_text(angle=90,hjust=1,vjust=.5))
p_td<-p_td + theme_bw()

g <- ggplot_gtable(ggplot_build(p_td))
strip_r <- which(grepl('strip-r', g$layout$name))
fills <- c("#00AFBB", "#E7B800", "#FC4E07")
k <- 1
for (i in strip_r) {
  j <- which(grepl('rect', g$grobs[[i]]$grobs[[1]]$childrenOrder))
  g$grobs[[i]]$grobs[[1]]$children[[j]]$gp$fill <- fills[k]
  k <- k+1
}
grid.draw(g)

ggsave('Img/t_demand_plot.pdf')
#################################################
