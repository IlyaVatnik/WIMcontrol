from PyQt5.QtCore import pyqtSignal, QObject
import time
import numpy as np

__version__='1.1'
__date__ = '2026.02.13'

class Static_measurement_params():
    def __init__(self):      
        self.attach_min_x = -15
        self.attach_max_x = 15
        '''
        Если вперёд по Y выступ 20 мм, назад 0:
        attach_min_y = 0, attach_max_y = +20
        '''
        self.attach_min_y = -5
        self.attach_max_y = 0
        '''
        Если колесо ниже сопла на 12 мм (выступ вниз, т.е. к столу), и вверх насадка не выступает:
        attach_min_z = -12, attach_max_z = 0
        '''
        self.attach_min_z = -100.0
        self.attach_max_z = 0
        
        self.x_start=247
        self.x_stop=265
        self.x_step=1
        
        self.y_start=160
        self.y_stop=180
        self.y_step=1
        
        self.z_safe=130
        self.z_contact=122
        
        self.file_name_to_save_static_meas='1'

class Static_measurement(QObject):
  
    S_finished=pyqtSignal()  # signal to finish
    S_print=pyqtSignal(str) # signal used to print into main text browser
    S_print_error=pyqtSignal(str) # signal used to print errors into main text browser
    S_finished=pyqtSignal()  # signal to finish

    def __init__(self,
                 it,
                 printer,
                 params,
                 file_path):
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
        self.file_path=file_path
        
        self.is_running=False
        
    def run(self,log_time=True,log_data=True):

        ### main loop

        
       
        velocity_mm_s=100
        accel_mm_s2=500
        self.printer.set_motion_limits(velocity_mm_s=velocity_mm_s, accel_mm_s2=accel_mm_s2)
        # self.printer.set_bed_temperature(30)

        X_array=np.arange(self.params.x_start,self.params.x_stop,self.params.x_step)
        Y_array=np.arange(self.params.y_start,self.params.y_stop,self.params.y_step)
        ii=0
        N_steps=len(X_array)*len(Y_array)
        try:
            time_tic_1=time.time()
            for x in X_array:
                for y in Y_array:
                    if log_time:
                        ii+=1
                        time_tic_2=time.time()
                        time_remaining=(N_steps-ii)*(time_tic_2-time_tic_1)
                        self.S_print.emit('Scanning at X={} Y={}, step {} of {}, time elapsed for step {:.1f} s, time remaining={:.0f} min {:.1f} s'.format(x,y,ii,N_steps,(time_tic_2-time_tic_1),time_remaining//60,np.mod(time_remaining,60)))
                        time_tic_1=time_tic_2
                   
                    self.printer.safe_y_pass(x=x, y_start=y, y_end=y, z_safe=self.params.z_safe, z_contact=self.params.z_safe)
            
                    time.sleep(0.1)
            
                    FBGs_pristine=self.it.get_averaged_single_FBG_measurement()
                    if log_data:
                        self.S_print.emit(str(FBGs_pristine))
                    
                    self.printer.move_absolute(x=x, y=y, z=self.params.z_contact, speed_mm_s=velocity_mm_s)
                    time.sleep(0.1)
            
                    FBGs_pressured=self.it.get_averaged_single_FBG_measurement()
                    if log_data:
                        self.S_print.emit(str(FBGs_pressured))
                    temp_bed=self.printer.get_bed_temperature()[0]
                    temp_chamber=self.printer.get_chamber_temperature()[0]
                    
                    self.printer.move_absolute(x=x, y=y, z=self.params.z_safe, speed_mm_s=velocity_mm_s)

                    with open(self.file_path+'.static','a') as f:
                        f.write(str([int(x),int(y),temp_bed, temp_chamber,FBGs_pristine,FBGs_pressured])+'\n')
                        
                    if not self.is_running:
                        self.S_print_error.emit('Scanning interrupted')
                        return
                        
            self.S_print.emit('Static scanning finished')
            self.S_finished.emit()
            
        except Exception as e:
            self.S_print_error.emit('Error while static measurement:' + str(e))
