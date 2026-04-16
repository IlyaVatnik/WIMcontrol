# -*- coding: utf-8 -*-
"""
Created on Thu Apr 16 19:24:39 2026

@author: Ilya
"""
import pickle
import matplotlib.pyplot as plt
import numpy as np
from PyQt5.QtCore import QObject,pyqtSignal
from AFR_interrogator.FBGRecorder import read_fbg_stream_raw_lp
from scipy.optimize import minimize
import os

from WIMcontrol.processing.process_dynamical_data import Dynamical_meas_processor

path_to_folder=r"D:\Ilya\2026.04.16 dynamical measurements\160 g"
calibration_file_path=r"D:\Ilya\WIMcontrol\calibrations\weight=86 g.setup_calib"
p=Dynamical_meas_processor(None, [1], [[1,2,3,4,5]],calibration_file_path=calibration_file_path)

file_list=os.listdir(path_to_folder)
weights=[]
lengths=[]
for file in file_list: 
    
    weight,x_l,x_r=p.calculate_weight_from_file(path_to_folder+'\\'+file)
    print(file, weight,x_l,x_r)
    weights.append(weight)
    lengths.append(x_r-x_l)
    
fig,axes=plt.subplots(2,1,sharex=True)
axes[0].plot(weights)
axes[0].set_ylabel('Weight, g')
axes[1].plot(lengths)
axes[1].set_ylabel('Length, mm')
