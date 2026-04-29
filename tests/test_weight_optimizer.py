import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize
from mpl_toolkits.mplot3d import Axes3D  # для 3D-графика
import pickle


# ----------------------------------------------------------------------
# 1. Модель отклика датчика (гауссиан)
       
def FBG_response(x, A, mu, sigma):
    """Гауссов отклик: A * exp(-(x - mu)^2 / sigma^2)"""
    return A * np.exp(-(x - mu)**2 / sigma**2)

def test_optimizer(W_true,xl_true,xr_true,calibration,
                   noise_level):
    

    # ----------------------------------------------------------------------
    # 2. Целевая функция (сумма квадратов невязок)
    def cost_function(x, calibration, measured_shifts, channels, fbgs_per_channel):
        """x = [W, xl, xr]"""
        W, xl, wheelset_width = x
        cost = 0.0
        for ch in channels:
            for fbg in fbgs_per_channel[ch]:
                # Получаем параметры модели для этого датчика: (A, mu, sigma)
                params = calibration[ch][fbg]['params']
                A, mu, sigma = params
                # Предсказанный сдвиг от колёсной пары
                predicted = (W / 2.0) * (FBG_response(xl, A, mu, sigma) +
                                         FBG_response(xl+wheelset_width, A, mu, sigma))
                # Измеренный сдвиг
                measured = measured_shifts[ch][fbg]
                cost += (measured - predicted) ** 2
        return cost

    def get_meas_shifts(W_true,xl_true,xr_true):
          max_response=[0,0,0]
          measured_shifts = {}
          for ch in channels:
              measured_shifts[ch] = {}
              for fbg in fbgs_per_channel[ch]:
                  A, mu, sigma = calibration[ch][fbg]['params']
                  exact = (W_true / 2.0) * (FBG_response(xl_true, A, mu, sigma) +
                                            FBG_response(xr_true, A, mu, sigma))
                  # Добавляем шум со стандартным отклонением 0.05
                  noise = np.random.normal(0, noise_level)
                  measured_shifts[ch][fbg] = exact + noise
                  if abs(max_response[0])<abs(measured_shifts[ch][fbg]):
                      max_response=[measured_shifts[ch][fbg],ch,fbg]
                      
                      
          
          # Выведем для проверки
          print("Сгенерированные измеренные сдвиги (с шумом):")
          for ch in channels:
              for fbg in fbgs_per_channel[ch]:
                  print(f"ch{ch}, fbg{fbg}: {measured_shifts[ch][fbg]:.3f}")
          return measured_shifts,max_response
      
    def callback(xk):
           """Функция, вызываемая на каждой итерации оптимизатора.
              xk — текущие значения переменных (массив)"""
           cost_val = cost_function(xk, calibration, measured_shifts, channels, fbgs_per_channel)
           history.append([xk[0], xk[1], xk[2], cost_val])
           

    np.random.seed(42)  # для воспроизводимости
    channels = [int(a) for a in  calibration.keys()]                     # два канала
    fbgs_per_channel={}
    for ch in channels:
        fbgs_per_channel[ch] =[int(a) for a in calibration[ch].keys()]
        
    measured_shifts,max_response=get_meas_shifts(W_true, xl_true, xr_true)
    
    history = []
    # Начальное приближение
    
    x_l_guess=calibration[max_response[1]][max_response[2]]['params'][1]
    weight_guess=max_response[0]/calibration[max_response[1]][max_response[2]]['params'][0]
    wheelset_width_guess=10
    
    guess=[weight_guess,x_l_guess,wheelset_width_guess]
    bounds=[(0,1000),(-110,110),(0,200)]
    # Запуск минимизации (метод Nelder-Mead)
    result = minimize(
        cost_function,
        guess,
        bounds=bounds,
        args=(calibration, measured_shifts, channels, fbgs_per_channel),
        method='Nelder-Mead',
        # method='BFGS',
        # method='Newton-CG',
        callback=callback,
        options={'maxiter': 1000, 'disp': True}
    )
    
    # Результаты
    W_opt, xl_opt, wheelset_width_opt = result.x
    xr_opt=xl_opt+wheelset_width_opt
    print("\n=== Результат оптимизации ===")
    print(f"Истинные значения: W = {W_true}, xl = {xl_true}, xr = {xr_true}")
    print(f"Найденные значения: W = {W_opt:.3f}, xl = {xl_opt:.3f}, xr = {xr_opt:.3f}")
    print(f"Значение функции стоимости: {result.fun:.6f}")
    print(f"Сообщение: {result.message}")
    
    # ----------------------------------------------------------------------
    # 5. Визуализация процесса оптимизации
    history = np.array(history)
    iterations = np.arange(len(history))
    return   W_opt, xl_opt, wheelset_width_opt, xr_opt,iterations,history
    
def plot_history(W_opt, xl_opt, wheelset_width_opt, xr_opt,iterations,history):
    
   
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle("Процесс оптимизации (Nelder-Mead)")
    
    # График значения функции стоимости
    axes[0,0].plot(iterations, history[:,3], 'b-', linewidth=1)
    axes[0,0].set_xlabel("Номер итерации")
    axes[0,0].set_ylabel("Cost (сумма квадратов)")
    axes[0,0].set_title("Сходимость целевой функции")
    axes[0,0].grid(True)
    
    # График изменения параметров
    axes[0,1].plot(iterations, history[:,0], 'r-', label='W (вес)')
    axes[0,1].plot(iterations, history[:,1], 'g-', label='xl (левое колесо)')
    axes[0,1].plot(iterations, history[:,1]+ history[:,2], 'b-', label='xr (правое колесо)')
    axes[0,1].axhline(y=W_true, color='r', linestyle='--', alpha=0.5, label='Истинный W')
    axes[0,1].axhline(y=xl_true, color='g', linestyle='--', alpha=0.5, label='Истинный xl')
    axes[0,1].axhline(y=xr_true, color='b', linestyle='--', alpha=0.5, label='Истинный xr')
    axes[0,1].set_xlabel("Номер итерации")
    axes[0,1].set_ylabel("Значение параметра")
    axes[0,1].set_title("Изменение параметров")
    axes[0,1].legend(loc='best')
    axes[0,1].grid(True)
    
    # Траектория в проекции (xl, xr)
    axes[1,0].plot(history[:,1], history[:,1]+history[:,2], 'k.-', alpha=0.7)
    axes[1,0].scatter(history[0,1],history[0,1]+history[0,2], color='green', s=80, label='Старт')
    axes[1,0].scatter(history[-1,1], history[-1,1]+history[-1,2], color='red', s=80, label='Финиш')
    axes[1,0].scatter(xl_true, xr_true, color='blue', marker='*', s=150, label='Истина')
    axes[1,0].set_xlabel("xl (мм)")
    axes[1,0].set_ylabel("xr (мм)")
    axes[1,0].set_title("Траектория в плоскости (xl, xr)")
    axes[1,0].legend()
    axes[1,0].grid(True)
    
    # Зависимость стоимости от веса W (на последних итерациях полезно, но нарисуем по всей истории)
    axes[1,1].scatter(history[:,0], history[:,3], c=iterations, cmap='viridis', s=10)
    axes[1,1].set_xlabel("W (вес)")
    axes[1,1].set_ylabel("Cost")
    axes[1,1].set_title("Целевая функция vs вес (цвет — итерация)")
    axes[1,1].grid(True)
    cbar = plt.colorbar(axes[1,1].collections[0], ax=axes[1,1])
    cbar.set_label("Номер итерации")
    
    plt.tight_layout()
    plt.show()
    


def plot_calibration(calibration):
    channels = [int(a) for a in  calibration.keys()]                     # два канала
    fbgs_per_channel={}
    for ch in channels:
        fbgs_per_channel[ch] =[int(a) for a in calibration[ch].keys()]
    
    x=np.arange(-100,100)
    total_response=np.zeros(len(x))
    colors = plt.cm.tab10.colors
    plt.figure()
    for ch in channels:
        for FBG in fbgs_per_channel[ch]:
            plt.plot(x,FBG_response(x,*calibration[ch][FBG]['params']),color=colors[ch])
            total_response+=FBG_response(x,*calibration[ch][FBG]['params'])
    plt.xlabel('position,mm')
    plt.ylabel('response, nm/g')
    
    
    plt.tight_layout()
    
    plt.figure()
    plt.plot(x,total_response)
    plt.xlabel('position,mm')
    plt.ylabel('Total response, nm/g')
    plt.tight_layout()
    

    
if __name__=='__main__':
    # ----------------------------------------------------------------------
    # 3. Генерация синтетических данных
    
    calibration_file_path=r"F:\!Projects\!WIM\2026.04.26 data\static\weight=160 g try 4.setup_calib"
    # Конфигурация датчиков: каналы и FBG
    with open(calibration_file_path,'rb') as f:
        calibration=pickle.load(f)
    
    # Истинные значения искомых параметров (на основе которых сгенерируем "измерения")
    W_true = 160          # г
    xl_true = 30        # мм
    xr_true = xl_true+50        # мм (расстояние между колёсами 90 мм)
    
    noise_level=0.00 # nm
    # Калибровочные параметры для каждого датчика (гауссиан)
    # Для упрощения зададим вручную, но можно было бы сгенерировать случайно.

    
    W_opt, xl_opt, wheelset_width_opt, xr_opt,iterations,history=test_optimizer(W_true,xl_true,xr_true,calibration,noise_level)
    plot_history(W_opt, xl_opt, wheelset_width_opt, xr_opt,iterations,history)
  
    # ----------------------------------------------------------------------
    # 4. Оптимизация с записью истории
    # Список для хранения истории (каждый элемент: [W, xl, xr, cost])

    
   
    
