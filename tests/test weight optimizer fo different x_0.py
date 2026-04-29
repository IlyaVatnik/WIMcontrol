# -*- coding: utf-8 -*-
"""
Created on Mon Apr 27 13:31:57 2026

@author: Илья
"""

from test_weight_optimizer import test_optimizer,plot_calibration
import numpy as np
import matplotlib.pyplot as plt
import pickle

    
def create_calibration(N_FBG):
    calibration={}
    calibration[1]={}
    x_i=np.linspace(-120, 120,N_FBG)
    for ii in range(N_FBG):
        calibration[1][ii+1]={}
        calibration[1][ii+1]['params']=np.array([-0.01,x_i[ii],30])
    return calibration

calibration_file_path=r"F:\!Projects\!WIM\2026.04.26 data\static\weight=160 g try 4.setup_calib"
with open(calibration_file_path,'rb') as f:
    calibration=pickle.load(f)
    
calibration[1][6]={}
calibration[1][7]={}
calibration[1][6]['params']=[-0.0015,-50,30]
calibration[1][7]['params']=[-0.0015,32,20]


# calibration=create_calibration(17)

plot_calibration(calibration)
W_true = 160          # г
xl_true_array = np.arange(-100,50,10)        # мм
wheelset_width=50        # мм (расстояние между колёсами 90 мм)

noise_level=0.00 # nm

xl_opt_array=np.zeros(len(xl_true_array))
wheelset_width_array=np.zeros(len(xl_true_array))
W_opt_array=np.zeros(len(xl_true_array))
for ii,xl in enumerate(xl_true_array):
    W_opt, xl_opt, wheelset_width_opt, xr_opt,iterations,history=test_optimizer(W_true,xl,xl+wheelset_width,calibration,noise_level=noise_level)
    xl_opt_array[ii]=xl_opt
    wheelset_width_array[ii]=wheelset_width_opt
    W_opt_array[ii]=W_opt
    

    
fig,axes=plt.subplots(3,1,sharex=True)
axes[0].plot(xl_true_array,W_opt_array,'o')
axes[0].set_ylabel('Weight, g')
axes[1].plot(xl_true_array,xl_opt_array, 'o',color='red')
axes[1].set_ylabel('Position of the left wheel')
axes[2].plot(xl_true_array,wheelset_width_array,'o',color='green')
axes[2].set_ylabel('Wheelset width, mm')
axes[2].set_xlabel('Position of the left wheel, mm')
plt.tight_layout()
plt.show()