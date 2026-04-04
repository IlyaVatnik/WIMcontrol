
import pickle
import matplotlib.pyplot as plt
import numpy as np
import ast
from scipy.interpolate import griddata
from PyQt5.QtCore import QObject,pyqtSignal

__version__='1.1'
__date__ = '2026.04.05'

class Long_term_meas_processor(QObject):
    S_print=pyqtSignal(str) # signal used to print into main text browser
    S_print_error=pyqtSignal(str) # signal used to print errors into main text browser
 
    def __init__(self, path_to_file:str,
                 channels_to_plot,
                 FBGs_to_plot):
        QObject.__init__(self)
        self.file_name=path_to_file
        
        
        
        
        self.times=None
        self.FBGs_map=None
        
        self.channels_to_plot=channels_to_plot
        self.FBGs_to_plot=FBGs_to_plot
      
        self.load_data()
        
    def load_data(self):

        
        with open(self.file_name, 'r') as file:
            
            N_FBGs_list=None
            while N_FBGs_list==None:
                line = file.readline().strip()   # читаем только одну строку 
                data = ast.literal_eval(line)
                try: 
                    N_FBGs_list=[len(x) for x in data[1]]
                except TypeError:
                    continue
            times=[data[0]]
            FBGs_map=[data[1]]
            
            
            
            for line in file:
                # Убираем пробелы и символы новой строки
                line = line.strip()
                
                try:
                    data = ast.literal_eval(line)
                    if [len(x) for x in data[1]]==N_FBGs_list: ## добавляет только те строки, где количество решеток равно начальному.
                        times.append(data[0])
                        FBGs_map.append(data[1])
                        

                    # Преобразование строки в список
                       
        
                    # Извлечение переменных
                except TypeError:
                    pass

        
                except (ValueError, SyntaxError) as e:
                    self.S_print_error.emit(f"Ошибка при обработке строки: {line}. Ошибка: {e}")
        self.times=np.array(times)
        self.FBGs_map=FBGs_map

        # FBGs=np.array(FBGs_map)
        return times, FBGs_map
   
        
    def _extract_FBG_wavelengths(self,FBGs_map,ch,FBG_number):
        FBG_wavelengths=[]
        try:
            for line in FBGs_map:
                try:
                    FBG_wavelengths.append(line[ch-1][FBG_number-1])
                except:
                    FBG_wavelengths.append(np.nan)
            return np.array(FBG_wavelengths)
        except IndexError:
            self.S_print_error.emit('there is no {} FBG in {} channel'.format(FBG_number, ch))
        except TypeError as e:
            self.S_print_error.emit('Error while extracting {} FBG in {} channel:'.format(FBG_number, ch)+str(e))
  
#%%
    def plot(self):
        self.figs_fbgs=[]
        for ch in self.channels_to_plot:
            N_FBG=len(self.FBGs_to_plot[ch-1])
            if N_FBG>1:
                
                fig,axes=plt.subplots(nrows=N_FBG,sharex=True)
                self.figs_fbgs.append(fig)
                fig.supxlabel("Time, min")
                fig.supylabel("FBG wavelength, nm")
                for ii,FBG in enumerate(self.FBGs_to_plot[ch-1]):
                    FBG_dynamics=self._extract_FBG_wavelengths(self.FBGs_map,ch,ii)
                    axes[ii].plot(self.times/60,FBG_dynamics)
                    axes[ii].set_title(f"FBG {FBG}", loc="left", fontsize=10, pad=2)
                plt.suptitle('ch {} of {}'.format(ch,  self.file_name.split('.')[0]))
                                    
   
            else: 
                
                fig=plt.figure()
                self.figs_fbgs.append(fig)
                plt.xlabel("Time, min")
                plt.ylabel("FBG wavelength, nm")
                FBG_dynamics=self._extract_FBG_wavelengths(self.FBGs_map,ch,0)
                plt.plot(self.times/60,FBG_dynamics)
                plt.title('FBG {}, ch {} of "{}"'.format(self.params.it.FBGs[ch-1][0],ch, self.file_name.split('.')[0]))
                
           
            plt.tight_layout()
         
        plt.show()     
   
 

   

    

#%%
if __name__=='__main__':
    path_to_file=r"D:\Ilya\2026.02.12 static\3.static"



  