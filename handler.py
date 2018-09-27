import numpy as np

def getData(fileName, separator=';', data_type='float'):
    data = []
    try:
        with open(fileName, 'r') as f:
            read_data = f.readlines()
        [data.append( line.strip().split(separator) ) for line in read_data]
        data = np.array(data, dtype=data_type)
    except:
        data = np.array([], dtype=data_type)
    return data

def idFrequency(data_array, timer_index=0, units='s'):
    timestamps = data_array[:,timer_index]
    diffs = np.diff(timestamps)
    mean = np.mean(diffs)
    if units=='ms':
        mean /= 1000.0
    return 1.0 / mean

def mergeData(data_array_1, data_array_2):
    len_data_1 = len(data_array_1)
    len_data_2 = len(data_array_2)
    if len_data_1>len_data_2:
        ratio = round(len_data_1/len_data_2)
        new_array = np.repeat(data_array_2, ratio, axis=0)
        len_new_array = len(new_array)
        if len_new_array<len_data_1:
            last_row = np.array([new_array[-1]])
            difference = len_data_1 - len_new_array
            missing_rows = np.repeat(last_row, difference, axis=0)
            new_array = np.concatenate((new_array, missing_rows), axis=0)
        elif len_data_1<len_new_array:
            difference = len_new_array - len_data_1
            new_array = new_array[:len_data_1]
        bigger_array = np.concatenate((data_array_1, new_array), axis=1)
        return bigger_array

imu_labels = ["timestamp_imu", "ax", "ay", "az", "gx", "gy", "gz"]
truth_labels = ["timestamp_gt", "px", "py", "pz", "qx", "qy", "qz", "qw"]

imu_data = getData('./data/imu_shapes_t.txt', separator=' ')
truth_data = getData('./data/groundtruth_shapes_t.txt', separator=' ')

print("IMU Frequency:", idFrequency(imu_data), "Hz")
print("Truth Frequency:", idFrequency(truth_data), "Hz")

merged_data = mergeData(imu_data, truth_data)

new_filename = "./data/ETH-Shapes-t.csv"
new_header = imu_labels + truth_labels
np.savetxt(new_filename, merged_data, fmt='%f', delimiter=';', header=';'.join(new_header), comments='')