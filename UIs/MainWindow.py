# -*- coding: utf-8 -*-
"""
Created on Wed Jan 21 11:32:18 2026

@author: Илья
"""

__version__='1.0'
__date__ = '2026.02.12'

import os
    
import numpy as np
import matplotlib.pyplot as plt
import json
import csv

import pickle

from PyQt5.QtCore import  QThread,QTimer,pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QFileDialog, QDialog,QLineEdit,QComboBox,QCheckBox,QMessageBox,QInputDialog
import time


from Printer_control.Printer import Printer, PrinterConfig
from AFR_interrogator.interrogator import Interrogator
from AFR_interrogator.FBGRecorder import read_fbg_stream_raw_lp
from processing.process_static_data import Static_meas_processor as Static_processor


from UIs.MainWindowUI import Ui_MainWindow


class Params_it():
    def __init__(self):
        self.it_IP='10.2.60.38'
        self.PC_IP='10.2.60.33'
        self.FBGs=[[1,2,3]]
        self.channels=[1]
        self.gains_auto=[0,0,0,0]
        self.gains_manual=[1,1,1,1]
        self.thresholds=[3000,3000,3000,3000]
        self.averaging_time_for_single_FBG_measurement=0.5
        self.rep_rate=2000
        self.recording_duration=10
        self.write_every_nth=10
        self.plot_live_while_recording=False
        
        
class Params_recording():
    def __init__(self):      
        self.rep_rate=2000
        self.recording_duration=10
        self.write_every_nth=10
        self.plot_live_while_recording=False

class Params_printer():
    def __init__(self):
        self.url="http://10.2.15.109:7125"
    
class Static_meas():
    def __init__(self):      
        self.attach_min_x = 0.0
        self.attach_max_x = 0.0
        '''
        Если вперёд по Y выступ 20 мм, назад 0:
        attach_min_y = 0, attach_max_y = +20
        '''
        self.attach_min_y = 0.0
        self.attach_max_y = 0.0
        '''
        Если колесо ниже сопла на 12 мм (выступ вниз, т.е. к столу), и вверх насадка не выступает:
        attach_min_z = -12, attach_max_z = 0
        '''
        self.attach_min_z = 0.0
        self.attach_max_z = 0.0
        
        self.x_start=140
        self.x_stop=160
        self.x_step=1
        
        self.y_start=140
        self.y_stop=160
        self.y_step=1
        
        self.z_safe=200
        self.z_contact=150
        
        self.file_name_to_save_static_meas='1'
        
class Dynamical_meas():
    def __init__(self):      
        self.attach_min_x = 0.0
        self.attach_max_x = 0.0
        '''
        Если вперёд по Y выступ 20 мм, назад 0:
        attach_min_y = 0, attach_max_y = +20
        '''
        self.attach_min_y = 0.0
        self.attach_max_y = 0.0
        '''
        Если колесо ниже сопла на 12 мм (выступ вниз, т.е. к столу), и вверх насадка не выступает:
        attach_min_z = -12, attach_max_z = 0
        '''
        self.attach_min_z = 0.0
        self.attach_max_z = 0.0
        
        self.x_start=140
        self.x_stop=160
        self.x_step=1
        
        self.y_start=140
        self.y_stop=160
        self.y_velocity=1
        
        self.z_safe=200
        self.z_contact=150
        
        self.write_every_nth=10
        # self.file_name_to_save_dynami_meas='1'
        
        


class Params():
    def __init__(self):
        self.it=Params_it()
        self.printer=Params_printer()
        self.record=Params_recording()
        self.static=Static_meas()
        self.dynamical=Dynamical_meas()


class ThreadedMainWindow(QMainWindow):
    
    force_static_process=pyqtSignal()
    force_dynamical_process=pyqtSignal()

    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)

        # Handle threads
        self.threads = []
        self.destroyed.connect(self.kill_threads)
        


    
    def add_thread(self, objects):
        """
        Creates thread, adds it into to-destroy list and moves objects to it.
        Thread is QThread there.
        :param objects -- list of QObjects.
        :return None
        """
        # Create new thread
        thread = QThread()

        # Add new thread to list of threads to close on app destroy.
        self.threads.append(thread)

        # Move objects to new thread.
        for obj in objects:
            obj.moveToThread(thread)

        thread.start()
        return thread

    def kill_threads(self):
        """
        Closes all of created threads for this window.
        :return: None
        """
        # Iterate over all the threads and call wait() and quit().
        for thread in self.threads:
#            thread.wait()
            thread.quit()



class MainWindow(ThreadedMainWindow):
  
    
    '''
    Initialization
    '''
    def __init__(self, parent=None,version='0.0',date='0.0.0'):
        super().__init__(parent)
        self.path_to_main=os.getcwd()
        # GUI
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.init_menu_bar()
        self.init_interface()
        
        self.saving_dir_path='data\\'
        self.file_to_load_path=None
        
        
        self.ParametersFileName='Params.txt'
        self.setWindowTitle("WIM experiment control V."+version+', released '+date)
        
        # self.it
        
        self.params=Params()
        self.load_parameters_from_file()
        
        self.it=None
        self.printer=None
        
        self.type_of_plotted_data=None

        
  
        
    def logText(self, text):
        self.ui.LogField.append(">" + text)
        
    def logWarningText(self, text):
        self.ui.LogField.append("<span style=\" font-size:8pt; font-weight:600; color:#ff0000;\" >"
                             + ">" + text + "</span>")
        
    def clear_log(self):
        """Функция, которая вызывается по нажатию кнопки и очищает LogField."""
        self.ui.LogField.clear()
        
    def init_interface(self):
        self.ui.pushButton_set_it_parameters.pressed.connect(self.set_it_parameters)
        self.ui.pushButton_set_static_measurements_params.pressed.connect(self.set_static_measurements_params)
        self.ui.pushButton_set_dynamical_measurements_params.pressed.connect(self.set_dynamical_measurements_params)
        
        self.ui.pushButton_choose_folder_to_save.clicked.connect(self.choose_folder_to_save)
        

        self.ui.pushButton_connect_it.toggled[bool].connect(self.connect_interrogator)
        self.ui.pushButton_connect_printer.pressed.connect(self.connect_printer) 
        
        self.ui.pushButton_printer_homing.pressed.connect(self.printer_homing)
        self.ui.pushButton_printer_move_bed_down.pressed.connect(self.printer_move_bed_down)
        
        self.ui.pushButton_static_measurements.toggled[bool].connect(self.static_measurements)
        
        
        
        
        

        self.ui.pushButton_choose_file_to_load.clicked.connect(self.choose_file_to_load)
        self.ui.pushButton_plot_from_file.clicked.connect(self.plot_from_file)
        self.ui.pushButton_plot_single_slice_of_static.pressed.connect(self.plot_single_slice_of_static)
        self.ui.pushButton_save_single_line_to_csv.pressed.connect(self.save_single_line_to_csv)
        
        
        self.ui.pushButton_clearLog.clicked.connect(self.clear_log)
        


        
        
        
        
      
    def init_menu_bar(self):
        self.ui.action_save_parameters.triggered.connect(self.save_parameters_to_file)
        self.ui.action_load_parameters.triggered.connect(self.load_parameters_from_file)
        self.ui.action_delete_all_figures.triggered.connect(self.delete_all_figures)      
        
        
    
        
    def connect_interrogator(self,pressed):
        if pressed:
            try:
                self.it = Interrogator(self.params.it.it_IP,self.params.it.PC_IP)
                self.set_gains()
                # self.add_thread(self.it)
                self.logText('Connected to interrogator')
            except Exception as e:
                self.logWarningText(str(e))
        else:
            del self.it
            self.logText('disconnected from interrogator')

            
    def connect_printer(self):
        try:
            self.printer = Printer(PrinterConfig(base_url=self.params.printer.url))
            # self.add_thread(self.it)
            self.logText('Connected to printer')
            
        except Exception as e:
            self.logWarningText(str(e))
   
    def printer_homing(self):
        try:
            if ask_homing_confirm(self):
                self.printer.home(confirm=False)
                self.logText('Printer successfully set to home')
                
        except Exception as e:
            self.logWarningText(str(e))
            
    def printer_move_bed_down(self):
        try:
            self.printer.move_z(z=300,speed_mm_s=25)
            self.logText('Printer bed is down')
                
        except Exception as e:
            self.logWarningText(str(e))
                  
    def set_it_parameters(self):
        '''
        open dialog with analyzer parameters
        '''
        d = get_parameters(self.params.it)
        from UIs.it_parameters_dialogUI import Ui_Dialog
        it_parameters_dialog = QDialog()
        ui = Ui_Dialog()
        ui.setupUi(it_parameters_dialog)
        set_widget_values(it_parameters_dialog,d)
        if it_parameters_dialog.exec_() == QDialog.Accepted:
            params=get_widget_values(it_parameters_dialog)
            set_parameters(self.params.it,params)
            if self.it!=None:
                self.set_gains()
                self.it.averaging_time_for_single_FBG_measurement=self.params.it.averaging_time_for_single_FBG_measurement
            
    def set_gains(self):
        for ch in range(self.it.channels):
            self.it.set_gain(ch+1, auto=self.params.it.gains_auto[ch], manual_level=self.params.it.gains_manual[ch])
            self.it.set_threshold(ch+1, self.params.it.thresholds[ch])
            
    def set_recording_parameters(self):
        '''
        open dialog with analyzer parameters
        '''
        d = get_parameters(self.params.record)
        from UIs.recording_parameters_dialogUI import Ui_Dialog
        parameters_dialog = QDialog()
        ui = Ui_Dialog()
        ui.setupUi(parameters_dialog)
        set_widget_values(parameters_dialog,d)
        if parameters_dialog.exec_() == QDialog.Accepted:
            params=get_widget_values(parameters_dialog)
            set_parameters(self.params.record,params)
            if self.it!=None:
                self.set_gains()
                
                
    def set_static_measurements_params(self):
        '''
        open dialog with static meas parameters
        '''
        d = get_parameters(self.params.static)
        from UIs.static_meas_params_dialogUI import Ui_Dialog
        parameters_dialog = QDialog()
        ui = Ui_Dialog()
        ui.setupUi(parameters_dialog)
        set_widget_values(parameters_dialog,d)
        if parameters_dialog.exec_() == QDialog.Accepted:
            params=get_widget_values(parameters_dialog)
            set_parameters(self.params.static,params)
            
    def set_dynamical_measurements_params(self):
        '''
        open dialog with dynamical meas parameters
        '''
        d = get_parameters(self.params.dynamical)
        from UIs.dynamic_meas_params_dialogUI import Ui_Dialog
        parameters_dialog = QDialog()
        ui = Ui_Dialog()
        ui.setupUi(parameters_dialog)
        set_widget_values(parameters_dialog,d)
        if parameters_dialog.exec_() == QDialog.Accepted:
            params=get_widget_values(parameters_dialog)
            set_parameters(self.params.dynamical,params)
            
            
            

                                
    def static_measurements(self,pressed):
        if pressed:
            msg=QMessageBox(2, 'Warning', 'Do you want to start static scanning? Please ensure there are proper scanning settings')
            msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            returnValue = msg.exec()
            if returnValue == QMessageBox.Ok:  
                from measurements.static_measurements import Static_measurement as Static_measurement
                try:
                    
                    self.static_measurement=Static_measurement(self.it,self.printer,self.params.static,
                                                               self.saving_dir_path+str(self.params.static.file_name_to_save_static_meas))
                    self.add_thread([self.static_measurement])
                    
                    self.static_measurement.S_print[str].connect(self.logText)
                    self.static_measurement.S_print_error[str].connect(self.logWarningText)
                    
                    self.static_measurement.S_finished.connect(lambda: self.ui.pushButton_static_measurements.setChecked(False))
                    self.static_measurement.S_finished.connect(self.kill_static_measurement)
                    
                    self.static_measurement.is_running=True
                    
                    self.force_static_process.connect(self.static_measurement.run)
                    self.logText('Start static measurement')
                    self.force_static_process.emit()

                    
                except Exception as e :
                    self.logWarningText(str(e))
            else:
                self.ui.pushButton_static_measurements.setChecked(False)
        else:
            try:
                self.static_measurement.is_running=False
            except:
                pass
            
            
    def kill_static_measurement(self):
        del self.static_measurement
          
    def dynamical_measurements(self,pressed):
        if pressed:
            msg=QMessageBox(2, 'Warning', 'Do you want to start dynamical scanning? Please ensure there are proper scanning settings')
            msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            returnValue = msg.exec()
            if returnValue == QMessageBox.Ok:  
                from measurements.dynamical_measurements import Dynamical_measurement as Dynamical_measurement
                try:
                    
                    self.dynamical_measurement=Dynamical_measurement(self.it,self.printer,self.params.dynamical,
                                                                  self.saving_dir_path)
                    self.add_thread([self.dynamical_measurement])
                    
                    self.dynamical_measurement.S_print[str].connect(self.logText)
                    self.dynamical_measurement.S_print_error[str].connect(self.logWarningText)
                    
                    self.dynamical_measurement.S_finished.connect(lambda: self.ui.pushButton_static_measurements.setChecked(False))
                    self.dynamical_measurement.S_finished.connect(self.kill_dynamical_measurement)
                    
                    self.dynamical_measurement.is_running=True
                    
                    self.force_static_process.connect(self.dynamical_measurement.run)
                    self.logText('Start dynamical measurement')
                    self.force_dynamical_process.emit()
    
                    
                except Exception as e :
                    self.logWarningText(str(e))
            else:
                self.ui.pushButton_dynamical_measurements.setChecked(False)
        else:
            try:
                self.static_measurement.is_running=False
            except:
                pass     
 
    def kill_dynamical_measurement(self):
        del self.dynamical_measurement
          
    def choose_folder_to_save(self):
        self.saving_dir_path = str(
            QFileDialog.getExistingDirectory(self, "Select Directory"))+'\\'
        self.ui.label_folder_to_save.setText(self.saving_dir_path+'\\')
       
    def choose_file_to_load(self):
        DataFilePath= str(QFileDialog.getOpenFileName(self, "Select Data File",'','*.fbgs *.spectrum *.static' )).split("\',")[0].split("('")[1]
        if DataFilePath=='':
            self.logWarningText('file is not chosen or previous choice is preserved')
        self.file_to_load_path=DataFilePath
        self.ui.label_file_to_load.setText(DataFilePath)
 
        
    def plot_from_file(self):
        file_name=os.path.basename(self.file_to_load_path)
        if file_name.split('.')[1]=='fbgs':
            colors = plt.cm.tab10.colors
            times, channels, channel_list, FBGs_list,other_params = read_fbg_stream_raw_lp(self.file_to_load_path)
            self.logText('In this file there are channels {} and FBGs {} in these channels'.format(channel_list,FBGs_list))
            for ch in self.params.it.channels:
                N_FBG=len(self.params.it.FBGs[ch-1])
                fig,axes=plt.subplots(nrows=N_FBG,sharex=True)
                fig.supxlabel("Time, s")
                fig.supylabel("FBG wavelength, nm")
                for ii,FBG in enumerate(self.params.it.FBGs[ch-1]):
                    axes[ii].plot(times - times[0], channels[ch][ii+1],color=colors[ii % len(colors)])
                    axes[ii].set_title(f"FBG {FBG}", loc="left", fontsize=10, pad=2)
                plt.suptitle('ch {}'.format(ch))
                plt.tight_layout()
                plt.show()
            self.type_of_plotted_data='fbgs' 
            self.logText('Other parameters of the record are {} '.format(other_params))       
            
        elif file_name.split('.')[1]=='spectrum':
            with open(self.file_to_load_path,'rb') as f:
                waves,spectrum=pickle.load(f)
            plt.figure()
            plt.plot(waves,spectrum)
            plt.xlabel('Wavelength, nm')
            plt.ylabel('Spectral power, dBm')
            plt.tight_layout()
            self.type_of_plotted_data='spectrum'
            
        elif file_name.split('.')[1]=='static':
            
            self.static_processor=Static_processor(self.file_to_load_path,self.params.it.channels,self.params.it.FBGs)
            # self.add_thread(self.static_processor)
            self.static_processor.S_print_error[str].connect(self.logWarningText)
            self.static_processor.plot_all_3d_plots()
            self.type_of_plotted_data='static3d'
            

      
    def plot_single_slice_of_static(self):
        try:
            if not hasattr(self, "static_processor"):
                self.static_processor=Static_processor(self.file_to_load_path,self.params.it.channels,self.params.it.FBGs)
                self.static_processor.S_print_error[str].connect(self.logWarningText)
            self.static_processor.plot_along_coord(float(self.ui.lineEdit_coordinate_to_plot_static_slice.text()),
                                                   self.ui.comboBox_axis_to_plot_static_slice.currentText(), 
                                                   int(self.ui.comboBox_channel_to_plot_static_slice.currentText()),
                                                   int(self.ui.comboBox_FBG_to_plot_static_slice.currentText()))
            self.type_of_plotted_data='static slice'
        except Exception as e:
            self.logWarningText('Error while plotting along coordinate:'+str(e))
            
            
    def save_single_line_to_csv(self):
        try:
            if self.type_of_plotted_data=='static slice':
                D=self.static_processor.single_slice_params
                line = D['fig'].gca().get_lines()[0]
                coords = line.get_xdata()
                signal = line.get_ydata()
                path=os.path.dirname(self.file_to_load_path)
                source_file_name=os.path.basename(self.file_to_load_path).split('.')[0]         
                file_name=source_file_name+' {}={} mm,ch={} FBG={}.csv'.format(D['axis'],D['x0'],D['ch'],D['FBG'])
                csv_line_saver(path+'//'+file_name, coords, signal, 'Coordinate, mm', 'Shift, nm')
                
            elif self.type_of_plotted_data=='fbgs':
                line = plt.gca().get_lines()[0]
                time = line.get_xdata()
                shifts = line.get_ydata()
                path=os.path.dirname(self.file_to_load_path)
                source_file_name=os.path.basename(self.file_to_load_path).split('.')[0]         
                file_name=source_file_name+'.csv'
                csv_line_saver(path+'//'+file_name, time, shifts, 'Time, s', 'Shift, nm')
                
       # строки
                

            self.logText('Line saved')  
        except Exception as e:
            self.logWarningText(str(e))
                
    def save_parameters_to_file(self):
        '''
        save all parameters and values except paths to file

        Returns
        -------
        None.

        '''
        D={}
        D['it']=get_parameters(self.params.it)
        D['recording']=get_parameters(self.params.record)
        D['static']=get_parameters(self.params.static)
        D['main_window']=get_widget_values(self)
        
        

        #remove all parameters that are absolute paths 
        for k in D:
            l=[key for key in list(D[k].keys()) if ('path' in key)]
            for key in l:
                del D[k][key]
    
        f=open(self.ParametersFileName,'w')
        json.encoder.FLOAT_REPR = lambda x: format(x, '.5f') if (x<0.01) else x
        json.dump(D,f)
        f.close()
        self.logText('\nParameters saved\n')
        
        
    def load_parameters_from_file(self):
        try:
            f=open(self.ParametersFileName)
            Dicts=json.load(f)
            f.close()
            
               
            if Dicts is not None:
                try:
                    set_parameters(self.params.it,Dicts['it'])
                    set_parameters(self.params.record,Dicts['recording'])
                    set_parameters(self.params.static,Dicts['static'])
                    set_widget_values(self, Dicts['main_window'])
                    
                except KeyError as e:
                    self.logWarningText(str(e))
                    pass
                self.logText('\nParameters loaded\n')
    
        except FileNotFoundError:
            self.logWarningText('Error while load parameters: Parameters file not found')
    
        except json.JSONDecodeError:
            self.logWarningText('Errpr while load parameters: file has wrong format')
    
    def delete_all_figures(self):
        if plt.get_backend()!='TkAgg':  
            for i in plt.get_fignums():
                plt.close(i)
        else:
            self.logWarningText('Deleting figures does not work with TKinter backend')
        # if plt.get_backend()!='TkAgg':
        #     plt.close(plt.close('all'))
        # else:
        #     matplotlib.use("Agg")
        #     plt.close(plt.close('all'))
        #     time.sleep(0.5)
         #     matplotlib.use("TkAgg")
         
        
    def __del__(self):
        if self.it!=None:
            self.it._sock.shutdown(2)
            self.it._sock.close()
            del self.it
           
       
    
def get_widget_values(window)->dict:
    '''
    collect all data from all widgets in a window
    '''
    D={}
    for w in window.findChildren(QLineEdit):
        s=w.text()
        key=w.objectName().split('lineEdit_')[1]
        try:
            f=int(s)
            
        except ValueError:
            
            try:
                f=float(s)
                
            except ValueError:
                f=s
        D[key]=f
    for w in window.findChildren(QCheckBox):
        f=w.isChecked()
        key=w.objectName().split('checkBox_')[1]
        D[key]=f
        
    for w in window.findChildren(QComboBox):
        s=w.currentText()
        key=w.objectName().split('comboBox_')[1]
        D[key]=s
    return D

def set_widget_values(window,d:dict)->None:
     for w in window.findChildren(QLineEdit):
         key=w.objectName().split('lineEdit_')[1]
         try:
             s=d[key]
             w.setText(str(s))
         except KeyError as e:
             print('Set widget values error: '+ str(e))
             pass
     for w in window.findChildren(QCheckBox):
         key=w.objectName().split('checkBox_')[1]
         try:
             s=d[key]
             w.setChecked(s)
             w.clicked.emit(s)
         except KeyError as e:
             print('Set widget values error: '+ str(e))
     for w in window.findChildren(QComboBox):
         key=w.objectName().split('comboBox_')[1]
         try:
             s=d[key]
             w.setCurrentText(s)
         except KeyError:
             pass
    
def set_parameters(obj, d:dict):
    for key in d:
        try:
            
            if '[' in d[key]:
                d[key]=json.loads(d[key])
            obj.__setattr__(key, d[key])
        except TypeError:
            obj.__setattr__(key, d[key])
            pass
   
def get_parameters(obj) -> dict:
    '''
    Returns
    -------
    Seriazible attributes of the  object
    '''
    d = dict(vars(obj)).copy()  # make a copy of the vars dictionary
    return d


def ask_homing_confirm(parent=None) -> bool:
    text, ok = QInputDialog.getText(
        parent,
        "Warning!",
        "Вы собираетесь откалибровать положение головки принтера. \n \n Убедитесь, что \n -с головки сняты все неоригинальные навесные элементы \n -со столика убраны неоригинальные площадки\n -на столик установлена оригинальная подставка \n\n Чтобы продолжить, введите фразу: CONFIRM",
        QLineEdit.Normal,
        ""
    )
    if not ok:
        return False

    if text.strip() == "CONFIRM":
        return True

    QMessageBox.warning(parent, "Ошибка", "Неверная фраза подтверждения.")
    return False

def csv_line_saver(file_path,x,y,x_label,y_label):
    with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow([x_label, y_label])          # заголовки
        writer.writerows(zip(x, y))   