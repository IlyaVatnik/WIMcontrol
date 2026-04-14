
import pickle
import matplotlib.pyplot as plt
import numpy as np
from PyQt5.QtCore import QObject,pyqtSignal
from AFR_interrogator.FBGRecorder import read_fbg_stream_raw_lp

__version__='1.0'
__date__ = '2026.04.10'

class Dynamical_meas_processor(QObject):
    S_print=pyqtSignal(str) # signal used to print into main text browser
    S_print_error=pyqtSignal(str) # signal used to print errors into main text browser
    S_weight_calculated=pyqtSignal(float)
 
    def __init__(self, path_to_file:str,
                 channels_to_plot,
                 FBGs_to_plot,):
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
      
        
    def load_data(self):

        

        self.times, self.channels, self.channel_list, self.FBGs_list,self.other_params = read_fbg_stream_raw_lp(self.file_name)
        self.S_print.emit('In this file there are channels {} and FBGs {} in these channels'.format(self.channel_list,self.FBGs_list))
        self.figs_fbgs=[]
        self.S_print.emit('Other parameters of the record are {} '.format(self.other_params))       
          
   
   
   
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
   
 
    def calculate_weight(self):
        return 0
   

    

#%%
if __name__=='__main__':
    #
    path_to_file=r"D:\Ilya\1.fbgs"



  