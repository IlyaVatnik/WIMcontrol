
import pickle
import matplotlib.pyplot as plt
import numpy as np
from PyQt5.QtCore import QObject,pyqtSignal
from AFR_interrogator.FBGRecorder import read_fbg_stream_raw_lp
from scipy.optimize import minimize
import os
__version__='2.3'
__date__ = '2026.04.26'




class Dynamical_meas_processor(QObject):
    S_print=pyqtSignal(str) # signal used to print into main text browser
    S_print_error=pyqtSignal(str) # signal used to print errors into main text browser
    S_weight_calculated=pyqtSignal(float,float,float)
 
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
      
        
    def load_data(self, logging=True):

        

        self.times, self.channels, self.channel_list, self.FBGs_list,self.other_params = read_fbg_stream_raw_lp(self.file_name)
        
        self.figs_fbgs=[]
        if logging:
            self.S_print.emit('In this file there are channels {} and FBGs {} in these channels'.format(self.channel_list,self.FBGs_list))
            self.S_print.emit('Other parameters of the record are {} '.format(self.other_params))       
          
   
    def load_calibration_data(self):
        with open(self.calibration_file_path,'rb') as f:
            self.dict_calibration=pickle.load(f)
        self.plot_calibration_data()
            
    def plot_calibration_data(self):
        for ch in self.channels_to_plot:
            plt.figure()
            colors = plt.cm.tab10.colors
            plt.title(self.calibration_file_path)
            plt.xlabel('Position, mm')
            plt.ylabel('Response, nm/g')
            coords=np.arange(-300,300)
    
            for FBG in self.FBGs_to_plot[ch-1]:
                plt.plot(coords,FBG_static_response_function(coords,*self.dict_calibration[ch][FBG]['params']),
                         color=colors[FBG-1],
                         label='FBG '+str(FBG)+' w={:.2f} nm'.format(self.dict_calibration[ch][FBG]['wavelength']))
   
            plt.legend()
            plt.title(f'Channel {ch}')
            plt.tight_layout()
            plt.show()
#%%
    def plot(self, show_max_shifts=False):
        if show_max_shifts:
            dict_shifts,max_response=self.get_maximum_shifts_from_experiment()
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
                    axes[ii].plot(self.times - self.times[0], self.channels[ch][FBG],color=colors[ii % len(colors)])
                    axes[ii].set_title(f"FBG {FBG}", loc="left", fontsize=10, pad=2)
                    if show_max_shifts:
                        axes[ii].axhline( self.channels[ch][FBG][0]+dict_shifts[ch][FBG],linestyle='--',color=colors[ii % len(colors)])
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
   
    def get_maximum_shifts_from_experiment(self):
        time_window=0.1
        time_window_index=int(time_window/(self.times[1] - self.times[0]))
        dict_shifts={}
        max_response=[0,0,0]
        for ch in self.channels_to_plot:
            dict_shifts[ch]={}
            for ii,FBG in enumerate(self.FBGs_to_plot[ch-1]):
                initial_wavelength=np.mean(self.channels[ch][FBG][0:time_window_index])
                index_max=np.argmax(abs(self.channels[ch][FBG]-initial_wavelength))
                maximum_wavelength=np.mean(self.channels[ch][FBG][int(index_max-time_window/2):int(index_max+time_window/2)])
                dict_shifts[ch][FBG]=maximum_wavelength-initial_wavelength
                if abs(max_response[0])<abs(dict_shifts[ch][FBG]):
                    max_response=[dict_shifts[ch][FBG],ch,FBG]
                # print(initial_wavelength,maximum_wavelength,FBG)
        return dict_shifts,max_response
                             

            
    def _cost_function(self,x,dict_calibration,dict_shifts):
        weight, x_left_wheel, wheelset_width=x
        cost=0
        for ch in self.channels_to_plot:
            for ii,FBG in enumerate(self.FBGs_to_plot[ch-1]):
                predicted_signal=weight/2*(FBG_static_response_function(x_left_wheel,*dict_calibration[ch][FBG]['params'])+FBG_static_response_function(x_left_wheel+wheelset_width,*dict_calibration[ch][FBG]['params']))
                cost+=(dict_shifts[ch][FBG]-predicted_signal)**2
                # cost+=((dict_shifts[ch][FBG]-predicted_signal)/predicted_signal)**2
                # print(predicted_signal,dict_shifts[ch][FBG],ch,FBG)
        return cost
 
    def calculate_weight(self):
        dict_shifts,max_response=self.get_maximum_shifts_from_experiment()
        x_l_guess=self.dict_calibration[max_response[1]][max_response[2]]['params'][1]
        weight_guess=max_response[0]/self.dict_calibration[max_response[1]][max_response[2]]['params'][0]
        wheelset_width_guess=50
        guess=[weight_guess,x_l_guess,wheelset_width_guess]
        bounds=[(0,1000),(-105,105),(0,200)]
        result = minimize(self._cost_function,  guess,  bounds=bounds, args=(self.dict_calibration, dict_shifts))
        weight_opt,x_l_opt,wheelset_width_opt=result.x
        x_r_opt=x_l_opt+wheelset_width_opt
        print(weight_opt,x_l_opt,x_r_opt)
        return weight_opt,x_l_opt,x_r_opt,result.message
    
    def calculate_weight_from_file(self,file_path):
        try:
            self.file_name=file_path
            self.load_data(logging=False)
            weight,x_l,x_r, message=self.calculate_weight()
            self.S_weight_calculated.emit(weight,x_l,x_r)
            self.S_print.emit('Weight={:.2f} g, x_l={:.2f} mm, x_r={:.2f} mm ;  '.format(weight,x_l,x_r)+message)
            
            # print()
            return weight,x_l,x_r
        
        except Exception as e:
            self.S_print_error.emit(str(e))
            print(e)
   
def FBG_static_response_function(x,A,x_0,w):
    return np.exp(-(x-x_0)**2/w**2)*A


def process_folder(p:Dynamical_meas_processor, path_to_folder:str):
    file_list=os.listdir(path_to_folder)
    weights=np.zeros(len(file_list)) 
    lengths=np.zeros(len(file_list)) 
    x_ls=np.zeros(len(file_list)) 
    positions=np.zeros(len(file_list)) 
    positions_of_the_wheelset_center=np.zeros(len(file_list))
    for ii,file in enumerate(file_list): 
        position=float(file.split('x=')[1].split(' mm')[0])
        weight,x_l,x_r=p.calculate_weight_from_file(path_to_folder+'\\'+file)
        print(file, weight,x_l,x_r)
        weights[ii]=weight
        lengths[ii]=(x_r-x_l)
        x_ls[ii]=x_l
        positions[ii]=position
        positions_of_the_wheelset_center[ii]=(x_r+x_l)/2
        
    
    fig,axes=plt.subplots(4,1,sharex=True)
    axes[0].plot(positions,weights,'o')
    axes[0].set_ylabel('Weight, g')
    axes[1].plot(positions,x_ls, 'o',color='red')
    axes[1].set_ylabel('Position of the left wheel')
    axes[2].plot(positions,lengths,'o',color='green')
    axes[2].set_ylabel('Wheelset width, mm')
    axes[3].plot(positions,positions_of_the_wheelset_center,'o',color='black')
    axes[3].set_ylabel('Wheelset center, mm')
    
    
    axes[3].set_xlabel('Position of the headtool, mm')
    

#%%
if __name__=='__main__':
    
    path_to_file=r"F:\!Projects\!WIM\2026.05.06\80 g\x=0 mm forward N=3.fbgs"
    
    
    #%% 
    # path_to_folder=r'F:\!Projects\!WIM\2026.05.06\80 g'
    # path_to_file=None
    #%%
    calibration_file_path=r"F:\!Projects\!WIM\WIMcontrol\calibrations\weight=87 g 5 слоев.setup_calib"
    p=Dynamical_meas_processor(path_to_file, [1,2], [[1,2,3,4,5],[1,2,3,4,5]],calibration_file_path=calibration_file_path)
    #%%
    p.load_data()
    p.plot(show_max_shifts=True)
    p.calculate_weight()
    #%%
    # process_folder(p, path_to_folder)
    


  