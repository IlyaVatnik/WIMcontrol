# -*- coding: utf-8 -*-
"""
Created on Thu Feb 12 14:41:16 2026

@author: Ilya
"""
from PyQt5.QtCore import pyqtSignal, QObject, QTimer
import time
import numpy as np
from AFR_interrogator.FBGRecorder import record_to_file_from_queue, FrameFanout,record_spectra_to_file
from queue import Queue

__version__='1.3'
__date__ = '2026.02.27'


MAX_SIZE_QUEUE=5000

class Dynamical_measurement_params():
    def __init__(self):      
        self.attach_min_x = -50 
        self.attach_max_x = 50
        '''
        Если вперёд по Y выступ 20 мм, назад 0:
        attach_min_y = 0, attach_max_y = +20
        '''
        self.attach_min_y = -30
        self.attach_max_y = 30
        '''
        Если колесо ниже сопла на 12 мм (выступ вниз, т.е. к столу), и вверх насадка не выступает:
        attach_min_z = -12, attach_max_z = 0
        '''
        self.attach_min_z = -45
        self.attach_max_z = 0.0
        
        self.bed_thickness=20
        
        self.x_start=250
        self.x_stop=260
        self.x_step=2
        
        self.y_start=120
        self.y_stop=200
        self.y_velocity=50
        
        self.z_safe=90
        self.z_contact=70
        
        self.write_every_nth=3
        
        self.plot_live_plot=False
        self.N_repetitions_at_each_x=1
        self.include_reverse=False
        self.type_of_data_to_record='FBG peaks'
        

class Dynamical_measurement(QObject):
  
    S_finished=pyqtSignal()  # signal to finish
    S_print=pyqtSignal(str) # signal used to print into main text browser
    S_print_error=pyqtSignal(str) # signal used to print errors into main text browser
    S_finished=pyqtSignal()  # signal to finish
    S_plot_queue_ready = pyqtSignal(object)   # передаем Queue для GUI live-plot
    def __init__(self,
                 it,
                 printer,
                 params,
                 folder_path,
                 channels,
                 FBGs):
        super().__init__()
        self.it=it
        self.printer=printer
        self.params=params ## Dynamical_measurement_params

        self.folder_path=folder_path
        self.channels=channels
        self.FBGs=FBGs
        
        self.is_running=False
        
        self.fan=None
        
        self.safe_velocity_mm_s=100
        

        
    def save_data(self,path,time_to_save,other_params):
        if self.params.type_of_data_to_record=='FBG peaks':
            self.it.start_freq_stream()
            q_rec = Queue(maxsize=MAX_SIZE_QUEUE)
            self.fan.add_consumer_queue(q_rec)
            time.sleep(0.01)
            
            # Запись (без GUI) — из q_rec
            record_to_file_from_queue(
                it=self.it,
                q_rec=q_rec,
                filepath=path+'.fbgs',
                duration_sec=time_to_save,
                write_every_n=self.params.write_every_nth,
                channels=self.channels,
                FBGs=self.FBGs,
                other_params=other_params,
                warmup_sec=0.1*time_to_save
            )
            
            self.fan.remove_consumer_queue(q_rec)
            self.it.stop_freq_stream()
        elif self.params.type_of_data_to_record=='Spectra':
            record_spectra_to_file(self.it,
                                   write_every_n=self.params.write_every_nth,
                                   filepath=path+'.spectra',
                                   duration_sec=time_to_save,
                                   channels=self.channels,
                                   other_params=other_params
                                   )
        
    def run(self,log=True):
        
        self.printer.set_attached_limits(min_x=self.params.attach_min_x,
                                         max_x=self.params.attach_max_x,
                                         min_y=self.params.attach_min_y,
                                         max_y=self.params.attach_max_y,
                                         min_z=self.params.attach_min_z-self.params.bed_thickness,
                                         max_z=self.params.attach_max_z)
        
        ### main loop
        if self.params.y_velocity>self.printer.cfg.max_velocity_mm_s:
            self.S_print_error.emit('Velocity along y exceeds the limits set for the printer in printer configuration script')
            self.S_print_error.emit('Stop dynamical measurements')
            return
        

       

        # self.printer.set_bed_temperature(30)

        X_array=np.arange(self.params.x_start,self.params.x_stop,self.params.x_step)
        ii=0
        N_steps=len(X_array)
        try:
            time_tic_1=time.time()
            # Очереди для self.fanout

            self.fan = FrameFanout(self.it, idle_sleep=0.0002)
            self.fan.start()

            # Сообщаем GUI, что можно подключаться к q_plot (если включен live plot)

            if self.params.plot_live_plot:
                q_plot = Queue(maxsize=MAX_SIZE_QUEUE)
                self.fan.add_consumer_queue(q_plot)
                self.S_plot_queue_ready.emit(q_plot)
                # if self.params.type_of_data_to_record=='Spectra':
                #     self.it.start_freq_stream()

    
            time_to_save=1.5*calc_time_of_moving(abs(self.params.y_stop-self.params.y_start),self.params.y_velocity,self.printer.cfg.max_accel_mm_s2)
            self.S_print.emit('Time for one movement is {:.2f} s'.format(time_to_save))
           
            for x in X_array:

                    
                    if log:
                        ii+=1
                        time_tic_2=time.time()
                        time_remaining=(N_steps-ii)*(time_tic_2-time_tic_1)
                        self.S_print.emit('Scanning at X={} , step {} of {}, time remaining={:.0f} min {:.1f} s'.format(x,ii,N_steps,time_remaining//60,np.mod(time_remaining,60)))
                        time_tic_1=time_tic_2
                        
                    
                    for jj in range(self.params.N_repetitions_at_each_x):
                        
                        d=self.printer.get_position()
                        x_c=d['x']
                        y_c=d['y']
                        if x_c!=x or y_c!=self.params.y_start:
                            self.printer.safe_y_pass(x=x,y_start=self.params.y_start, y_end=self.params.y_start,
                                                     z_safe=self.params.z_safe,z_contact=self.params.z_safe,
                                                     approach_speed_mm_s=self.safe_velocity_mm_s)
                    
                        self.printer.move_z(z=self.params.z_contact, speed_mm_s=self.safe_velocity_mm_s)
                    
            
                        
                        
                        path=self.folder_path+'//'+'x={} mm forward N={}'.format(x,jj)
                        d={}
                        d['X']=x
                        d['bed_temp']=self.printer.get_bed_temperature()[0]
                        d['chamber_temp']=self.printer.get_chamber_temperature()[0]
                        d['y_start']=self.params.y_start
                        d['y_stop']=self.params.y_stop
                        d['z_contact']=self.params.z_contact
                        d['y_velocity']=self.params.y_velocity
                        
                        
                        # self.it.start_freq_stream(self.params.rep_rate if hasattr(self.params, "rep_rate") else None)

                        
                        self.printer.move_absolute(x=x, y=self.params.y_stop, z=self.params.z_contact,
                                                   speed_mm_s=self.params.y_velocity, wait=False)
     
                        self.save_data(path, time_to_save, other_params=d)
                     
                        
                        if not self.is_running:
                            self.interrupted('Scanning interrupted')
                            return
                        
                        if self.params.include_reverse:
                            path=self.folder_path+'//'+'x={} mm backward N={}'.format(x,jj)
                            d={}
                            d['X']=x
                            d['bed_temp']=self.printer.get_bed_temperature()[0]
                            d['chamber_temp']=self.printer.get_chamber_temperature()[0]
                            d['y_start']=self.params.y_stop
                            d['y_stop']=self.params.y_start
                            d['z_contact']=self.params.z_contact
                            d['y_velocity']=self.params.y_velocity
                            
                            
                            # self.it.start_freq_stream(self.params.rep_rate if hasattr(self.params, "rep_rate") else None)
  
                            self.printer.move_absolute(x=x, y=self.params.y_start, z=self.params.z_contact,
                                                       speed_mm_s=self.params.y_velocity, wait=False)
         
                   
                            self.save_data(path, time_to_save, other_params=d)
                            
                    
                        
                    
                    
                    if not self.is_running:
                        self.interrupted('Scanning interrupted')
                        return
                        
            self.S_finished.emit()
            self.interrupted('Dynamical scanning finished',error=False)
        except Exception as e:
            self.interrupted('Error while dynamical measurement:' + str(e),error=True)

            
    def interrupted(self,message,error=False):
        if error:
            self.S_print_error.emit(message)
        else:
            self.S_print.emit(message)
        self.it.stop_freq_stream()
        self.fan.stop(timeout=1.0)
        self.printer.move_z(z=self.params.z_safe, speed_mm_s=self.safe_velocity_mm_s)
        
def calc_time_of_moving(length, speed,acc):
    t_acc=speed/acc
    length_acc=t_acc**2*acc
    if length/2<=length_acc:
        time=2*np.sqrt(length/acc)
        return time
    else:
        length_stable_speed=length-2*length_acc
        time_stable_speed=length_stable_speed/speed
        return 2*t_acc+time_stable_speed

if __name__=='__main__':
    from AFR_interrogator.interrogator import Interrogator
    from Printer_control.Printer import Printer, PrinterConfig

            
    it = Interrogator('10.2.15.150','10.2.15.158')
    printer=Printer(PrinterConfig(base_url="http://10.2.15.109:7125"))
    folder_path=r"D:\Ilya\WIMcontrol\data"
    params=Dynamical_measurement_params()
    measure=Dynamical_measurement(it, printer, params, folder_path,[1],[[1,2,3]])
    measure.is_running=True
    measure.params.plot_live_plot=True
    measure.run()
