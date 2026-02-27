
import pickle
import matplotlib.pyplot as plt
import numpy as np
import ast
from scipy.interpolate import griddata
from PyQt5.QtCore import QObject,pyqtSignal
from matplotlib import cm

from AFR_interrogator.FBGRecorder import read_spectra_from_file as read_spectra_from_file

__version__='1.0'
__date__ = '2026.02.27'

class Spectra_meas_processor(QObject):
    S_print=pyqtSignal(str) # signal used to print into main text browser
    S_print_error=pyqtSignal(str) # signal used to print errors into main text browser
 
    def __init__(self, path_to_file:str,
                 channels_to_plot):
        QObject.__init__(self)
        self.file_name=path_to_file
        self.channels_to_plot=channels_to_plot

        
        
        

        
# Открываем файл для чтения

            
    def plot_3d(self):
        for ch in self.channels_to_plot:
            times,waves,spectra,other_params=read_spectra_from_file(self.file_name,ch)
            self.S_print.emit('Average acqisition rate is {} Hz '.format(1/np.mean(np.diff(times))))
            self.S_print.emit('Other parameters of the record are {} '.format(other_params))
            fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
            X, Y = np.meshgrid(waves, times)  # X,Y shape (Ny, Nx)
            ax.plot_surface(X,Y, spectra.T, cmap=cm.coolwarm, linewidth=0, antialiased=False)
            plt.ylabel('Time, s')
            plt.xlabel('Wavelength, nm')
            plt.gca().set_zlabel('Spectral power, dBm')

    

#%%
if __name__=='__main__':
    path_to_file=r"D:\Ilya\2026.02.12 static\3.static"
    p=Static_meas_processor(path_to_file, channels_to_plot=[1], FBGs_to_plot=[[1,2,3]])
    p.plot_all_3d_plots()
    # p.plot_along_coord(250, 'Y', 1, 1)

# plot_3d(coords,temps_bed)
# plt.xlabel('X, mm')
# plt.ylabel('Y, mm')
# plt.gca().set_zlabel("Bed temperature")
# plt.tight_layout()

# plot_3d(coords,temps_chamber)
# plt.xlabel('X, mm')
# plt.ylabel('Y, mm')
# plt.gca().set_zlabel("Chamber temperature")
# plt.tight_layout()



  