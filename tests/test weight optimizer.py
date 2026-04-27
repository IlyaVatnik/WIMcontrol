import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize
from mpl_toolkits.mplot3d import Axes3D  # для 3D-графика

# ----------------------------------------------------------------------
# 1. Модель отклика датчика (гауссиан)
def response_function(x, A, mu, sigma):
    """Гауссов отклик: A * exp(-(x - mu)^2 / sigma^2)"""
    return A * np.exp(-(x - mu)**2 / sigma**2)

# ----------------------------------------------------------------------
# 2. Целевая функция (сумма квадратов невязок)
def cost_function(x, calibration, measured_shifts, channels, fbgs_per_channel):
    """x = [W, xl, xr]"""
    W, xl, xr = x
    cost = 0.0
    for ch in channels:
        for fbg in fbgs_per_channel[ch]:
            # Получаем параметры модели для этого датчика: (A, mu, sigma)
            params = calibration[ch][fbg]['params']
            A, mu, sigma = params
            # Предсказанный сдвиг от колёсной пары
            predicted = (W / 2.0) * (response_function(xl, A, mu, sigma) +
                                     response_function(xr, A, mu, sigma))
            # Измеренный сдвиг
            measured = measured_shifts[ch][fbg]
            cost += (measured - predicted) ** 2
    return cost

# ----------------------------------------------------------------------
# 3. Генерация синтетических данных
np.random.seed(42)  # для воспроизводимости

# Конфигурация датчиков: каналы и FBG
channels = [1, 2]                     # два канала
fbgs_per_channel = {1: [1, 2, 3],     # в канале 1 три FBG
                    2: [1, 2]}        # в канале 2 два FBG

# Истинные значения искомых параметров (на основе которых сгенерируем "измерения")
W_true = 75.0          # г
xl_true = 120.0        # мм
xr_true = 200.0        # мм (расстояние между колёсами 90 мм)

# Калибровочные параметры для каждого датчика (гауссиан)
# Для упрощения зададим вручную, но можно было бы сгенерировать случайно.
calibration = {}
for ch in channels:
    calibration[ch] = {}
    for fbg in fbgs_per_channel[ch]:
        # Каждый датчик имеет свою чувствительность (A), центр (mu) и ширину (sigma)
        # Центры mu разнесены, чтобы покрыть диапазон x от 0 до 300 мм
        if ch == 1:
            if fbg == 1:
                params = (0.003, 100.0, 15.0)   # A, mu, sigma
            elif fbg == 2:
                params = (0.005, 150.0, 12.0)
            else:  # fbg == 3
                params = (0.004, 200.0, 18.0)
        else:  # ch == 2
            if fbg == 1:
                params = (0.004, 130.0, 14.0)
            else:  # fbg == 2
                params = (0.004, 180.0, 16.0)
        calibration[ch][fbg] = {'params': params, 'wavelength': None}  # wavelength не используется

# Генерируем "измеренные" сдвиги: вычисляем точные значения по истинным параметрам,
# затем добавляем гауссов шум.
measured_shifts = {}
for ch in channels:
    measured_shifts[ch] = {}
    for fbg in fbgs_per_channel[ch]:
        A, mu, sigma = calibration[ch][fbg]['params']
        exact = (W_true / 2.0) * (response_function(xl_true, A, mu, sigma) +
                                  response_function(xr_true, A, mu, sigma))
        # Добавляем шум со стандартным отклонением 0.05
        noise = np.random.normal(0, 0.010)
        measured_shifts[ch][fbg] = exact + noise

# Выведем для проверки
print("Сгенерированные измеренные сдвиги (с шумом):")
for ch in channels:
    for fbg in fbgs_per_channel[ch]:
        print(f"ch{ch}, fbg{fbg}: {measured_shifts[ch][fbg]:.3f}")

# ----------------------------------------------------------------------
# 4. Оптимизация с записью истории
# Список для хранения истории (каждый элемент: [W, xl, xr, cost])
history = []

def callback(xk):
    """Функция, вызываемая на каждой итерации оптимизатора.
       xk — текущие значения переменных (массив)"""
    cost_val = cost_function(xk, calibration, measured_shifts, channels, fbgs_per_channel)
    history.append([xk[0], xk[1], xk[2], cost_val])

# Начальное приближение
x0 = [100.0, 120.0, 215.0]   # W=100, xl=150, xr=235 (ширина ~85 мм)
# Запуск минимизации (метод Nelder-Mead)
result = minimize(
    cost_function,
    x0,
    args=(calibration, measured_shifts, channels, fbgs_per_channel),
    # method='Nelder-Mead',
    # method='BFGS',
    # method='Newton-CG',
    callback=callback,
    options={'maxiter': 500, 'disp': True}
)

# Результаты
W_opt, xl_opt, xr_opt = result.x
print("\n=== Результат оптимизации ===")
print(f"Истинные значения: W = {W_true}, xl = {xl_true}, xr = {xr_true}")
print(f"Найденные значения: W = {W_opt:.3f}, xl = {xl_opt:.3f}, xr = {xr_opt:.3f}")
print(f"Значение функции стоимости: {result.fun:.6f}")
print(f"Сообщение: {result.message}")

# ----------------------------------------------------------------------
# 5. Визуализация процесса оптимизации
history = np.array(history)
iterations = np.arange(len(history))

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
axes[0,1].plot(iterations, history[:,2], 'b-', label='xr (правое колесо)')
axes[0,1].axhline(y=W_true, color='r', linestyle='--', alpha=0.5, label='Истинный W')
axes[0,1].axhline(y=xl_true, color='g', linestyle='--', alpha=0.5, label='Истинный xl')
axes[0,1].axhline(y=xr_true, color='b', linestyle='--', alpha=0.5, label='Истинный xr')
axes[0,1].set_xlabel("Номер итерации")
axes[0,1].set_ylabel("Значение параметра")
axes[0,1].set_title("Изменение параметров")
axes[0,1].legend(loc='best')
axes[0,1].grid(True)

# Траектория в проекции (xl, xr)
axes[1,0].plot(history[:,1], history[:,2], 'k.-', alpha=0.7)
axes[1,0].scatter(history[0,1], history[0,2], color='green', s=80, label='Старт')
axes[1,0].scatter(history[-1,1], history[-1,2], color='red', s=80, label='Финиш')
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

# Дополнительный 3D-график траектории (W, xl, xr)
fig = plt.figure(figsize=(10, 7))
ax = fig.add_subplot(111, projection='3d')
ax.plot(history[:,0], history[:,1], history[:,2], 'b-', alpha=0.6)
ax.scatter(history[0,0], history[0,1], history[0,2], c='green', s=80, label='Старт')
ax.scatter(history[-1,0], history[-1,1], history[-1,2], c='red', s=80, label='Финиш')
ax.scatter(W_true, xl_true, xr_true, c='blue', marker='*', s=150, label='Истина')
ax.set_xlabel('W (вес)')
ax.set_ylabel('xl (мм)')
ax.set_zlabel('xr (мм)')
ax.set_title('Траектория оптимизации в пространстве (W, xl, xr)')
ax.legend()
plt.show()