# -*- coding: utf-8 -*-
"""
Created on Fri Mar 20 13:52:48 2026

@author: Admin
"""


__version__='1.0'
__date__ = '2026.03.24'
import numpy as np
from PyQt5.QtCore import pyqtSignal, QObject
import time

#%%
class Long_term_measurement_params():
    def __init__(self):      
        self.sleep_time = 10
        self.duration = 100
        self.file_name=''

class Long_term_measurement(QObject):
    S_finished=pyqtSignal()  # signal to finish
    S_print=pyqtSignal(str) # signal used to print into main text browser
    S_print_error=pyqtSignal(str) # signal used to print errors into main text browser
    def __init__(self,
                 it,
                 params,
                 file_path):
        super().__init__()
        self.it=it
        self.params=params ## Dynamical_measurement_params
        self.is_running=False
        self.file_path=file_path

    
        
    def run(self):
        time0=time.time()
        time_current=0
        try:
            while time_current<self.params.duration:
                
                self.S_print.emit('Time ={:.1f} min of {:.1f} min'.format(time_current/60,self.params.duration/60))
                FBGs=self.it.get_averaged_single_FBG_measurement()
                with open(self.file_path,'a') as f:
                    f.write(str([time_current,FBGs])+'\n')
                time.sleep(self.params.sleep_time)
                time_current=time.time()-time0
                if not self.is_running:
                    self.S_print_error.emit('Long term measurement interrupted')
                    return
            self.S_print.emit('Long term measurement finished')
            self.S_finished.emit()
        except (Exception, KeyboardInterrupt) as e:
            self.S_print_error.emit('Error while long term measurement:' + str(e))

       
    
   #%%
