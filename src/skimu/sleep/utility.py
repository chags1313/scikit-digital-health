"""
Utility functions required for sleep metric generation

Yiorgos Christakis
Pfizer DMTI 2021
"""
from numpy import any, asarray, arctan, pi, roll, abs, argmax, diff, nonzero, insert, sqrt, pad, \
    int_, append, argsort, sort, cumsum, sum, float_, minimum

from skimu.utility import rolling_mean, rolling_sd, rolling_median

__all__ = [
    "rle", "compute_z_angle", "compute_absolute_difference", "drop_min_blocks", "arg_longest_bout",
    "gini"
]


def get_weartime(acc_rmed, temp, fs, move_thresh, temp_thresh):
    """
    Compute the wear time using acceleration and temperature data.

    Parameters
    ----------
    acc_rmed : numpy.ndarray
        Rolling median acceleration with 5s windows and 1 sample skips.
    temp : numpy.ndarray
        Raw temperature data.
    fs : float
        Sampling frequency.
    move_thresh : float
        Threshold to classify acceleration as wear/nonwear
    temp_thresh : float
        Temperature threshold to classify as wear/nonwear

    Returns
    -------
    wear : numpy.ndarray
        (N, 2) array of [start, stop] indices of blocks of wear time.
    """
    n5 = int(5 * fs)
    # rolling 5s mean (non-overlapping windows)
    mn = rolling_mean(acc_rmed, n5, n5, axis=0)
    # rolling 30min StDev.  5s windows -> 12 windows per minute
    acc_rsd = rolling_sd(mn, 12 * 30, 1, axis=0, return_previous=False)

    # rolling 5s median of temperature
    rmd = rolling_median(temp, n5, skip=1, pad=False)
    # rolling 5s mean (non-overlapping)
    mn = rolling_mean(rmd, n5, n5)
    # rolling 5m median
    temp_rmd = rolling_median(mn, 12 * 5, skip=1, pad=False)

    move_mask = any(acc_rsd > move_thresh, axis=1)
    temp_mask = temp_rmd >= temp_thresh

    # pad the movement mask, temperature mask is the correct size
    npad = temp_mask.size - move_mask.size
    move_mask = pad(move_mask, (0, npad), mode="constant", constant_values=0)

    dwear = diff((move_mask | temp_mask).astype(int_))

    starts = nonzero(dwear == 1)[0] + 1
    stops = nonzero(dwear == -1)[0] + 1

    if move_mask[0] or temp_mask[0]:
        starts = insert(starts, 0, 0)
    if move_mask[-1] or temp_mask[-1]:
        stops = append(stops, move_mask.size)

    return starts, stops


def compute_z_angle(acc):
    """
    Computes the z-angle of a tri-axial accelerometer signal with columns X, Y, Z per sample.

    Parameters
    ----------
    acc : array

    Returns
    -------
    z : array
    """
    z = arctan(acc[:, 2] / sqrt(acc[:, 0] ** 2 + acc[:, 1] ** 2)) * (180.0 / pi)
    return z


def compute_absolute_difference(arr):
    """
    Computes the absolute difference between an array and itself shifted by 1 sample along the first axis.

    Parameters
    ----------
    arr : array

    Returns
    -------
    absd: array
    """
    shifted = roll(arr, 1)
    shifted[0] = shifted[1]
    absd = abs(arr - shifted)
    return absd


def drop_min_blocks(arr, min_block_size, drop_value, replace_value, skip_bounds=True):
    """
    Drops (rescores) blocks of a desired value with length less than some minimum length.
    (Ex. drop all blocks of value 1 with length < 5 and replace with new value 0).

    Parameters
    ----------
    arr : array
    min_block_size : integer
        Minimum acceptable block length in samples.
    drop_value : integer
        Value of blocks to examine.
    replace_value : integer
        Value to replace dropped blocks to.
    skip_bounds : boolean
        If True, ignores the first and last blocks.

    Returns
    -------
    arr : array
    """
    lengths, starts, vals = rle(arr)
    ctr = 0
    n = len(lengths)
    for length, start, val in zip(lengths, starts, vals):
        ctr += 1
        if skip_bounds and (ctr == 1 or ctr == n):
            continue
        if val == drop_value and length < min_block_size:
            arr[start: start + length] = replace_value
    return arr


def arg_longest_bout(arr, block_val):
    """
    Finds the first and last indices of the longest block of a given value present in a 1D array.

    Parameters
    ----------
    arr : array
        One-dimensional array.
    block_val : integer
        Value of the desired blocks.

    Returns
    -------
    longest_bout : tuple
        First, last indices of the longest block.
    """
    lengths, starts, vals = rle(arr)
    vals = vals.flatten()
    val_mask = vals == block_val
    if len(lengths[val_mask]):
        max_index = argmax(lengths[val_mask])
        max_start = starts[val_mask][max_index]
        longest_bout = max_start, max_start + lengths[val_mask][max_index]
    else:
        longest_bout = None, None
    return longest_bout


def gini(x, w=None, corr=True):
    """
    Compute the GINI Index.

    Parameters
    ----------
    x : numpy.ndarray
        Array of bout lengths
    w : {None, numpy.ndarray}, optional
        Weights for x. Must be the same size. If None, weights are not used.
    corr : bool, optional
        Apply finite sample correction. Default is True.

    Returns
    -------
    g : float
        Gini index

    References
    ----------
    .. [1] https://stackoverflow.com/questions/48999542/more-efficient-weighted-gini-coefficient-in
        -python/48999797#48999797
    """
    if x.size == 0:
        return 0.
    elif x.size == 1:
        return 1.

    # The rest of the code requires numpy arrays.
    if w is not None:
        sorted_indices = argsort(x)
        sorted_x = x[sorted_indices]
        sorted_w = w[sorted_indices]
        # Force float dtype to avoid overflows
        cumw = cumsum(sorted_w, dtype=float_)
        cumxw = cumsum(sorted_x * sorted_w, dtype=float_)
        g = (sum(cumxw[1:] * cumw[:-1] - cumxw[:-1] * cumw[1:]) / (cumxw[-1] * cumw[-1]))
        if corr:
            return g * x.size / (x.size - 1)
        else:
            return g
    else:
        sorted_x = sort(x)
        n = x.size
        cumx = cumsum(sorted_x, dtype=float_)
        # The above formula, with all weights equal to 1 simplifies to:
        g = (n + 1 - 2 * sum(cumx) / cumx[-1]) / n
        if corr:
            return minimum(g * n / (n - 1), 1)
        else:
            return g
