import re
import warnings
import copy
import os
import pandas as pd
import numpy as np
from skdh.completeness.helpers import from_unix

def compute_summary_metrics(completeness_master_dic, time_periods, timescales, measures):
    dic_summary = {}
    for period in time_periods:
        period_summary = []

        # Charging
        if completeness_master_dic['charging']['all'] is None:
            charging_time = None
        else:
            charging_time = np.sum(completeness_master_dic['charging'][period][:, 1] -
                                   completeness_master_dic['charging'][period][:, 0])
        period_summary.append(['charge time', charging_time])

        # Wearing
        if completeness_master_dic['wearing']['all'] is None:
            wear_time = None
        else:
            wear_time = np.sum(completeness_master_dic['wearing'][period]['wear_times'][:, 1] -
                               completeness_master_dic['wearing'][period]['wear_times'][:, 0])
            period_summary.append(['wear time', wear_time])
            no_wear_time = np.sum(completeness_master_dic['wearing'][period]['no_wear_times'][:, 1] -
                               completeness_master_dic['wearing'][period]['no_wear_times'][:, 0])
            period_summary.append(['no-wear time', no_wear_time])
            unknown_wear_time = np.sum(completeness_master_dic['wearing'][period]['unknown_times'][:, 1] -
                               completeness_master_dic['wearing'][period]['unknown_times'][:, 0])
            period_summary.append(['unknown wear time', unknown_wear_time])

        # Measures
        for measure in measures:
            if not measure in list(completeness_master_dic.keys()):
                period_summary.append([measure + ' completeness: 0 (no valid values)', 0])
            else:
                for key in completeness_master_dic[measure]['Completeness']['native'][period].items():
                    period_summary.append([measure + ', ' + key[0] + ', native', key[1]])
                if not timescales is None:
                    for timescale in timescales:
                        for key in completeness_master_dic[measure]['Completeness'][timescale][period].items():
                            period_summary.append([measure + ', ' + str(key[0]) + ', ' + str(timescale), key[1]])
                if 'data_gaps' in completeness_master_dic[measure].keys():
                    for data_gap in completeness_master_dic[measure]['data_gaps'][period].items():
                        for reason in data_gap[1].items():
                            period_summary.append([measure + ', data gap ' + str(data_gap[0]) + ', reason: ' + reason[0], reason[1]])

        period_summary = np.array(period_summary)
        dic_summary.update({period : period_summary[:, 1]})
    df_summary = pd.DataFrame(dic_summary, index=period_summary[:, 0])

    return df_summary


def dic_to_str(dic):
    if isinstance(dic, dict):
        keys = list(dic.keys())
        for key in keys:
            if not isinstance(key, str):
                dic[str(key)] = dic.pop(key)
            dic[str(key)] = dic_to_str(dic[str(key)])
    elif type(dic) == np.ndarray:
        if dic.dtype == np.dtype('O') or dic.dtype == np.dtype('<m8'):
            dic = dic.astype(str)

    return dic


def load_subject_data(subject_folder, subject, device_name, measures, ranges=None):

    data_dic = {'Subject ID' : subject,
                'Device Name' : device_name,
                'Measurement Streams' : {}}

    data_files = measures
    if 'Device Battery.csv' in os.listdir(subject_folder):
        data_files = data_files + ['Device Battery']
    if 'Wear Indicator.csv' in os.listdir(subject_folder):
        data_files = data_files + ['Wear Indicator']

    for measure in data_files:
        fname = subject_folder + '/' + measure + '.csv'
        df_raw = pd.read_csv(fname)

        assert 'Time Unix (ms)' in df_raw.keys(), '"Time Unix (ms)" column is missing from file ' + fname
        assert 'Sampling Frequency (Hz)' in df_raw.keys(), '"Sampling Frequency (Hz)" column is missing from file ' + fname
        assert measure in df_raw.keys(), measure + ' column is missing from file ' + fname
        assert df_raw['Time Unix (ms)'].iloc[0] < 10 ** 13 and df_raw['Time Unix (ms)'].iloc[0] > 10 ** 11, \
            'Unix times are too small or too big, they need to be in ms and should therefore be ~10^12'
        assert df_raw['Sampling Frequency (Hz)'].dtype in [float, int], 'sfreq must be a number (int/float)'

        if not 'Device ID' in df_raw.keys():
            df_raw['Device ID'] = 'n/a'

        if not 'Timezone' in df_raw.keys():
            warnings.warn('No timezone key given, will presume the timezone is EST (-5).')
            times = [from_unix(df_raw['Time Unix (ms)'], time_unit='ms', utc_offset=-5)]
            df_raw.set_index(times, inplace=True)
        else:
            times = [from_unix(df_raw['Time Unix (ms)'], time_unit='ms', utc_offset=df_raw['Timezone'])]
            df_raw.set_index(times, inplace=True)

        df_raw['Sampling Frequency (Hz)'] = np.array(1 / df_raw['Sampling Frequency (Hz)'] * 10 ** 9, 'timedelta64[ns]')
        df_raw = df_raw.iloc[np.where(~np.isnan(df_raw[measure]))[0]]
        df_raw = df_raw.iloc[np.argsort(df_raw['Time Unix (ms)'])]

        if not ranges is None:
            if measure in ranges.keys():
                df_raw = clean_df(df_raw, measure, ranges[measure][0], ranges[measure][1])
        if len(df_raw) > 0:
            if measure in ['Device Battery', 'Wear Indicator']:
                data_dic.update({measure: df_raw})
            else:
                data_dic['Measurement Streams'].update({measure : df_raw})

    return data_dic


def clean_df(df, col, val_min, val_max):
    df_cleaned = df.iloc[np.where(np.array([val_min <= df[col], df[col] <= val_max]).all(axis=0))[0]]
    if len(df_cleaned) == 0:
        warnings.warn(col + ' did not have a single valid value. Removing from analysis.')
    return df_cleaned


def check_hyperparameters(subject, subject_folder, device_name, fpath_output, measures, resample_width_mins,
                          gap_size_mins, ranges, data_gaps, time_periods, timescales):

    assert type(subject) == str, 'subject parameter should be a string, identifying the subject'
    assert os.path.isdir(subject_folder), 'subject_folder does not appear to exist'
    assert type(device_name) == str, 'device_name parameter should be a string, identifying the name of the device'
    assert os.path.isdir(fpath_output), 'fpath_output does not appear to exist'
    for measure in measures:
        assert os.path.isfile(subject_folder + measure + '.csv'), 'The file ' + subject_folder + measure + '.csv' +\
                                                                  'could not be found'
    assert type(resample_width_mins) in [int, float], str(resample_width_mins) + ' parameter has to be an int or float'
    assert type(gap_size_mins) in [int, float], str(gap_size_mins) + ' parameter has to be an int or float'
    assert gap_size_mins >= resample_width_mins, 'gap_size_mins should be greater or equal to resample_width_mins'
    if ranges is not None:
        assert type(ranges) == dict, 'ranges has to be a dictionary'
        for key in ranges.keys():
            assert key in measures, str(
                key) + ' from ranges parameter not in measure. All keys in the ranges variable must be in measures'
            assert ranges[key][1] > ranges[key][0], 'The second and first value in ranges are the upper and lower bounds, '+\
            'respectively, so the upper value must therefore be larger than the first. This was not the case for ' + \
                                                    str(key)
    if data_gaps is not None:
        assert type(data_gaps) == np.ndarray and data_gaps.dtype in ['timedelta64[s]', 'timedelta64[m]', 'timedelta64[h]'], \
            'data_gaps must be a numpy array of dtype timedelta64'
        assert len(np.unique(data_gaps)) == len(data_gaps), 'Each element in data_gaps must be unique'
    if timescales is not None:
        assert type(timescales) == np.ndarray and timescales.dtype in ['timedelta64[s]', 'timedelta64[m]', 'timedelta64[h]'], \
            'timescales must be a numpy array of dtype timedelta64'
        assert len(np.unique(timescales)) == len(timescales), 'Each element in timescales must be unique'
    if time_periods is not None and not time_periods == 'daily':
        assert type(time_periods) == list, 'time_periods must be a list'
        for time_period in time_periods:
            assert type(time_period) == tuple and len(time_period) == 2 and type(time_period[0]) == pd.Timestamp and \
                   type(time_period[1]) == pd.Timestamp, 'each element in time_periods must be a tuple of two elements, ' +\
                                                         'both being pd.Timestamp types'

    print('All hyperparameters passed input controls.')

    return


def compute_completeness_master(data_dic, data_gaps=None, time_periods=None, timescales=None):
    for time_period in time_periods:
        assert isinstance(time_period, tuple) and len(time_period) == 2 and \
               isinstance(time_period[0], pd._libs.tslibs.timestamps.Timestamp) \
            and isinstance(time_period[1], pd._libs.tslibs.timestamps.Timestamp) \
            and time_period[1] > time_period[0], \
            'time_period has to be a tuple with two date-time elements where time_period[1] is after time_period[0]'
    if not data_gaps is None:
        assert isinstance(data_gaps, np.ndarray) and \
               np.array([isinstance(data_gap, np.timedelta64) for data_gap in data_gaps]).all(), \
            'data_gaps has to be an array of np.timedelta64 elements'
    if not timescales is None:
        assert isinstance(timescales, np.ndarray) and \
               np.array([isinstance(timescale, np.timedelta64) for timescale in timescales]).all(), \
            'timescales has to be an array of np.timedelta64 elements'

    completeness_master_dic = {}

    if 'Device Battery' in list(data_dic.keys()):
        completeness_master_dic.update({'charging' : {'all' : find_charging_periods(data_dic)}})
        for time_period in time_periods:
            completeness_master_dic['charging'].update(
                {time_period: _find_time_periods_overlap(completeness_master_dic['charging']['all'], time_period)[0]})
    else:
        completeness_master_dic.update({'charging': {'all': None}})

    if 'Wear Indicator' in list(data_dic.keys()):
        completeness_master_dic.update({'wearing': {'all': find_wear_periods(data_dic)}})
        for time_period in time_periods:
            completeness_master_dic['wearing'].update({time_period: {
                key: _find_time_periods_overlap(completeness_master_dic['wearing']['all'][key], time_period)[0] for key in
                completeness_master_dic['wearing']['all'].keys()}})
    else:
        completeness_master_dic.update({'wearing': {'all': None}})

    for measure in data_dic['Measurement Streams'].keys():
        deltas = _find_gap_codes(data_dic, measure, completeness_master_dic['charging']['all'],
                                 completeness_master_dic['wearing']['all'])
        completeness_master_dic.update({measure : {'Completeness' :
                                                       compute_completeness(deltas, time_periods=time_periods,
                                                                            timescales=timescales,
                                                                            last_time=data_dic['Measurement Streams'][
                                                                                measure].index[-1])}})
        if not data_gaps is None:
            completeness_master_dic[measure].update({'data_gaps' : _compute_data_gaps(deltas, time_periods, data_gaps)})

    return completeness_master_dic


def find_charging_periods(data_dic):
    battery_diff = np.diff(data_dic['Device Battery']['Device Battery'])
    noise_lvl = 3 * np.nanstd(battery_diff)
    charging_starts = np.where(battery_diff > noise_lvl)[0]
    charging_periods = np.array([[data_dic['Device Battery'].index[start], data_dic['Device Battery'].index[start + 1]]
                                 for start in charging_starts])

    return charging_periods


def find_wear_periods(data_dic):
    wear_indicator = np.array([np.nan] * (len(data_dic['Wear Indicator']['Wear Indicator']) - 1))
    time_periods = np.array([[data_dic['Wear Indicator'].index[c], data_dic['Wear Indicator'].index[c + 1]] for c in range(len(data_dic['Wear Indicator']) - 1)])
    for c in range(len(time_periods)):
        if (time_periods[c][1] - time_periods[c][0]) <= data_dic['Wear Indicator']['Sampling Frequency (Hz)'].iloc[1:].iloc[c]:
            if data_dic['Wear Indicator']['Wear Indicator'].iloc[c] == data_dic['Wear Indicator']['Wear Indicator'].iloc[c + 1]:
                wear_indicator[c] = data_dic['Wear Indicator']['Wear Indicator'].iloc[c]
    wear_times = []
    no_wear_times = []
    unknown_times = []
    if wear_indicator[0] == 1:
        wear_times.append([time_periods[0][0], -1])
        current_ind = 1
    if wear_indicator[0] == 0:
        no_wear_times.append([time_periods[0][0], -1])
        current_ind = 0
    if np.isnan(wear_indicator[0]):
        unknown_times.append([time_periods[0][0], -1])
        current_ind = np.nan
    for c, time_period in enumerate(time_periods):
        if not wear_indicator[c] == current_ind:
            if current_ind == 1:
                wear_times[-1][1] = time_periods[c - 1][1]
            if current_ind == 0:
                no_wear_times[-1][1] = time_periods[c - 1][1]
            if np.isnan(current_ind):
                unknown_times[-1][1] = time_periods[c - 1][1]
            current_ind = wear_indicator[c]
            if wear_indicator[c] == 1:
                wear_times.append([time_period[0], -1])
                current_ind = 1
            if wear_indicator[c] == 0:
                no_wear_times.append([time_period[0], -1])
                current_ind = 0
            if np.isnan(wear_indicator[c]):
                unknown_times.append([time_period[0], -1])
                current_ind = np.nan
    if wear_indicator[-1] == 1:
        wear_times[-1][1] = time_periods[-1][1]
    if wear_indicator[-1] == 0:
        no_wear_times[-1][1] = time_periods[-1][1]
    if np.isnan(wear_indicator[-1]):
        unknown_times[-1][1] = time_periods[-1][1]
    wear_times = np.array(wear_times)
    no_wear_times = np.array(no_wear_times)
    unknown_times = np.array(unknown_times)

    return {'wear_times' : wear_times, 'no_wear_times' : no_wear_times, 'unknown_times' : unknown_times}


def _find_gap_codes(data_dic, measure, charging_periods, wearing_periods):

    no_wear_periods = wearing_periods['no_wear_times']
    dts = np.diff(data_dic['Measurement Streams'][measure].index)
    gap_codes = pd.DataFrame(data={'unknown' : np.ones(len(dts)),
                                   'normal': np.zeros(len(dts)),
                                   'charging': np.zeros(len(dts)),
                                   'no_wear': np.zeros(len(dts)),
                                   'dts' : dts,
                                   'Sampling Frequency (Hz)' : data_dic['Measurement Streams'][measure][
                                                                   'Sampling Frequency (Hz)'][:-1]},
                             index=data_dic['Measurement Streams'][measure].index[:-1])
    data_gaps = np.where((dts > data_dic['Measurement Streams'][measure]['Sampling Frequency (Hz)'][:-1]))[0]
    normals = np.where(dts <= data_dic['Measurement Streams'][measure]['Sampling Frequency (Hz)'][:-1])[0]
    gap_codes.iloc[normals, gap_codes.columns.get_loc('unknown')] = 0
    gap_codes.iloc[normals, gap_codes.columns.get_loc('normal')] = 1

    # Assign gap codes based on share of data gap
    for row_ind in data_gaps:
        data_gap_start = data_dic['Measurement Streams'][measure].index[row_ind]
        data_gap_end = data_dic['Measurement Streams'][measure].index[row_ind + 1]
        data_gap_duration = data_gap_end - data_gap_start

        # Charging
        charging_time = np.timedelta64(0)
        if not charging_periods is None:
            overlap = _find_time_periods_overlap(charging_periods, [data_gap_start, data_gap_end])[0]
            charging_time = np.sum(overlap[:, 1] - overlap[:, 0])

        # Non-wearing
        nonwear_time = np.timedelta64(0)
        if not no_wear_periods is None:
            overlap = _find_time_periods_overlap(no_wear_periods, [data_gap_start, data_gap_end])[0]
            nonwear_time = np.sum(overlap[:, 1] - overlap[:, 0])

        unknown_time = data_gap_duration - (nonwear_time + charging_time)

        gap_codes.iloc[row_ind, gap_codes.columns.get_loc('unknown')] = unknown_time / data_gap_duration
        gap_codes.iloc[row_ind, gap_codes.columns.get_loc('charging')] = charging_time / data_gap_duration
        gap_codes.iloc[row_ind, gap_codes.columns.get_loc('no_wear')] = nonwear_time / data_gap_duration

        assert np.sum(gap_codes.iloc[row_ind, gap_codes.columns.get_loc('unknown')] +
                      gap_codes.iloc[row_ind, gap_codes.columns.get_loc('normal')] +
                      gap_codes.iloc[row_ind, gap_codes.columns.get_loc('charging')] +
                      gap_codes.iloc[row_ind, gap_codes.columns.get_loc('no_wear')]) == 1, 'Sum of data gap reasons != 1'

    gap_codes.measure = measure

    return gap_codes


def _find_time_periods_overlap(periods, time_segment):
    """
    Find overlap between periods (an array of time periods) and time_segment (one time period). Returns an array of
    periods that overlap. If one period is partially inside time_segment, the portion inside will be added, so that
    all overlap time will be inside time_segment. Periods have to be sorted in time and non-overlapping.
    :param periods : np.array
    :param time_segment : list with len(list) = 2
    :return: period_overlap : np.array
    """
    period_overlap = np.array([], dtype=np.timedelta64).reshape(0, 2)
    period_inds = np.array([])
    if not len(periods) == 0 and not len(time_segment) == 0:
        periods = np.array(periods, dtype=np.datetime64)
        assert np.array(np.diff(periods[:, 0]) > np.timedelta64(0)).all(), 'Periods have to be sorted in time'
        assert np.array(periods[1:, 0] - periods[:-1, 1] >= np.timedelta64(0)).all(), 'Periods have to be non-overlapping'
        time_segment = (pd.Timestamp.to_numpy(time_segment[0]), pd.Timestamp.to_numpy(time_segment[1]))
        if np.array([periods[:, 0] <= time_segment[0], periods[:, 1] >= time_segment[1]]).all(axis=0).any():
            period_overlap = np.array([time_segment])
            period_inds = np.where(np.array([periods[:, 0] <= time_segment[0],
                                             periods[:, 1] >= time_segment[1]]).all(axis=0))[0]
        else:
            obs_periods_fully_inside = np.where(np.array([periods[:, 0] >= time_segment[0],
                                                          periods[:, 1] <= time_segment[1]]).all(axis=0))[0]
            obs_periods_beg = np.where(np.array([periods[:, 0] < time_segment[0],
                                                 periods[:, 1] > time_segment[0]]).all(axis=0))[0]
            obs_periods_end = np.where(np.array([periods[:, 0] < time_segment[1],
                                                 periods[:, 1] > time_segment[1]]).all(axis=0))[0]
            period_overlap = periods[obs_periods_fully_inside]
            period_inds = np.concatenate((obs_periods_beg, obs_periods_fully_inside, obs_periods_end))
            if len(obs_periods_beg) == 1:
                period_overlap = np.concatenate(([[time_segment[0], periods[:, 1][obs_periods_beg][0]]], period_overlap))
            if len(obs_periods_end) == 1:
                period_overlap = np.concatenate((period_overlap, [[periods[:, 0][obs_periods_end][0], time_segment[1]]]))

    return period_overlap, period_inds


def _find_time_periods_overlap_fraction(periods, time_segment, weights=None):
    """
    Find overlap fraction between periods (np.array) and time_segment (single list with 2 elements). Overlap fraction
    weighted by weights, which if given have to be the same size as periods. If not given, the overlap fraction will
    be a straight quota.
    :param periods:
    :param time_segment:
    :param weights:
    :return:
    """
    if weights is None:
        weights = np.ones(len(periods))
    assert len(weights) == len(periods), 'weights and periods have to be equal size'
    if np.array([periods[:, 0] <= time_segment[0], periods[:, 1] >= time_segment[1]]).all(axis=0).any():
        return weights[np.where(np.array([periods[:, 0] <= time_segment[0], periods[:, 1] >= time_segment[1]]).all(axis=0))[0]]
    else:
        period_overlap, period_inds = _find_time_periods_overlap(periods, time_segment)
        return np.sum((period_overlap[:, 1] - period_overlap[:, 0]) * weights[period_inds]) / (time_segment[1] - time_segment[0])


def calculate_completeness_timescale(deltas, time_periods, timescale, last_time):
    assert type(timescale) in [np.timedelta64, pd.core.series.Series, np.ndarray], \
        'type(timescale) must be np.timedelta64, pd.core.series.Series or np.ndarray'
    assert type(deltas) == pd.core.frame.DataFrame and 'dts' in deltas.keys(), 'deltas must be a Pandas dataframe'
    if type(timescale) == np.timedelta64:
        timescale = np.array([timescale] * len(deltas))
    dts_inds = np.where(deltas['dts'] > timescale)[0]
    if len(dts_inds) == 0:
        observation_periods = np.array([[deltas.index[0], last_time]])
    else:
        observation_periods = [[deltas.index[0], deltas.index[dts_inds[0]] + timescale[dts_inds[0]] / 2]]
        for c in range(len(dts_inds) - 1):
            observation_periods.append([deltas.index[dts_inds[c] + 1] - timescale[dts_inds[c] + 1] / 2,
                                        deltas.index[dts_inds[c + 1]] + timescale[dts_inds[c + 1]] / 2])
        if dts_inds[-1] == len(deltas) - 1:
            observation_periods.append([last_time - timescale[dts_inds[-1]] / 2, last_time])
        else:
            observation_periods.append([deltas.index[dts_inds[-1] + 1] - timescale[dts_inds[-1] + 1] / 2, last_time])
        observation_periods = np.array(observation_periods)
    reason_periods = {'periods' : {}, 'weights' : {}}
    for reason in ['normal', 'charging', 'no_wear', 'unknown']:
        reason_inds = np.where(deltas.iloc[dts_inds][reason] > 0)[0]
        reason_periods['weights'].update({reason : np.array(deltas.iloc[dts_inds][reason])})
        if len(reason_inds) > 0:
            if dts_inds[reason_inds][-1] == len(deltas) - 1:
                reason_periods['periods'].update(
                    {reason: np.array(
                        [deltas.index[dts_inds[reason_inds[:-1]]] + timescale[dts_inds[reason_inds[:-1]]] / 2,
                         deltas.index[dts_inds[reason_inds[:-1]] + 1] - timescale[
                             dts_inds[reason_inds[:-1]] + 1] / 2]).T.reshape(len(reason_inds[:-1]), 2)})
                reason_periods['periods'].update({reason : np.concatenate((reason_periods['periods'][reason], np.array(
                        [deltas.index[dts_inds[reason_inds[-1]]] + timescale[dts_inds[reason_inds[-1]]] / 2,
                         last_time - timescale[-1] / 2], dtype=np.datetime64).T.reshape((1, 2))), axis=0)})
            else:
                reason_periods['periods'].update({reason : np.array([deltas.index[dts_inds[reason_inds]] + timescale[dts_inds][reason_inds] / 2,
                                       deltas.index[dts_inds[reason_inds] + 1] - timescale[dts_inds[reason_inds] + 1] / 2]).T.reshape(len(reason_inds), 2)})
    data_completeness = {}
    if deltas.index[0] > time_periods[0][0]:
        if 'unknown' in reason_periods['periods'].keys():
            reason_periods['periods'].update({'unknown' : np.concatenate((np.array([[time_periods[0][0],
                                                                          observation_periods[0][0]]],
                                                                        dtype=np.datetime64),
                                                               reason_periods['periods']['unknown']), axis=0)})
            reason_periods['weights'].update({'unknown': np.insert(reason_periods['weights']['unknown'], 0, 1)})
        else:
            reason_periods['periods'].update({'unknown' : np.array([[time_periods[0][0], observation_periods[0][0]]], dtype=np.datetime64)})
            reason_periods['weights'].update({'unknown': np.array([1])})
    if last_time < time_periods[-1][1]:
        last_time_point = np.min([last_time + timescale[-1] / 2, time_periods[-1][1]])
        observation_periods = np.concatenate(
            (observation_periods, np.array([[last_time, last_time_point]])))
        if 'unknown' in reason_periods['periods'].keys():
            reason_periods['periods'].update({'unknown' : np.concatenate((reason_periods['periods']['unknown'],
                                                               np.array([[last_time_point, time_periods[-1][1]]],
                                                                        dtype=np.datetime64)), axis=0)})
            reason_periods['weights'].update({'unknown': np.append(reason_periods['weights']['unknown'], 1)})
        else:
            reason_periods['periods'].update({'unknown' : np.array([[last_time_point, time_periods[-1][1]]],
                                                                        dtype=np.datetime64)})
            reason_periods['weights'].update({'unknown': np.array([1])})

    for time_period in time_periods:
        data_completeness.update({time_period: {'Completeness' : _find_time_periods_overlap_fraction(observation_periods, time_period)}})
        for reason in reason_periods['periods'].keys():
            weights = reason_periods['weights'][reason][np.where(reason_periods['weights'][reason] > 0)[0]]
            data_completeness[time_period].update({'Missingness, ' + reason : _find_time_periods_overlap_fraction(reason_periods['periods'][reason], time_period, weights)})
    assert np.abs(np.sum(list(list(data_completeness.values())[0].values())) - 1) < .005, \
        'Completeness + Missingness less than 99.5% (should be 100%). Something is wrong!'
    return data_completeness


def compute_completeness(deltas, time_periods, last_time, timescales=None):
    completeness = {'native' : calculate_completeness_timescale(deltas=deltas, time_periods=time_periods,
                                                                timescale=deltas['Sampling Frequency (Hz)'],
                                                                last_time=last_time)}
    if not timescales is None:
        for timescale in timescales:
            completeness.update({timescale : calculate_completeness_timescale(deltas=deltas, time_periods=time_periods,
                                                                              timescale=timescale, last_time=last_time)})

    return completeness


def _compute_data_gaps(deltas, time_periods, data_gaps):

    # Assign data gaps based on majority vote
    reasons_ind = np.argmax(np.array([deltas['normal'], deltas['unknown'], deltas['no_wear'], deltas['charging']]), axis=0)
    deltas['gap_codes_majority'] = np.array(['normal', 'unknown', 'no_wear', 'charging'])[reasons_ind]

    data_gap_summary = {}
    for time_period in time_periods:
        data_gap_summary.update({time_period : {}})
        for data_gap in data_gaps:
            data_gap_inds = np.where(np.array([deltas['dts'] >= data_gap, deltas['dts'].index >= time_period[0],
                                               deltas['dts'].index < time_period[1]]).all(axis=0))[0]
            reasons = deltas['gap_codes_majority'].unique()
            data_gap_reason = {}
            for reason in reasons:
                data_gap_reason.update(
                    {reason: np.sum(deltas.iloc[data_gap_inds, deltas.columns.get_loc('gap_codes_majority')] == reason)})
            data_gap_summary[time_period].update({data_gap: data_gap_reason})

    return data_gap_summary


def truncate_data_dic(data_dic, time_period):
    data_dic_trunc = copy.deepcopy(data_dic)
    for stream in data_dic_trunc['Measurement Streams'].keys():
        data_dic_trunc['Measurement Streams'][stream] = data_dic_trunc['Measurement Streams'][stream].iloc[
            np.where(np.array([data_dic_trunc['Measurement Streams'][stream].index >= time_period[0],
                               data_dic_trunc['Measurement Streams'][stream].index <= time_period[1]]).all(axis=0))[0]]
    data_dic_trunc['Wear Indicator'] = data_dic_trunc['Wear Indicator'].iloc[
        np.where(np.array([data_dic_trunc['Wear Indicator'].index >= time_period[0],
                           data_dic_trunc['Wear Indicator'].index <= time_period[1]]).all(axis=0))[0]]
    data_dic_trunc['Device Battery'] = data_dic_trunc['Device Battery'].iloc[
        np.where(np.array([data_dic_trunc['Device Battery'].index >= time_period[0],
                           data_dic_trunc['Device Battery'].index <= time_period[1]]).all(axis=0))[0]]

    return data_dic_trunc


