
import pickle
import matplotlib.pyplot as plt
import numpy as np
from PyQt5.QtCore import QObject,pyqtSignal
from AFR_interrogator.FBGRecorder import read_fbg_stream_raw_lp
from scipy.optimize import minimize

__version__='2'
__date__ = '2026.04.15'


wheelset_width=70

class Dynamical_meas_processor(QObject):
    S_print=pyqtSignal(str) # signal used to print into main text browser
    S_print_error=pyqtSignal(str) # signal used to print errors into main text browser
    S_weight_calculated=pyqtSignal(float)
 
    def __init__(self, path_to_file:str,
                 channels_to_plot,
                 FBGs_to_plot,
                 calibration_file_path=None):
        QObject.__init__(self)
        self.file_name=path_to_file
        
        self.times=None
        self.FBGs_map=None
        self.channels=None
        self.channel_list=None
        self.FBGs_list=None
        self.other_params=None
        
        self.channels_to_plot=channels_to_plot
        self.FBGs_to_plot=FBGs_to_plot
        
        if calibration_file_path!=None:
            self.calibration_file_path=calibration_file_path
            self.load_calibration_data()
        else:
            self.calibration_file_path=None
            self.dict_calibration=None
      
        
    def load_data(self):

        

        self.times, self.channels, self.channel_list, self.FBGs_list,self.other_params = read_fbg_stream_raw_lp(self.file_name)
        self.S_print.emit('In this file there are channels {} and FBGs {} in these channels'.format(self.channel_list,self.FBGs_list))
        self.figs_fbgs=[]
        self.S_print.emit('Other parameters of the record are {} '.format(self.other_params))       
          
   
    def load_calibration_data(self):
        with open(self.calibration_file_path,'rb') as f:
            self.dict_calibration=pickle.load(f)
   
   
#%%
    def plot(self):
        colors = plt.cm.tab10.colors
        self.figs_fbgs=[]
        for ch in self.channels_to_plot:
            N_FBG=len(self.FBGs_to_plot[ch-1])
            if N_FBG>1:
                    
                fig,axes=plt.subplots(nrows=N_FBG,sharex=True)
                self.figs_fbgs.append(fig)
                fig.supxlabel("Time, s")
                fig.supylabel("FBG wavelength, nm")
                for ii,FBG in enumerate(self.FBGs_to_plot[ch-1]):
                    axes[ii].plot(self.times - self.times[0], self.channels[ch][ii+1],color=colors[ii % len(colors)])
                    axes[ii].set_title(f"FBG {FBG}", loc="left", fontsize=10, pad=2)
                plt.suptitle('ch {} of {}, v_y={} mm/s'.format(ch, self.file_name.split('.')[0], self.other_params['y_velocity']))
                                        

            else: 
                fig=plt.figure()
                self.figs_fbgs.append(fig)
                plt.xlabel("Time, s")
                plt.ylabel("FBG wavelength, nm")
                plt.plot(self.times - self.times[0], self.channels[ch][self.FBGs_to_plot[ch-1][0]])
                plt.title('FBG {}, ch {} of "{}"'.format(self.FBGs_to_plot[ch-1][0],ch, self.file_name.split('.fbgs')[0]))
                
           
            plt.tight_layout()
                
        plt.show()
   
    def get_maximum_shifts(self):
        time_window=0.2
        time_window_index=int(time_window/(self.times[1] - self.times[0]))
        dict_shifts={}
        for ch in self.channels_to_plot:
            dict_shifts[ch]={}
            N_FBG=len(self.FBGs_to_plot[ch-1])
            for ii,FBG in enumerate(self.FBGs_to_plot[ch-1]):
                
                initial_wavelength=np.mean(self.channels[ch][ii+1][0:time_window_index])
                index_max=np.argmax(abs(self.channels[ch][ii+1]))
                maximum_wavelength=np.mean(self.channels[ch][ii+1][int(index_max-time_window/2):int(index_max+time_window/2)])
                dict_shifts[ch][FBG]=maximum_wavelength-initial_wavelength
        return dict_shifts
                                        
    def _cost_function(self,x,dict_calibration,dict_shifts):
        weight, x_left_wheel=x
        cost=0
        for ch in self.channels_to_plot:
            for ii,FBG in enumerate(self.FBGs_to_plot[ch-1]):
                predicted_signal=weight*(FBG_static_response_function(x_left_wheel,*dict_calibration[ch][FBG])+FBG_static_response_function(x_left_wheel+wheelset_width,*dict_calibration[ch][FBG]))
                cost+=abs(dict_shifts[ch][FBG]-predicted_signal)
        return cost
 
    def calculate_weight(self):
        dict_shifts=self.get_maximum_shifts()
        x0=[50,30]
        result = minimize(self._cost_function,  x0,  args=(self.dict_calibration, dict_shifts),   method="BFGS")
        weight,x_0=result.x
        return weight,x_0
    
    def calculate_weight_from_file(self,file_path):
        
        self.file_name=file_path
        self.load_data()
        weight,x_0=self.calculate_weight()
        self.S_weight_calculated.emit(weight,x_0,x_0+wheelset_width)
        return weight,x_0,x_0+wheelset_width
   
def FBG_static_response_function(x,A,x_0,w):
    return np.exp(-(x-x_0)**2/w**2)*A


#%%
if __name__=='__main__':
    #
    path_to_file=r"D:\Ilya\1.fbgs"



  