# -*- coding: utf-8 -*-
"""
Created on Wed Jan 21 11:32:18 2026

@author: Илья
"""

__version__='1.6'
__date__ = '2026.03.30'

import os
    
import numpy as np
import time
import matplotlib
matplotlib.use("Qt5Agg")
import matplotlib.pyplot as plt
import json
import csv

import pickle

from PyQt5.QtCore import  QThread,QTimer,pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QFileDialog, QDialog,QLineEdit,QComboBox,QCheckBox,QMessageBox,QInputDialog
import traceback

from Printer_control.Printer import Printer, PrinterConfig
from AFR_interrogator.interrogator import Interrogator,Params_interrogator
from AFR_interrogator.FBGRecorder import (read_fbg_stream_raw_lp,
                                          start_live_plot_session,record_to_file,record_and_plot,
                                          record_spectra_to_file,
                                          live_plot_wavelengths)


from processing.process_spectra import Spectra_meas_processor as Spectra_meas_processor

from measurements.static_measurements import Static_measurement as Static_measurement
from measurements.static_measurements import Static_measurement_params as Static_measurement_params
from processing.process_static_data import Static_meas_processor as Static_processor

from measurements.dynamical_measurements import Dynamical_measurement as Dynamical_measurement
from measurements.dynamical_measurements import Dynamical_measurement_params as Dynamical_measurement_params

from measurements.long_term_measurements import Long_term_measurement as Long_term_measurement
from measurements.long_term_measurements import Long_term_measurement_params as Long_term_measurement_params
from processing.process_long_term_measurements import Long_term_meas_processor as Long_term_meas_processor


from UIs.MainWindowUI import Ui_MainWindow


        
class Params_recording():
    def __init__(self):      
        self.rep_rate=2000
        self.recording_duration=10
        self.write_every_nth=10
        self.plot_live_while_recording=False
        self.type_of_recording='FBG peaks'
        self.file_name='1.fbgs'


     

        
        


class Params():
    def __init__(self):
        self.it=Params_interrogator()
        self.record=Params_recording()
        self.static=Static_measurement_params()
        self.dynamical=Dynamical_measurement_params()
        self.long_term=Long_term_measurement_params()


class ThreadedMainWindow(QMainWindow):
    
    force_static_process=pyqtSignal()
    force_dynamical_process=pyqtSignal()
    force_long_term_process=pyqtSignal()
    

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

        
        self.it=None
        self.printer=None
        
        self.type_of_plotted_data=None
        self.load_parameters_from_file()

        
  
        
    def logText(self, text):
        self.ui.LogField.append(">" + text)
        
    def logWarningText(self, text):
        self.ui.LogField.append("<span style=\" font-size:8pt; font-weight:600; color:#ff0000;\" >"
                             + ">" + text + "</span>")
        
    def clear_log(self):
        """Функция, которая вызывается по нажатию кнопки и очищает LogField."""
        self.ui.LogField.clear()
        
    def init_interface(self):
        
        
        
        
        self.ui.pushButton_choose_folder_to_save.clicked.connect(self.choose_folder_to_save)
        

        self.ui.pushButton_connect_it.toggled[bool].connect(self.connect_interrogator)
        self.ui.pushButton_set_it_parameters.pressed.connect(self.set_it_parameters)
        
        self.ui.pushButton_connect_printer.pressed.connect(self.connect_printer) 
        
        self.ui.pushButton_printer_homing.pressed.connect(self.printer_homing)
        self.ui.pushButton_printer_move_bed_down.pressed.connect(self.printer_move_bed_down)
        
        
        self.ui.pushButton_single_measurement.clicked.connect(self.single_measurement)
        self.ui.pushButton_save_single_spectrum.clicked.connect(self.save_single_spectrum)
        
        self.ui.pushButton_start_recording.pressed.connect(self.recording)
        self.ui.pushButton_plot_live_dynamics.toggled[bool].connect(self.plot_live_dynamics)
        self.ui.pushButton_set_recording_parameters.pressed.connect(self.set_recording_parameters)
        
        self.ui.pushButton_long_term_measurements.toggled[bool].connect(self.long_term_measurements)
        self.ui.pushButton_set_long_term_measurements_params.pressed.connect(self.set_long_term_measurements_params)
        
        self.ui.pushButton_static_measurements.toggled[bool].connect(self.static_measurements)
        self.ui.pushButton_set_static_measurements_params.pressed.connect(self.set_static_measurements_params)
        
        self.ui.pushButton_dynamical_measurements.toggled[bool].connect(self.dynamical_measurements)
        self.ui.pushButton_set_dynamical_measurements_params.pressed.connect(self.set_dynamical_measurements_params)
        
        
        
        
        

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
                set_parameters(self.it.params, get_parameters(self.params.it))
                time.sleep(0.1)
                # self.it.set_gains()
                # self.add_thread(self.it)
                self.logText('Connected to interrogator')
            except Exception as e:
                self.logWarningText(str(e))
        else:
            del self.it
            self.logText('disconnected from interrogator')

            
    def connect_printer(self):
        try:
            self.printer = Printer(PrinterConfig())
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
            self.printer.move_z(z=300,speed_mm_s=50)
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
                set_parameters(self.it.params,params)
                self.it.set_gains()
                

            
    def set_recording_parameters(self):
        '''
        open dialog with recorder parameters
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
                self.it.set_gains()
                
    def set_long_term_measurements_params(self):
        '''
        open dialog with static meas parameters
        '''
        d = get_parameters(self.params.long_term)
        from UIs.long_term_recording_parameters_dialogUI import Ui_Dialog
        parameters_dialog = QDialog()
        ui = Ui_Dialog()
        ui.setupUi(parameters_dialog)
        set_widget_values(parameters_dialog,d)
        if parameters_dialog.exec_() == QDialog.Accepted:
            params=get_widget_values(parameters_dialog)
            set_parameters(self.params.long_term,params)
                
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
            
            
    def single_measurement(self):
        try:
            FBGs=self.it.get_averaged_single_FBG_measurement()
            if FBGs==None:
                self.logWarningText('error. no data returned from Interrogator')
                return 
            string=''
            for ch in self.params.it.channels:
    
                    if FBGs[ch-1] is not None:
                        string+=f'channel{ch}:  '+(", ".join(f"{x:.3f}" for x in FBGs[ch-1]))+ ' nm'
    
            self.logText(string)
            if self.ui.checkBox_plot_single_spectrum.isChecked():
                waves=self.it.get_waves()
                for ch in self.params.it.channels:
                    spectrum=self.it.get_single_spectrum(ch)
                    plt.figure()
                    plt.plot(waves,spectrum)
                    plt.xlabel('Wavelength, nm')
                    plt.ylabel('Spectral power, dBm')
                    ymin, ymax = plt.ylim()
                    if FBGs[ch-1] is not None:
                        for FBG_wave in FBGs[ch-1]:
                            if FBG_wave is not np.nan:
                                plt.axvline(FBG_wave,  color='red')
                    plt.axhline(self.it.get_log_threshold(ch),ls='--',color='gray',alpha=0.3)
                    plt.title('Channel {}'.format(ch))
            plt.show(block=False)
        except Exception as e:
            self.logWarningText(str(e))            

    def save_single_spectrum(self):
        try:
            line = plt.gca().get_lines()[0]
            waves = line.get_xdata()
            signal = line.get_ydata()
            with open(self.saving_dir_path+'\\'+ self.ui.lineEdit_file_name_to_save_spectrum.text()+'.spectrum', "wb") as f:
                pickle.dump([waves,signal], f)
            self.logText('\nSpectrum saved\n')     
        except Exception as e:
            self.logWarningText(str(e))

    def plot_live_dynamics(self, pressed: bool):
        if pressed:
            try:
                # старт потока данных
                self.it.start_freq_stream(self.params.record.rep_rate)
    
                # старт live session (fanout + plots)
                self._stop_live, self._live_info = start_live_plot_session(
                    it=self.it,
                    plot_channels=list(self.params.it.channels),      # 1-based
                    plot_FBGs=list(self.params.it.FBGs),              # 1-based
                    rep_rate_hz=float(self.params.record.rep_rate),
                    window_sec=20.0,
                    max_fps=30,
                    ylim=None,
                    title_prefix="Live dynamics",
                    use_subplots=True,
                    queue_maxsize=1000,
                    max_frames_per_update=1200
                )
    
                self.logText("Live dynamics started")
    
            except Exception as e:
                self.logWarningText(str(e))
                try:
                    self.ui.pushButton_plot_live_dynamics.setChecked(False)
                except Exception:
                    pass
    
        else:
            try:
                # остановить live session
                if hasattr(self, "_stop_live") and self._stop_live is not None:
                    try:
                        self._stop_live()
                    except Exception:
                        pass
                    self._stop_live = None
                    self._live_info = None
    
                # остановить приборный стрим
                try:
                    self.it.stop_freq_stream()
                except Exception:
                    pass
    
                self.logText("Live dynamics stopped")
    
            except Exception as e:
                self.logWarningText(str(e))        

           
    def recording(self):
        FilePrefix=self.ui.lineEdit_file_name_for_recording.text()
        self.logText('start recording')
        
        if self.params.record.type_of_recording=='FBG peaks':
            if not self.params.record.plot_live_while_recording:
                
                try:
                    self.it.start_freq_stream(self.params.record.rep_rate)
                    stats = record_to_file(self.it, self.saving_dir_path+self.params.record.file_name+".fbgs", duration_sec=self.params.record.recording_duration,
                                           channels=self.params.it.channels,FBGs=self.params.it.FBGs,write_every_n=self.params.record.write_every_nth)
                    self.logText("Recording finished: {}".format(stats))
                    self.it.stop_freq_stream()
                except Exception as e:
                    self.logWarningText(str(e))
                    
                self.it.stop_freq_stream()
                
            else:
                try:
                    self.it.start_freq_stream()
        
                    self._stop_all, stats = record_and_plot(
                        self.it,
                        channels=self.params.it.channels,
                        FBGs=self.params.it.FBGs,
                        write_every_n=self.params.record.write_every_nth,
                        filepath=self.saving_dir_path+self.params.record.file_name+".fbgs",
                        duration_sec=self.params.record.recording_duration,
                        plot_channels=self.params.it.channels,
                        plot_FBGs=np.array(self.params.it.FBGs)-1,
                        window_sec=10.0,
                        max_fps=30    
                    )
                    QTimer.singleShot(int(self.params.record.recording_duration * 1000), self._stop_all)
                    self.logText("Recording finished: {}".format(stats))
                except Exception as e:
                    self.logWarningText(str(e))
                # ... окно живёт; когда захотите — останавливайте
            # stop_all()
            # self.it.stop_freq_stream()
        elif self.params.record.type_of_recording=='Spectra':

            record_spectra_to_file(self.it,
                                   write_every_n=self.params.record.write_every_nth,
                                   filepath=self.saving_dir_path+self.params.record.file_name+".spectra",
                                   duration_sec=self.params.record.recording_duration,
                                   channels=self.params.it.channels
                                   )
            self.logText("Recording of spectra finished:")
            
            
    def long_term_measurements(self,pressed):
        if pressed:
            self.long_term_measurement=Long_term_measurement(self.it, self.params.long_term,
                                                             self.saving_dir_path+str(self.params.long_term.file_name)+".long_dynamics")
            self.add_thread([self.long_term_measurement])
            self.force_long_term_process.connect(self.long_term_measurement.run)
            self.logText('Start long-term measurement')
            self.long_term_measurement.is_running=True
            self.long_term_measurement.S_print[str].connect(self.logText)
            self.long_term_measurement.S_print_error[str].connect(self.logWarningText)
            
            
            
            self.long_term_measurement.S_finished.connect(lambda: self.ui.pushButton_long_term_measurements.setChecked(False))
            self.long_term_measurement.S_finished.connect(self.kill_long_term_measurement)
            self.force_long_term_process.emit()
        else:
            self.long_term_measurement.is_running=False
            
    def kill_long_term_measurement(self):
        del self.long_term_measurement
                                
    def static_measurements(self,pressed):
        if pressed:
            msg=QMessageBox(2, 'Warning', 'Do you want to start static scanning? \n Please ensure there are proper scanning settings \n Ensure that the bed thickness is properly set!')
            msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            returnValue = msg.exec()
            if returnValue == QMessageBox.Ok:  
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
          


    def _start_live_plot_from_queue(self, q_plot):
        """
        Запускается в GUI потоке. Создаёт matplotlib окна и подключает их к очереди q_plot,
        которую наполняет FrameFanout из рабочего потока.
        """
        try:
            # Закроем предыдущие плоты (если были)
            if hasattr(self, "live_plot_stops"):
                for s in self.live_plot_stops:
                    try:
                        s()
                    except Exception:
                        pass
    
            self.live_plot_stops = []
            self.live_plot_figs = []
    
            # ВНИМАНИЕ: live_plot_wavelengths ожидает fbg_indices 0-based!
            for ch in self.params.it.channels:
                fbg_indices_0 = [int(i) - 1 for i in self.params.it.FBGs[ch-1]]  # 1-based -> 0-based
                stop, fig = live_plot_wavelengths(
                    it=self.it,
                    channel=ch,
                    fbg_indices=fbg_indices_0,
                    window_sec=10.0,
                    max_fps=30,
                    blocking=False,
                    source_queue=q_plot,   # ключевой момент: НЕ читаем it.pop_freq_frame в GUI
                    use_subplots=True
                )
                self.live_plot_stops.append(stop)
                self.live_plot_figs.append(fig)
    
        except Exception as e:
            self.logWarningText("Live plot start error: " + str(e))
            
            
    def dynamical_measurements(self,pressed):
        if pressed:
            msg=QMessageBox(2, 'Warning', 'Do you want to start dynamical scanning? \n  \n Ensure that the bed thickness is properly set!')
            msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            returnValue = msg.exec()
            if returnValue == QMessageBox.Ok:  
                try:
                    
                    self.dynamical_measurement=Dynamical_measurement(self.it,self.printer,self.params.dynamical,
                                                                     self.saving_dir_path,
                                                                     self.params.it.channels,
                                                                     self.params.it.FBGs)
                    self.add_thread([self.dynamical_measurement])
                    
                    self.dynamical_measurement.S_print[str].connect(self.logText)
                    self.dynamical_measurement.S_print_error[str].connect(self.logWarningText)
                    self.dynamical_measurement.S_plot_queue_ready.connect(self._start_live_plot_from_queue)
                    
                    self.dynamical_measurement.S_finished.connect(lambda: self.ui.pushButton_dynamical_measurements.setChecked(False))
                    self.dynamical_measurement.S_finished.connect(self.kill_dynamical_measurement)
                    
                    self.dynamical_measurement.is_running=True
                    
                    self.force_dynamical_process.connect(self.dynamical_measurement.run)
                    self.logText('Start dynamical measurement')
                    self.force_dynamical_process.emit()
    
                    
                except Exception as e :
                    self.logWarningText(str(e))
            else:
                self.ui.pushButton_dynamical_measurements.setChecked(False)
        else:
            try:
                self.dynamical_measurement.is_running=False
                if hasattr(self, "live_plot_stops"):
                    for s in self.live_plot_stops:
                        try: s()
                        except Exception: pass
                    self.live_plot_stops = []
            except:
                pass     
 
    def kill_dynamical_measurement(self):
        del self.dynamical_measurement
          
    def choose_folder_to_save(self):
        self.saving_dir_path = str(
            QFileDialog.getExistingDirectory(self, "Select Directory"))+'\\'
        self.ui.label_folder_to_save.setText(self.saving_dir_path+'\\')
       
    def choose_file_to_load(self):
        DataFilePath= str(QFileDialog.getOpenFileName(self, "Select Data File",'','*.fbgs *.spectrum *.static *.spectra *.long_dynamics' )).split("\',")[0].split("('")[1]
        if DataFilePath=='':
            self.logWarningText('file is not chosen or previous choice is preserved')
        self.file_to_load_path=DataFilePath
        self.ui.label_file_to_load.setText(DataFilePath)
 
        
    def plot_from_file(self):
        try:
            file_name=os.path.basename(self.file_to_load_path)
            if file_name.split('.')[1]=='fbgs':
                colors = plt.cm.tab10.colors
                times, channels, channel_list, FBGs_list,other_params = read_fbg_stream_raw_lp(self.file_to_load_path)
                self.logText('In this file there are channels {} and FBGs {} in these channels'.format(channel_list,FBGs_list))
                self.figs_fbgs=[]
                for ch in self.params.it.channels:
                    N_FBG=len(self.params.it.FBGs[ch-1])
                    if N_FBG>1:
                        
                        fig,axes=plt.subplots(nrows=N_FBG,sharex=True)
                        self.figs_fbgs.append(fig)
                        fig.supxlabel("Time, s")
                        fig.supylabel("FBG wavelength, nm")
                        for ii,FBG in enumerate(self.params.it.FBGs[ch-1]):
                            axes[ii].plot(times - times[0], channels[ch][ii+1],color=colors[ii % len(colors)])
                            axes[ii].set_title(f"FBG {FBG}", loc="left", fontsize=10, pad=2)
                        plt.suptitle('ch {} of {}, v_y={} mm/s'.format(ch, file_name.split('.')[0], other_params['y_velocity']))
                                            
    
                    else: 
                        fig=plt.figure()
                        self.figs_fbgs.append(fig)
                        plt.xlabel("Time, s")
                        plt.ylabel("FBG wavelength, nm")
                        plt.plot(times - times[0], channels[ch][self.params.it.FBGs[ch-1][0]])
                        plt.title('FBG {}, ch {} of "{}"'.format(self.params.it.FBGs[ch-1][0],ch, file_name.split('.')[0]))
                        
                   
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
                plt.show()
                
            elif file_name.split('.')[1]=='static':
                
                self.static_processor=Static_processor(self.file_to_load_path,self.params.it.channels,self.params.it.FBGs)
                self.static_processor.S_print_error[str].connect(self.logWarningText)
                self.static_processor.S_print[str].connect(self.logText)
                self.static_processor.indicate_maxima_of_maps()
                self.static_processor.plot_all_3d_plots()
                self.type_of_plotted_data='static3d'
                
            elif file_name.split('.')[1]=='spectra':
                self.spectra_processor=Spectra_meas_processor(self.file_to_load_path,self.params.it.channels)
                self.spectra_processor.S_print_error[str].connect(self.logWarningText)
                self.spectra_processor.S_print[str].connect(self.logText)
                self.spectra_processor.plot_3d()
                self.type_of_plotted_data='spectra'
                
                  
            elif file_name.split('.')[1]=='long_dynamics':
                self.long_term_processor=Long_term_meas_processor(self.file_to_load_path,self.params.it.channels,self.params.it.FBGs)
                self.long_term_processor.S_print_error[str].connect(self.logWarningText)
                self.long_term_processor.S_print[str].connect(self.logText)
                self.long_term_processor.plot()
                self.type_of_plotted_data='long_dynamics'
        except Exception:
            self.logWarningText(traceback.format_exc()) 
            
                
            

      
    def plot_single_slice_of_static(self):
        try:
            if not hasattr(self, "static_processor"):
                self.static_processor=Static_processor(self.file_to_load_path,self.params.it.channels,self.params.it.FBGs)
                self.static_processor.S_print_error[str].connect(self.logWarningText)
                self.static_processor.S_print[str].connect(self.logText)
                self.static_processor.indicate_maxima_of_maps()
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
                ch=int(self.ui.comboBox_channel_to_plot_static_slice.currentText())
                FBG=int(self.ui.comboBox_FBG_to_plot_static_slice.currentText())
                index=self.params.it.FBGs[ch-1].index(FBG)
                axis=self.figs_fbgs[ch-1].axes[index]
                line = axis.get_lines()[0]
                time = line.get_xdata()
                shifts = line.get_ydata()
                path=os.path.dirname(self.file_to_load_path)
                source_file_name=os.path.basename(self.file_to_load_path).split('.')[0]         
                file_name=source_file_name+'.csv'
                csv_line_saver(path+'//'+file_name, time, shifts, 'Time, s', 'Wavelength, nm')
                
            elif self.type_of_plotted_data=='long_dynamics':
                ch=int(self.ui.comboBox_channel_to_plot_static_slice.currentText())
                FBG=int(self.ui.comboBox_FBG_to_plot_static_slice.currentText())
                index=self.params.it.FBGs[ch-1].index(FBG)
                axis=self.long_term_processor.figs_fbgs[ch-1].axes[index]
                line = axis.get_lines()[0]
                time = line.get_xdata()
                shifts = line.get_ydata()
                path=os.path.dirname(self.file_to_load_path)
                source_file_name=os.path.basename(self.file_to_load_path).split('.')[0]         
                file_name=source_file_name+'.csv'
                csv_line_saver(path+'//'+file_name, time, shifts, 'Time, s', 'Wavelength, nm')
                
                
                
       # строки
                

            self.logText('Line saved to '+ path+'//'+file_name) 
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
        D['dynamical']=get_parameters(self.params.dynamical)
        D['long_term']=get_parameters(self.params.long_term)
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
                    if self.it!=None:
                        set_parameters(self.it.params,Dicts['it'])
                    set_parameters(self.params.record,Dicts['recording'])
                    set_parameters(self.params.static,Dicts['static'])
                    set_parameters(self.params.dynamical,Dicts['dynamical'])
                    set_parameters(self.params.long_term,Dicts['long_term'])
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
            if hasattr(obj, key):
                if '[' in d[key]:
                    obj.__setattr__(key,json.loads(d[key]))
                else:
                    obj.__setattr__(key,d[key])
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