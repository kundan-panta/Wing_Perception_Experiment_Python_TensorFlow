# -*- coding: utf-8 -*-
# %%
from math import floor
import numpy as np
import matplotlib.pyplot as plt
# from correct_biases import correct_biases
from tensorflow import keras

# %%
# all files to extract the data from (collected at multiple locations)
file_names = ['6', '12']
N_files = len(file_names)

# also convert the list into an array of floats
file_names_float = np.zeros(N_files)
for i in range(N_files):
    file_names_float[i] = float(file_names[i])
file_names_float += 3  # offset between ruler reading and distance from wing tip to wall

# choose trajectory name for which to process data
trajectory_name = '30deg'

# %%
# get stroke cycle period information from one of the files
t = np.around(np.loadtxt(file_names[0] + '/' + trajectory_name + '/' + 't.csv', delimiter=',', unpack=True), decimals=3)  # round to ms
cpg_param = np.loadtxt(file_names[0] + '/' + trajectory_name + '/' + 'cpg_param.csv', delimiter=',', unpack=True)

N = len(t)  # number of data points

# find points where a new stroke cycle is started
t_s = round(t[1] - t[0], 3)  # sample time
freq = cpg_param[-1, 0]  # store frequencies of each param set
t_cycle = 1 / freq  # stroke cycle time

# calculate number of cycles
t_total = t[-1]  # period of time over which data has been collected for each param set
t_total += t_s  # including first point
t_total = np.around(t_total, decimals=3)

# calculate number of data points per cycle
N_per_cycle = round(t_cycle / t_s)

print('Number of data points in a cycle:')
print(N_per_cycle)

# N_cycles = 50
N_cycles = floor(N / N_per_cycle)  # floor(total data points / data points in a cycle)
print('Number of stroke cycles:')
print(N_cycles)

# print number of unused data points
print('Number of unused data points:')
print(N - N_per_cycle * N_cycles)  # total # of data points - # of data points used

# number of training and testing stroke cycles
N_cycles_train = round(0.8 * N_cycles)
N_cycles_test = N_cycles - N_cycles_train
print('Number of training stroke cycles:')
print(N_cycles_train)
print('Number of testing stroke cycles:')
print(N_cycles_test)

# %%
N_inputs = 7

data = np.zeros((N_files * N_cycles * N_per_cycle, N_inputs))  # all data
x = np.zeros((N_files * N_cycles_train, N_inputs, N_per_cycle))
y = np.zeros((N_files * N_cycles_train))
x_val = np.zeros((N_files * N_cycles_test, N_inputs, N_per_cycle))
y_val = np.zeros((N_files * N_cycles_test))

############### alternative nominal FT - futhest from wall ###############
ft_pred = np.loadtxt('22/' + trajectory_name + '/' + 'ft_meas.csv', delimiter=',', unpack=True)

for k in range(N_files):
    # get data
    t = np.around(np.loadtxt(file_names[k] + '/' + trajectory_name + '/' + 't.csv', delimiter=',', unpack=True), decimals=3)  # round to ms
    # ft_pred = np.loadtxt(file_names[k] + '/' + trajectory_name + '/' + 'ft_pred.csv', delimiter=',', unpack=True)
    ft_meas = np.loadtxt(file_names[k] + '/' + trajectory_name + '/' + 'ft_meas.csv', delimiter=',', unpack=True)
    ang_meas = np.loadtxt(file_names[k] + '/' + trajectory_name + '/' + 'ang_meas.csv', delimiter=',', unpack=True)
    cpg_param = np.loadtxt(file_names[k] + '/' + trajectory_name + '/' + 'cpg_param.csv', delimiter=',', unpack=True)

    ############### take difference?? ###############
    ft_meas -= ft_pred

    data[(k * N_cycles * N_per_cycle):((k+1) * N_cycles * N_per_cycle), 0:6] = ft_meas[:, 0:(N_cycles * N_per_cycle)].T  # meassured FT
    data[(k * N_cycles * N_per_cycle):((k+1) * N_cycles * N_per_cycle), 6] = ang_meas[0, 0:(N_cycles * N_per_cycle)].T  # stroke angle

data = (data - np.min(data, axis=0)) / (np.max(data, axis=0) - np.min(data, axis=0))  # normalize
ft_meas_norm = data.reshape(N_files * N_cycles, N_per_cycle, N_inputs)
ft_meas_norm = ft_meas_norm.transpose(0, 2, 1)  # cycle -> FT components -> all data points of that cycle

# split data into training and testing sets
for k in range(N_files):
    x[N_cycles_train*k:N_cycles_train*(k+1), :, :] = ft_meas_norm[N_cycles*k:N_cycles*(k+1)-N_cycles_test, :, :]
    y[N_cycles_train*k:N_cycles_train*(k+1)] = k
    x_val[N_cycles_test*k:N_cycles_test*(k+1), :, :] = ft_meas_norm[N_cycles*k+N_cycles_train:N_cycles*(k+1), :, :]
    y_val[N_cycles_test*k:N_cycles_test*(k+1)] = k

# %%
model = keras.models.Sequential(
    [
        keras.layers.RNN(keras.layers.LSTMCell(128), return_sequences=True, input_shape=(N_inputs, N_per_cycle)),
        keras.layers.RNN(keras.layers.LSTMCell(128)),
        keras.layers.Dense(2),
    ]
)


model.compile(
    loss=keras.losses.SparseCategoricalCrossentropy(from_logits=True),
    optimizer="sgd",
    metrics=["accuracy"],
)

# model.summary()

# print("Learning rate:", model.optimizer.learning_rate.numpy())
lr = 0.002
keras.backend.set_value(model.optimizer.learning_rate, lr)
# print("Learning rate:", model.optimizer.learning_rate.numpy())

history = model.fit(
    x, y, validation_data=(x_val, y_val), epochs=1000, verbose=0
)

plt.plot(history.history['accuracy'])
plt.plot(history.history['val_accuracy'])
plt.title('model accuracy')
plt.ylabel('accuracy')
plt.xlabel('epoch')
plt.legend(['train', 'test'], loc='upper left')

plt.savefig('plots/2021.04.11/' + trajectory_name + '/lstm_filtered_' + str(file_names) + '_' + str(lr) + '.png')  # change this
plt.show()

# %%
