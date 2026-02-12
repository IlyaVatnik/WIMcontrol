
import pickle
import matplotlib.pyplot as plt
import numpy as np
import ast
from scipy.interpolate import griddata
from PyQt5.QtCore import QObject,pyqtSignal

__version__='1.0'
__date__ = '2026.02.12'

class Static_meas_processor(QObject):
    S_print=pyqtSignal(str) # signal used to print into main text browser
    S_print_error=pyqtSignal(str) # signal used to print errors into main text browser
 
    def __init__(self, path_to_file:str,
                 channels_to_plot,
                 FBGs_to_plot):
        QObject.__init__(self)
        self.file_name=path_to_file
        self.channels_to_plot=channels_to_plot
        self.FBGs_to_plot=FBGs_to_plot
        
        
        
        self.coords=None
        self.temps_bed=None
        self.temps_chamber=None
        self.FBGs_map_pristine=None
        self.FBGs_map_pressed=None
        
        self.load_data()
        
# Открываем файл для чтения
    def load_data(self):

        
        with open(self.file_name, 'r') as file:
            
            N_FBGs_list=None
            while N_FBGs_list==None:
                line = file.readline().strip()   # читаем только одну строку 
                data = ast.literal_eval(line)
                try: 
                    N_FBGs_list=[len(x) for x in data[4]]
                except TypeError:
                    continue
            coords=[[data[0],data[1]]]
            temps_bed=[data[2]]
            temps_chamber=[data[3]]
            self.FBGs_map_pristine=[data[4]]
            self.FBGs_map_pressed=[data[5]]      
            
            for line in file:
                # Убираем пробелы и символы новой строки
                line = line.strip()
                
                try:
                    data = ast.literal_eval(line)
                    if [len(x) for x in data[4]]==N_FBGs_list: ## добавляет только те строки, где количество решеток равно начальному.
                        if [len(x) for x in data[5]]==N_FBGs_list:
                            self.FBGs_map_pristine.append(data[4])
                            self.FBGs_map_pressed.append(data[5])
                            coords.append([data[0],data[1]])
                            temps_bed.append(data[2])
                            temps_chamber.append(data[3])
                    # Преобразование строки в список
                       
        
                    # Извлечение переменных
                except TypeError:
                    pass

        
                except (ValueError, SyntaxError) as e:
                    print(f"Ошибка при обработке строки: {line}. Ошибка: {e}")
        self.coords=np.array(coords)
        
        self.temps_bed=np.array(temps_bed)  
        self.temps_chamber=np.array(temps_chamber)
#%%

    def get_line_along_coord(self,x0,axis,ch,FBG_number):
        Z_pristine=self.extract_FBG_wavelengths(self.FBGs_map_pristine,ch,FBG_number)
        Z_pressed=self.extract_FBG_wavelengths(self.FBGs_map_pressed,ch,FBG_number)
        Z=Z_pressed-Z_pristine
        x, y = self.coords[:, 0], self.coords[:, 1]
        if axis=='X':
            index_coord_nearest=np.argmin(abs(x-x0))
            coord_nearest=x[index_coord_nearest]
            Z_for_x0=Z[x==coord_nearest]
            coord_for_x0=y[x==coord_nearest]
        elif axis=='Y':
            index_coord_nearest=np.argmin(abs(y-x0))
            coord_nearest=y[index_coord_nearest]
            Z_for_x0=Z[y==coord_nearest]
            coord_for_x0=x[y==coord_nearest]
        return coord_for_x0,Z_for_x0,coord_nearest
        
    def plot_along_coord(self,x0,axis,ch,FBG_number):
        x,shifts,coord_nearest=self.get_line_along_coord(x0,axis,ch,FBG_number)
        fig=plt.figure()
        plt.plot(x, shifts)
        plt.xlabel('Coordinate, mm')
        plt.ylabel('Wavelength shift, nm')
        plt.title('Scanning along {}={:.1f} mm'.format(axis,coord_nearest))
        plt.tight_layout()
        D={}
        D['fig']=fig
        D['x0']=coord_nearest
        D['axis']=axis
        D['ch']=ch
        D['FBG']=FBG_number
        self.single_slice_params=D
  
        
    def plot_3d(self,coords,Z):
        x, y = coords[:, 0], coords[:, 1]
        X, Y = np.meshgrid(x, y)
        nx, ny = len(x),len(y)
        xi = np.linspace(x.min(), x.max(), nx)
        yi = np.linspace(y.min(), y.max(), ny)
        X, Y = np.meshgrid(xi, yi)
        re_Z = griddata(coords, Z, (X, Y), method="cubic")  # можно: "linear", "nearest"

    # === 2) Рисуем 3D поверхность + исходные точки ===
        fig = plt.figure(figsize=(8, 6))
        ax = fig.add_subplot(111, projection="3d")
    
        surf = ax.plot_surface(X, Y, re_Z, cmap="inferno", linewidth=0, antialiased=True, alpha=0.9)
        ax.scatter(x, y, Z, c="cyan", edgecolor="k", s=60)  # исходные измерения
        return fig,ax
    
    def plot_all_3d_plots(self):
        for ch in self.channels_to_plot:
            for FBG in self.FBGs_to_plot[ch-1]:
                
                FBG_wavelengths_pristine=self.extract_FBG_wavelengths(self.FBGs_map_pristine,ch,FBG)
                FBG_wavelengths_pressed=self.extract_FBG_wavelengths(self.FBGs_map_pressed,ch,FBG)
                try:
                    fig,ax=self.plot_3d(self.coords,FBG_wavelengths_pressed-FBG_wavelengths_pristine)
                    plt.xlabel('X, mm')
                    plt.ylabel('Y, mm')
                    ax.set_zlabel("FBG wavelength shift, nm")
                    ax.set_title("ch={} FBG={}".format(ch,FBG))
                    plt.tight_layout()
                except:
                    pass

    
    def extract_FBG_wavelengths(self,FBGs_map,ch,FBG_number):
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



  