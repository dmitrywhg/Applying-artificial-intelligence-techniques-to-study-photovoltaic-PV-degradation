# -*- coding: utf-8 -*-
"""final_1_k-means.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1kx-8jFfdJDHk1FTfOgrvNt6Js5rtV3QP

### data_cleaning
"""

import pandas as pd
import numpy as np
from scipy.ndimage import gaussian_filter1d
import matplotlib.pyplot as plt

# Read data files
pv_data = pd.read_csv('https://gitlab.in2p3.fr/energy4climate/public/sirta-pv1-data/-/raw/master/pv_data/2022/FranceWatts_20220101@08h01m12s_20220405@12h59m32s.csv?ref_type=heads')

pv_data = pv_data[['Date', 'Pmpp', 'Vmpp', 'Impp', 'Tmod']]
pv_data['Date'] = pd.to_datetime(pv_data['Date'])
pv_data = pv_data.set_index('Date')

meteo_data = pd.read_csv('https://gitlab.in2p3.fr/energy4climate/public/sirta-pv1-data/-/raw/master/meteo_data/2022/meteo_20220101@07h50m20s_20220406@14h21m10s.csv?ref_type=heads')

meteo_data = meteo_data[['Date', 'GPOA_pyrano']]
meteo_data.columns = ['Date', 'GPOA']
meteo_data['Date'] = pd.to_datetime(meteo_data['Date'])
meteo_data = meteo_data.set_index('Date')

pv_data, meteo_data = pv_data.loc['2022':'2022-03-31'], meteo_data.loc['2022':'2022-03-31']

# Minimum Intensity Threshold (MIT)
meteo_data = meteo_data[meteo_data['GPOA'] > 100]

# Keep positive values only
non_neg_cols = ['Impp', 'Vmpp', 'Pmpp']
for non_neg_col in non_neg_cols:
    pv_data = pv_data[pv_data[non_neg_col] > 0]

# Resample to closest 5s (meteo data is measured every 5s, pv data every 30s)
pv_data = pv_data.resample('5s').mean().dropna()
meteo_data = meteo_data.resample('5s').mean().dropna()

# Filter outliers using Gaussian 1D filter
def filter_outliers(data, sigma=5, out_thresh=0.05): #out_thresh: max error accepted (threshold to determine if a point is considered an outlier or not)
    days = sorted(set(data.index.strftime('%Y-%m-%d')))

    data_gauss = pd.DataFrame(index=data.index, columns=[col + '_gauss' for col in data.columns])

    for col in data.columns:
        for day in days: #apply filter on a daily basis to avoid influence from previous and future days
            data_gauss[col + '_gauss'].loc[day] = gaussian_filter1d(data[col].loc[day], sigma=sigma) #sigma=5 empirical value

        data_gauss[col + '_mape'] = np.abs(data_gauss[col + '_gauss'] - data[col]) / (data[col] + 1E-8) #percentage error between filtered and original data

    mape_cols = [col + '_mape' for col in data.columns]
    data_gauss = data_gauss[(data_gauss[mape_cols] <= out_thresh).all(axis=1)] #remove data rows with outliers in any of the measured variables

    data = data.loc[data_gauss.index] #keep data points with no outliers

    return data

pv_data, meteo_data = filter_outliers(pv_data, sigma=5), filter_outliers(meteo_data, sigma=5)

# Merge PV and Meteo data
data = pd.concat([pv_data, meteo_data], axis=1).dropna()

# Automatic detection of outliers
fig, ax = plt.subplots(constrained_layout=True)
ratio = data['Impp']/data['GPOA']
out_high = data[(data['Impp']/data['GPOA']) > (ratio.mean()+2*ratio.std())]
out_low = data[(data['Impp']/data['GPOA']) < (ratio.mean()-2*ratio.std())]
ax.scatter(data['GPOA'], data['Impp'])
ax.scatter(out_high['GPOA'], out_high['Impp'], c='red')
ax.scatter(out_low['GPOA'], out_low['Impp'], c='green')
ax.plot([0, 1000, 1000*1.4], [0, ratio.mean()*1000, ratio.mean()*1400], '--', c='black')
ax.set_xlabel('GPOA Irradiance [W/m$^2$]')
ax.set_ylabel('I$_{mpp}$ [A]')
fig.suptitle('Automatic Detection of Outliers Outside 2*\u03C3 Region \n (Red & Green Points)')

data = data.drop(out_high.index)

data = data.drop(out_low.index)

# Plot Impp vs Irradiance
fig, ax = plt.subplots(constrained_layout=True)
sc = ax.scatter(data['GPOA'], data['Impp'], c=data.index)
cbar = plt.colorbar(sc)
cbar.ax.set_yticklabels(pd.to_datetime(cbar.get_ticks()).strftime(date_format='%Y-%m-%d'))
ax.plot([0, 1000, 1000*1.4], [0, ratio.mean()*1000, ratio.mean()*1400], '--', c='black')
ax.set_xlabel('GPOA Irradiance [W/m$^2$]')
ax.set_ylabel('I$_{mpp}$ [A]')

# Check daily profiles
fig, ax = plt.subplots(constrained_layout=True)
ax.plot(data['Impp'], label='I$_{MPP}$')
ax.set_ylabel('I$_{MPP}$ [A]')
ax2 = ax.twinx()
ax2.plot(data['GPOA'], c='orange', label='GPOA')
ax2.set_ylabel('GPOA Irradiance [W/m$^2$]')
fig.legend()

fig, ax = plt.subplots(constrained_layout=True)
ax.plot(data['Vmpp'], label='V$_{MPP}$')
ax.set_ylabel('V$_{MPP}$ [V]')
ax2 = ax.twinx()
ax2.plot(data['GPOA'], c='orange', label='GPOA')
ax2.set_ylabel('GPOA Irradiance [W/m$^2$]')
fig.legend()

"""###Utils"""

pip install pvlib

import pvlib
from pvlib import iotools, location

from pvlib import ivtools, pvsystem
import itertools
from sklearn.metrics import mean_absolute_percentage_error as mape
from sklearn.metrics import mean_squared_error as mse

modules = {'cSi': {'Name': 'FranceWatts',
                    'celltype': 'monoSi',

                    'V_mp_ref': 30.52,
                    'I_mp_ref': 8.21,

                    'V_oc_ref': 37.67,
                    'I_sc_ref': 8.64,

                    'alpha_sc': 0.02 / 100 * 8.64,
                    'beta_oc': -0.36 / 100 * 37.67,

                    'gamma_pmp': -0.48,
                    'cells_in_series': 60,
                    'temp_ref': 25,
                    'power_tolerance': 3},
           'aSi': {'Name': 'Sharp', 'celltype': 'amorphous', 'V_mp_ref': 45.4, 'I_mp_ref': 2.82, 'V_oc_ref': 59.8,
                    'I_sc_ref': 3.45, 'alpha_sc': 0.07 / 100 * 3.45, 'beta_oc': -0.3 / 100 * 59.8, 'gamma_pmp': -0.24,
                    'cells_in_series': 180, 'temp_ref': 25, 'power_tolerance': 10},
           'CIS': {'Name': 'SolarFrontier', 'celltype': 'cis', 'V_mp_ref': 81.5, 'I_mp_ref': 1.85, 'V_oc_ref': 108,
              'I_sc_ref': 2.2, 'alpha_sc': 0.01 / 100 * 2.2, 'beta_oc': -0.3 / 100 * 108, 'gamma_pmp': -0.31,
              'cells_in_series': 184, 'temp_ref': 25, 'power_tolerance': 3.33},
           'HIT': {'Name': 'Panasonic', 'celltype': 'monoSi', 'V_mp_ref': 43.7, 'I_mp_ref': 5.51, 'V_oc_ref': 52.4,
            'I_sc_ref': 5.85, 'alpha_sc': 1.76 / 1000, 'beta_oc': -0.131, 'gamma_pmp': -0.29, 'cells_in_series': 72,
             'temp_ref': 25, 'power_tolerance': 10},
           'CdTe': {'Name': 'FirstSolar', 'celltype': 'cdte', 'V_mp_ref': 48.3, 'I_mp_ref': 1.71, 'V_oc_ref': 60.8,
              'I_sc_ref': 1.94, 'alpha_sc': 0.04 / 100 * 1.94, 'beta_oc': -0.27 / 100 * 60.8, 'gamma_pmp': -0.25,
              'cells_in_series': 154 / 2, 'temp_ref': 25, 'power_tolerance': 5},
           }

def search_space(data, module, nb_vals=[5]*5, freq=0.5, meas_unc=7.2):
    ''' Inputs:
    data: DataFrame of production data
    module: module specs (dictionary)
    freq: frequency of measurements in min
    meas_unc: measurement uncertainty (%)
    nb_vals: number of discrete values considered for each parameter (list) '''

    # Calculate the amount of energy (kWh) produced by the PV system during the analysis period
    pv_perf = pd.DataFrame(index=['Measured', 'Ideal'], columns=['Energy Production'])
    pv_perf.loc['Measured'] = data['Pmpp'].sum()*freq/60/1000

    # Calculate the amount of energy (kWh) that would be "ideally" produced by the PV system
    IL_ref, Io_ref, Rs_ref, Rsh_ref, a_ref, module['Adjust'] = ivtools.sdm.fit_cec_sam(celltype=module['celltype'],
                                                                                       v_mp=module['V_mp_ref'],
                                                                                       i_mp=module['I_mp_ref'],
                                                                                       v_oc=module['V_oc_ref'],
                                                                                       i_sc=module['I_sc_ref'],
                                                                                       alpha_sc=module['alpha_sc'],
                                                                                       beta_voc=module['beta_oc'],
                                                                                       gamma_pmp=module['gamma_pmp'],
                                                                                       cells_in_series=module['cells_in_series'],
                                                                                       temp_ref=module['temp_ref'])

    IL_adj, Io_adj, Rs_adj, Rsh_adj, a_adj = pvsystem.calcparams_cec(data['GPOA'], data['Tmod'],
                                                                        alpha_sc=module['alpha_sc'],
                                                                        I_L_ref=IL_ref, I_o_ref=Io_ref,
                                                                        R_s=Rs_ref, R_sh_ref=Rsh_ref, a_ref=a_ref,
                                                                        Adjust=module['Adjust'])

    Rs_adj = 1000/data['GPOA']*Rs_adj

    mpp_sim = pvsystem.max_power_point(photocurrent=IL_adj, saturation_current=Io_adj, resistance_series=Rs_adj, resistance_shunt=Rsh_adj, nNsVth=a_adj)

    pv_perf.loc['Ideal'] = mpp_sim['p_mp'].sum()*freq/60/1000

    # Calculate the (extreme) performance drop w.r.t. ideal production
    pv_perf_drop = float(pv_perf.loc['Measured']/pv_perf.loc['Ideal'])

    max_perf_drop = pv_perf_drop * (1-meas_unc/100) / (1+module['power_tolerance']/100)
    print('pv_perf_drop loss, max_perf_drop: ', float(pv_perf_drop)*100, float(max_perf_drop)*100)

    module['P_mp_ref'] = module['V_mp_ref']*module['I_mp_ref']
    pmp_min = module['P_mp_ref']*max_perf_drop
    pmp_max = module['P_mp_ref']*(1+module['power_tolerance']/100)

    ref_params = [IL_ref, Io_ref, Rs_ref, Rsh_ref, a_ref]
    param_ranges = []

    for i in range(len(ref_params)):
        p = [1]*5
        sign = 1
        p[i] -= 0.01*sign

        IL, Io, Rs, Rsh, a = np.multiply(ref_params, p)
        pmp = pvsystem.singlediode(IL, Io, Rs, Rsh, a)['p_mp']

        if pmp < module['P_mp_ref']:
            sign = 1
        else:
            sign = -1

        while pmp > pmp_min:
            p[i] -= 0.01*sign
            IL, Io, Rs, Rsh, a = np.multiply(ref_params, p)
            pmp = pvsystem.singlediode(IL, Io, Rs, Rsh, a)['p_mp']

        p_dec = p[i]

        if i == 2 and pvsystem.singlediode(IL_ref, Io_ref, Rs_ref*1E-3, Rsh_ref, a_ref)['p_mp'] < pmp_max:  #in some cases even if Rs drops to 0 the power is still lower than the desired value
            p[i] = 1E-2
            pmp = pmp_max
        elif i == 3 and pvsystem.singlediode(IL_ref, Io_ref, Rs_ref, Rsh_ref*1E4, a_ref)['p_mp'] < pmp_max: #above a certain threshold Rsh no longer impacts  Pmpp
            p[i] = 1 + module['power_tolerance']/100
            pmp = pmp_max
        else:
            p[i] = 1
            p[i] += 0.01 * sign

        while pmp < pmp_max:
            p[i] += 0.01*sign
            IL, Io, Rs, Rsh, a = np.multiply(ref_params, p)
            pmp = pvsystem.singlediode(IL, Io, Rs, Rsh, a)['p_mp']

        p_inc = p[i]

        ref_value = ref_params[i]
        if i == 1:
            param_ranges.append(np.logspace(np.log10(ref_value*min(p_dec, p_inc)), np.log10(ref_value*max(p_dec, p_inc)), nb_vals[i]))
        else:
            param_ranges.append(np.linspace(ref_value*min(p_dec, p_inc), ref_value*max(p_dec, p_inc), nb_vals[i]))

    combs = list(itertools.product(*param_ranges)) #get all the possible parameter combinations

    ss = pd.DataFrame(combs, columns=['IL', 'Io', 'Rs', 'Rsh', 'a'])
    ss['Rsh'][ss['Rsh'] < 0] = 1

    # Remove unnecessary combinations to evaluate
    ss[['i_mp', 'v_mp', 'p_mp']] = pvsystem.max_power_point(ss['IL'], ss['Io'], ss['Rs'], ss['Rsh'], ss['a'])
    ss = ss[ss['p_mp'] >= pmp_min]
    ss = ss[ss['p_mp'] <= pmp_max]

    return param_ranges, ss

def get_daily_data(data, gpoa_interval=100, points_gpoa_bin=5, temp_interval=5, points_temp_bin=5):
    # Irradiance bins
    data['gpoa_bin'] = np.floor(data['GPOA'] / gpoa_interval) * gpoa_interval  #split gpoa data into bins
    gpoa_count = data['gpoa_bin'].value_counts()  #count the number of data points per bin
    data_gpoa = data[data['gpoa_bin'].isin(gpoa_count[gpoa_count > points_gpoa_bin].index)]

    gpoa_dates = []
    for gpoa_val in data_gpoa['gpoa_bin'].unique():
        gpoa_dates.extend(data[data['gpoa_bin']==gpoa_val].sample(points_gpoa_bin, random_state=0).index)

    # Temperature bins
    data['temp_bin'] = np.floor(data['Tmod'] / temp_interval) * temp_interval  #split temp data into bins
    temp_count = data['temp_bin'].value_counts()  #count the number of data points per bin
    data_temp = data[data['temp_bin'].isin(temp_count[temp_count > points_temp_bin].index)]

    temp_dates = []
    for temp_val in data_temp['temp_bin'].unique():
        temp_dates.extend(data[data['temp_bin']==temp_val].sample(points_temp_bin, random_state=0).index)

    train_dates = set(gpoa_dates + temp_dates)

    return data.loc[list(train_dates)]

def get_likelihood(IL, Io, Rs, Rsh, a, daily_data, alpha_sc, Adjust):
    IL_adj, Io_adj, Rs_adj, Rsh_adj, a_adj = pvsystem.calcparams_cec(daily_data['GPOA'], daily_data['Tmod'],
                                                        alpha_sc=alpha_sc,
                                                        I_L_ref=IL,
                                                        I_o_ref=Io,
                                                        R_s=Rs,
                                                        R_sh_ref=Rsh,
                                                        a_ref=a,
                                                        Adjust=Adjust)

    Rs_adj = 1000/daily_data['GPOA']*Rs

    mpp_sim = pvsystem.max_power_point(photocurrent=IL_adj, saturation_current=Io_adj, resistance_series=Rs_adj, resistance_shunt=Rsh_adj, nNsVth=a_adj)

    mape_err = mape([daily_data['Impp'], daily_data['Vmpp'], daily_data['Pmpp']], [mpp_sim['i_mp'], mpp_sim['v_mp'], mpp_sim['p_mp']])*100
    rmse_err = np.sqrt(mse([daily_data['Impp'], daily_data['Vmpp'], daily_data['Pmpp']], [mpp_sim['i_mp'], mpp_sim['v_mp'], mpp_sim['p_mp']]))

    err = (mape_err+rmse_err)/2

    return np.exp(-err)

"""###K-means"""

from sklearn.cluster import KMeans

# Import data
pv_tech = 'cSi'
save_dir = 'results'

data = pd.read_csv(f'data_{pv_tech}.csv')
data['Date'] = pd.to_datetime(data['Date'])
data = data.set_index('Date')

data = data.loc['2022':'2022-03-31']

from google.colab import drive
drive.mount('/content/drive')

# Define module datasheet specs
module = modules[pv_tech]

pip install nrel-pysam

# Estimate the reference SDM parameters using datasheet specs
IL_ref, Io_ref, Rs_ref, Rsh_ref, a_ref, module['Adjust'] = ivtools.sdm.fit_cec_sam(
    celltype=module['celltype'],
    v_mp=module['V_mp_ref'],
    i_mp=module['I_mp_ref'],
    v_oc=module['V_oc_ref'],
    i_sc=module['I_sc_ref'],
    alpha_sc=module['alpha_sc'],
    beta_voc=module['beta_oc'],
    gamma_pmp=module['gamma_pmp'],
    cells_in_series=module['cells_in_series'],
    temp_ref=module['temp_ref']
)

# Define search space
param_ranges, bpe = search_space(data, module, nb_vals=[10]*5, freq=0.5, meas_unc=7.2)
print(len(bpe))

# Choose number of days to evaluate
days = np.array(sorted(set(data.index.date)))
conf_intervals = pd.DataFrame()
th_pm = 90 #90% confidence interval

num_clusters = 5 # количество кластеров
kmeans = KMeans(n_clusters=num_clusters)
for day in days:
    day = day.strftime('%Y-%m-%d')
    print(day)
    daily_data = get_daily_data(data.loc[day], points_gpoa_bin=3, points_temp_bin=3)
    if len(daily_data) > 10:
        print(day)

        bpe['Likelihood'] = bpe.apply(lambda row: get_likelihood(row['IL'], row['Io'], row['Rs'], row['Rsh'], row['a'], daily_data, module['alpha_sc'], module['Adjust']), axis=1)

        kmeans.fit(bpe[['Likelihood']])
        bpe['Cluster'] = kmeans.labels_

        # Получаем средние значения для каждого кластера
        cluster_means = bpe.groupby('Cluster').mean().reset_index()

        # Получаем 90% доверительный интервал
        conf_int = cluster_means.sort_values('Likelihood', ascending=False)
        conf_int.index = [day] * len(conf_int)

        conf_intervals = pd.concat([conf_intervals, conf_int])

conf_intervals.index = pd.to_datetime(conf_intervals.index)

conf_intervals_iv = pvsystem.singlediode(conf_intervals['IL'], conf_intervals['Io'], conf_intervals['Rs'], conf_intervals['Rsh'], conf_intervals['a'])
conf_intervals_iv = conf_intervals_iv[['p_mp', 'v_oc', 'i_sc', 'v_mp', 'i_mp']]

# Print expected values for the module SDM parameters and IV properties
bpe_iv = pvsystem.singlediode(bpe['IL'], bpe['Io'], bpe['Rs'], bpe['Rsh'], bpe['a'])

expected_vals = []
for param in ['IL', 'Io', 'Rs', 'Rsh', 'a']:
    expected_vals.append(cluster_means[param].mean())  # Используем средние значения кластеров
expected_vals = pd.DataFrame([expected_vals], columns=['IL', 'Io', 'Rs', 'Rsh', 'a'])
print('Expected Values')
print(expected_vals)

expected_vals_iv = []
for iv_prop in ['p_mp', 'v_mp', 'i_mp', 'v_oc', 'i_sc']:
    expected_vals_iv.append((bpe_iv[iv_prop].mean()))  # Используем средние значения кластеров
expected_vals_iv = pd.DataFrame([expected_vals_iv], columns=['p_mp', 'v_mp', 'i_mp', 'v_oc', 'i_sc'])
print('Expected Values')
print(expected_vals_iv)

#bpe.to_csv(f'{save_dir}/bpe_{

# Сохранение файлов
bpe.to_csv(f'{save_dir}/bpe_{pv_tech}.csv')
conf_intervals.to_csv(f'{save_dir}/conf_intervals_{pv_tech}.csv')
conf_intervals_iv.to_csv(f'{save_dir}/conf_intervals_iv_{pv_tech}.csv')

"""###Plots"""

results_dir = 'results/'
import os

# Задаем путь к директории
results_dir = 'results/'

# Создаем директорию, если она не существует
if not os.path.exists(results_dir):
    os.makedirs(results_dir)

import matplotlib.pyplot as plt
import seaborn
from pvlib import pvsystem

pv_tech = 'cSi'

bpe.to_csv(f'{save_dir}/bpe_{pv_tech}.csv')

bpe = pd.read_csv(results_dir + f'bpe_{pv_tech}.csv', index_col=0)
bpe_iv = pvsystem.singlediode(bpe['IL'], bpe['Io'], bpe['Rs'], bpe['Rsh'], bpe['a'])
bpe_iv['Cluster'] = bpe['Cluster']

conf_intervals = pd.read_csv(results_dir + f'conf_intervals_{pv_tech}.csv', index_col=0)
conf_intervals.index = pd.to_datetime(conf_intervals.index)
days = sorted(set(conf_intervals.index))

#conf_intervals_iv = pd.read_csv(results_dir + f'conf_intervals_iv_{pv_tech}.csv', index_col=0)
#conf_intervals_iv.index = pd.to_datetime(conf_intervals_iv.index)

module = modules[pv_tech]
module['P_mp_ref'] = module['V_mp_ref']*module['I_mp_ref']

IL_ref, Io_ref, Rs_ref, Rsh_ref, a_ref, module['Adjust'] = ivtools.sdm.fit_cec_sam(celltype=module['celltype'], v_mp=module['V_mp_ref'], i_mp=module['I_mp_ref'], v_oc=module['V_oc_ref'], i_sc=module['I_sc_ref'], alpha_sc=module['alpha_sc'], beta_voc=module['beta_oc'], gamma_pmp=module['gamma_pmp'], cells_in_series=module['cells_in_series'], temp_ref=module['temp_ref'])
kB, q = 1.38 * 10**-23, 1.602 * 10**-19
ref_values = [IL_ref, Io_ref, Rs_ref, Rsh_ref, a_ref]
Vth = kB*(module['temp_ref']+273.15)/q

data = pd.DataFrame(data=[[module['P_mp_ref'], 1000, 25]], columns=['Pmpp', 'GPOA', 'Tmod'])
param_ranges, _ = search_space(data, module, nb_vals=[2]*5, freq=0.5, meas_unc=0)

params = ['IL', 'Io', 'Rs', 'Rsh', 'a']
param_labels = ['I$_L$', 'I$_o$', 'R$_s$', 'R$_{sh}$', 'a']
param_units = ['A', 'A', 'Ω', 'Ω', 'unitless']
param_scales = ['linear', 'log', 'linear', 'linear', 'linear']

iv_props = ['P$_{MPP}$', 'V$_{MPP}$', 'I$_{MPP}$', 'V$_{oc}$', 'I$_{sc}$']
iv_props_units = ['W', 'V', 'A', 'V', 'A']

expected_vals = []
for param in ['IL', 'Io', 'Rs', 'Rsh', 'a']:
    expected_vals.append(cluster_means[param].mean())  # Используем средние значения кластеров
expected_vals = pd.DataFrame([expected_vals], columns=['IL', 'Io', 'Rs', 'Rsh', 'a'])
print('Expected Values')
print(expected_vals)



expected_vals_iv = []
for iv_prop in ['p_mp', 'v_mp', 'i_mp', 'v_oc', 'i_sc']:
    expected_vals_iv.append((bpe_iv[iv_prop].mean()))  # Используем средние значения кластеров
expected_vals_iv = pd.DataFrame([expected_vals_iv], columns=['p_mp', 'v_mp', 'i_mp', 'v_oc', 'i_sc'])
print('Expected Values')
print(expected_vals_iv)

# Prediction precision
for i, iv_prop in enumerate(['p_mp', 'v_mp', 'i_mp', 'v_oc', 'i_sc']):
    v_min, v_max = conf_intervals_iv.loc[days[-1], iv_prop].min(), conf_intervals_iv.loc[days[-1], iv_prop].max()
    v_exp = expected_vals_iv.loc[0, iv_prop]
    # print(f'{iv_prop}: {np.round(v_min - v_exp, 2)}{iv_props_units[i]} {np.round(v_max - v_exp, 2)}{iv_props_units[i]}')
    print(f'{iv_prop}: {np.round((v_min - v_exp) / v_exp * 100, 2)}% {np.round((v_max - v_exp) / v_exp * 100, 2)}%')

# IV properties Histogram
# SDM Param Dist
fig, ax = plt.subplots(1, 5, figsize=(10, 2.5), sharey=True, constrained_layout=True)
ax[0].set_ylim([0, 1])
ax[0].set_ylabel('Probability')

for i, param in enumerate(params):
    # Группируем данные
    grouped_data = bpe.groupby(param).sum()

    # Получаем значения для построения графиков
    x_values = grouped_data.index
    y_values = grouped_data['Cluster'].values

    # Нормализация для получения вероятностей
    total = y_values.sum()
    probabilities = y_values / total

    if param == 'a':
        adjusted_x_values = x_values / Vth / module['cells_in_series']
        ax[i].plot(adjusted_x_values, probabilities)  # Используем вероятности для графика
        ax[i].set_xlabel(f'n [{param_units[i]}]')
        n_ref = ref_values[i] / Vth / module['cells_in_series']
        ax[i].plot([n_ref] * 2, [0, 1], '--')
        ax[i].axvspan(param_ranges[i][0] / Vth / module['cells_in_series'], param_ranges[i][1] / Vth / module['cells_in_series'], alpha=0.15, color='orange')

    else:
        ax[i].plot(x_values, probabilities)  # Используем вероятности для графика
        ax[i].set_xlabel(f'{param_labels[i]} [{param_units[i]}]')
        ax[i].plot([ref_values[i]] * 2, [0, 1], '--')
        ax[i].axvspan(param_ranges[i][0], param_ranges[i][1], alpha=0.15, color='orange')

    # Вывод значений вероятностей
    for j in range(len(probabilities)):
        print(f'{param_labels[i]} [{param_units[i]}]: Value = {x_values[j]:.4f}, Probability = {probabilities[j]:.4f}')

    ax[i].set_xscale(param_scales[i])

fig.suptitle('Values at STC')
plt.show()

# Confidence Intervals
fig, ax = plt.subplots(5, sharex=True, figsize=(10, 10), constrained_layout=True)
for i, iv_prop in enumerate(['p_mp', 'v_mp', 'i_mp', 'v_oc', 'i_sc']):
    seaborn.boxplot(x=conf_intervals_iv.loc[days[::2]].index.date, y=conf_intervals_iv.loc[days[::2], iv_prop],
                    showfliers=True, ax=ax[i],
                    showmeans=False, meanline=False,
                    flierprops=dict(marker='o', markersize=3))
    ax[i].set_ylabel(f'{iv_props[i]} [{iv_props_units[i]}]')

plt.xticks(rotation=45)
fig.suptitle('90% Confidence Interval (Values at STC)')
plt.locator_params(axis='x', nbins=9)

fig, ax = plt.subplots(5, sharex=True, figsize=(10, 10), constrained_layout=True)
for i, iv_prop in enumerate(params):
    seaborn.boxplot(x=conf_intervals.loc[days[::2]].index.date, y=conf_intervals.loc[days[::2], iv_prop],
                    showfliers=True, ax=ax[i],
                    showmeans=False, meanline=False,
                    flierprops=dict(marker='o', markersize=3))
    ax[i].set_ylabel(f'{param_labels[i]} [{param_units[i]}]')
    ax[i].set_yscale(param_scales[i])

plt.xticks(rotation=45)
fig.suptitle('90% Confidence Interval (Values at STC)')
plt.locator_params(axis='x', nbins=9)

import pandas as pd
import matplotlib.pyplot as plt

# Пример данных
# bpe_iv - ваш DataFrame с данными
# Замените на ваши данные
bpe_iv = pd.DataFrame({
    'Cluster': ['A', 'A', 'B', 'B', 'C'],
    'p_mp': [0.1, 0.3, 0.2, 0.4, 0.3],
    'v_mp': [1.0, 1.2, 1.1, 1.3, 1.2],
    'i_mp': [5, 4, 6, 5, 7],
    'v_oc': [10, 10.5, 10.2, 10.3, 10.4],
    'i_sc': [15, 14, 15, 16, 14],
})

iv_props = ['p_mp', 'v_mp', 'i_mp', 'v_oc', 'i_sc']
iv_props_units = ['V', 'V', 'A', 'V', 'A']

# IV properties Histogram
fig, ax = plt.subplots(1, 5, figsize=(13, 2.5), sharey=True, constrained_layout=True)

# Словарь для хранения вероятностей
probabilities = {}

for i, iv_prop in enumerate(iv_props):
    # Группируем данные по кластерам для IV свойств
    cluster_data = bpe_iv.groupby('Cluster')[iv_prop].sum()

    # Рассчитываем вероятности
    total = cluster_data.sum()
    prob = cluster_data / total

    # Сохраняем значения вероятностей
    probabilities[iv_prop] = prob

    # Строим гистограмму для каждого IV свойства
    ax[i].bar(cluster_data.index, prob, alpha=0.6)

    ax[i].set_xlabel(f'{iv_prop} [{iv_props_units[i]}]')

ax[0].set_ylim([0, 1])
ax[0].set_ylabel('Probability')
fig.suptitle('IV Properties Distribution at STC')

plt.show()

# Печатаем значения вероятностей
for iv_prop, prob in probabilities.items():
    print(f'Пробabilities for {iv_prop}:')
    print(prob)

import time

# Продолжительность в секундах (2 часа)
duration = 2 * 60 * 60

# Начало таймера
start_time = time.time()

while (time.time() - start_time) < duration:
    # Ваш код здесь (например, просто ждем)
    time.sleep(60)  # Ждем 1 минуту между итерациями
    print("Сессия активна, прошло времени (в секундах):", time.time() - start_time)

print("Хотя время закончилось, сессия может быть отключена.")