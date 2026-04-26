from PyQt5.QtCore import pyqtSignal, QObject
import time
import numpy as np

__version__='1.4'
__date__ = '2026.04.03'

class Static_measurement_params():
    def __init__(self):      
        self.attach_min_x = -40
        self.attach_max_x = 40
        '''
        Если вперёд по Y выступ 20 мм, назад 0:
        attach_min_y = 0, attach_max_y = +20
        '''
        self.attach_min_y = -35
        self.attach_max_y = 35
        '''
        Если колесо ниже сопла на 12 мм (выступ вниз, т.е. к столу), и вверх насадка не выступает:
        attach_min_z = -12, attach_max_z = 0
        если у штампа есть свободный ход по вертикали, то 
        self.attach_min_z_unsafe - это минимальное расстояние от сопла до нижней части штампа
        self.attach_min_z_safe - это максимальное расстояние от сопла до нижней части штампа
        '''
        self.attach_min_z_unsafe=-100
        self.attach_min_z_safe=-104
        self.attach_max_z = 0.0
        
        self.bed_thickness=18
        
        self.x_start=247
        self.x_stop=265
        self.x_step=1
        
        self.y_start=160
        self.y_stop=180
        self.y_step=1
        
       
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
       
        self.file_path=file_path
        
        self.is_running=False
        
        self.z_safe=abs(self.params.attach_min_z_safe)+self.params.bed_thickness+10
        self.z_contact=abs(self.params.attach_min_z_safe)+self.params.bed_thickness-2
        
    def run(self,log_time=True,log_data=True):

        ### main loop

        try:
       
            velocity_mm_s=100
            accel_mm_s2=500
            self.printer.set_motion_limits(velocity_mm_s=velocity_mm_s, accel_mm_s2=accel_mm_s2)
            
            self.printer.set_attached_limits(min_x=self.params.attach_min_x,
                                            max_x=self.params.attach_max_x,
                                            min_y=self.params.attach_min_y,
                                            max_y=self.params.attach_max_y,
                                            min_z=self.params.attach_min_z_unsafe-self.params.bed_thickness,
                                            max_z=self.params.attach_max_z)
            
            # self.printer.set_bed_temperature(30)
    
            X_array=np.arange(self.params.x_start,self.params.x_stop,self.params.x_step)
            Y_array=np.arange(self.params.y_start,self.params.y_stop,self.params.y_step)
            ii=0
            N_steps=len(X_array)*len(Y_array)
       
            for x in X_array:
                for y in Y_array:
                    time_tic_1=time.time()
                    self.printer.safe_y_pass(x=x, y_start=y, y_end=y, z_safe=self.z_safe, z_contact=self.z_safe)
            

            
                    FBGs_pristine=self.it.get_averaged_single_FBG_measurement()


                    
                    self.printer.move_absolute(x=x, y=y, z=self.z_contact, speed_mm_s=velocity_mm_s)

            
                    FBGs_pressured=self.it.get_averaged_single_FBG_measurement()
                    
                    if log_data:
                        s = '  Out of contact: ' + ", ".join(
                            "[" + ", ".join(f"{x:.3f}" for x in inner) + "]"
                            for inner in FBGs_pristine
                            ) + "]"
                        self.S_print.emit(s)
                        s = '       In contact: ' + ", ".join(
                            "[" + ", ".join(f"{x:.3f}" for x in inner) + "]"
                            for inner in FBGs_pressured
                            ) + "]"
                        self.S_print.emit(s)
                        
                    temp_bed=self.printer.get_bed_temperature()[0]
                    temp_chamber=self.printer.get_chamber_temperature()[0]
                    
                    self.printer.move_absolute(x=x, y=y, z=self.z_safe, speed_mm_s=velocity_mm_s)
                    
                    if log_time:
                        ii+=1
                        time_tic_2=time.time()
                        time_remaining=(N_steps-ii+1)*(time_tic_2-time_tic_1)
                        self.S_print.emit('Scanning at X={} Y={}, step {} of {}, time elapsed for step {:.1f} s, time remaining={:.0f} min {:.1f} s'.format(x,y,ii,N_steps,(time_tic_2-time_tic_1),time_remaining//60,np.mod(time_remaining,60)))


                    with open(self.file_path+'.static','a') as f:
                        f.write(str([int(x),int(y),temp_bed, temp_chamber,FBGs_pristine,FBGs_pressured])+'\n')
                        
                    if not self.is_running:
                        self.S_print_error.emit('Scanning interrupted')
                        return
                        
            self.S_print.emit('Static scanning finished')
            self.S_finished.emit()
            
        except Exception as e:
            self.S_print_error.emit('Error while static measurement:' + str(e))
