# -*- coding: utf-8 -*-
"""
Created on Thu Feb 12 14:41:16 2026

@author: Ilya
"""
from PyQt5.QtCore import pyqtSignal, QObject
import time
import numpy as np
from AFR_interrogator.FBGRecorder import record_to_file

__version__='1.0'
__date__ = '2026.02.12'

class Dynamical_measurement(QObject):
  
    S_finished=pyqtSignal()  # signal to finish
    S_print=pyqtSignal(str) # signal used to print into main text browser
    S_print_error=pyqtSignal(str) # signal used to print errors into main text browser
    S_finished=pyqtSignal()  # signal to finish

    def __init__(self,
                 it,
                 printer,
                 params,
                 folder_path):
        super().__init__()
        self.it=it
        self.printer=printer
        self.params=params
        self.printer.set_attached_limits(min_x=self.params.attach_min_x,
                                         max_x=self.params.attach_max_x,
                                         min_y=self.params.attach_min_y,
                                         max_y=self.params.attach_max_y,
                                         min_z=self.params.attach_min_z,
                                         max_z=self.params.attach_max_z)
        self.folder_path=folder_path
        
        self.is_running=False
        
    def run(self,log=True):

        ### main loop

        
       
        velocity_mm_s=100
        accel_mm_s2=500
        self.printer.set_motion_limits(velocity_mm_s=velocity_mm_s, accel_mm_s2=accel_mm_s2)
        # self.printer.set_bed_temperature(30)

        X_array=np.arange(self.params.x_start,self.params.x_stop,self.params.x_step)
        ii=0
        N_steps=len(X_array)
        try:
            time_tic_1=time.time()
            for x in X_array:
             
                    if log:
                        ii+=1
                        time_tic_2=time.time()
                        time_remaining=(N_steps-ii)*(time_tic_2-time_tic_1)
                        self.S_print.emit('Scanning at X={} , step {} of {}, time remaining={:.0f} min {:.1f} s'.format(x,ii,N_steps,time_remaining//60,np.mod(time_remaining,60)))
                        time_tic_1=time_tic_2
                   
                    self.printer.safe_y_pass(x=x, y_start=self.params.y_start, y_end=self.params.y_start, z_safe=self.params.z_safe, z_contact=self.params.z_safe)
                    time_to_save=(self.params.y_stop-self.params.y_start)/self.params.y_velocity
                    path=self.folder_path+'//'+'x={} mm.fbgs'.format(x)
                    d={}
                    d['X']=x
                    d['bed_temp']=self.printer.get_bed_temperature()[0]
                    d['chamber_temp']=self.printer.get_chamber_temperature()[0]
                    d['exp_params']=self.params
                    record_to_file(self.it, self.folder_path, time_to_save+1,time_to_save+1,write_every_n=self.params.write_every_nth,params=d)
                    self.printer.safe_y_pass(x=x, y_start=self.params.y_start, y_end=self.params.y_stop, z_safe=self.params.z_safe, z_contact=self.params.z_contact, travel_speed_mm_s=self.params.y_velocity)
                    
                        
                    if not self.is_running:
                        self.S_print_error.emit('Scanning interrupted')
                        return
                        
            self.S_print.emit('Dynamical scanning finished')
            self.S_finished.emit()
            
        except Exception as e:
            self.S_print_error.emit('Error while dynamical measurement:' + str(e))
