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
        calibration[1][ii+1]['params']=np.array([-0.002,x_i[ii],30])
    return calibration

calibration=create_calibration(32)
#%%

# calibration_file_path="D:\Ilya\WIMcontrol\calibrations\weight=87 g 5 слоев.setup_calib"
# with open(calibration_file_path,'rb') as f:
#     calibration=pickle.load(f)
    
# calibration[1][6]={}
# calibration[1][6]['params']=[-0.003,0,30]
# calibration[1][7]={}
# calibration[1][7]['params']=[-0.0015,-32,20]
# calibration[1][8]={}
# calibration[1][8]['params']=[-0.003,30,30]
# calibration[1][9]={}
# calibration[1][9]['params']=[-0.0015,70,20]





#%%


plot_calibration(calibration)
W_true = 160          # г
xl_true_array = np.arange(-40,40,4)        # мм
N=5
xl_true_array=np.repeat(xl_true_array, N)
wheelset_width=50        # мм (расстояние между колёсами)

noise_level=0.03 # nm

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
axes[0].set_title(f'Weight={np.mean(W_opt_array):.1f} g +- {np.std(W_opt_array):.2f} g ')
axes[1].plot(xl_true_array,xl_opt_array, 'o',color='red')
axes[1].set_ylabel('Position of the left wheel')
axes[2].plot(xl_true_array,wheelset_width_array,'o',color='green')
axes[2].set_ylabel('Wheelset width, mm')
axes[2].set_title(f'width={np.mean(wheelset_width_array):.1f} mm +- {np.std(wheelset_width_array):.2f} mm ')
axes[2].set_xlabel('Position of the left wheel, mm')
plt.tight_layout()
plt.show()