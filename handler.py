import numpy as np

def getData(fileName, separator=';', data_type='float', returnHeader=False):
    data, header_list = [], []
    try:
        with open(fileName, 'r') as f:
            read_lines = f.readlines()
        num_header_rows = countHeaders(read_lines, separator=separator)
        if returnHeader:
            header_list = read_lines[0].replace('#', '').split(separator)
            header_list = [item.strip() for item in header_list]
        [data.append( line.strip().split(separator) ) for line in read_lines[num_header_rows:]]
    except:
        print("[ERROR] Could not read and store the data.")
    data = np.array(data, dtype=data_type)
    if returnHeader:
        return data, header_list
    else:
        return data

def countHeaders(data_lines=[], separator=';'):
    row_count = 0
    for line in data_lines:
        elements_array = []
        for element in line.strip().split(separator):
            elements_array.append(isfloat(element))
        if not all(elements_array):
            row_count += 1
        else:
            break
    return row_count

def isfloat(value):
    try:
        float(value)
        return True
    except ValueError:
        return False

def idFrequency(data_array, timer_index=0, units='s'):
    timestamps = data_array[:,timer_index]
    diffs = np.diff(timestamps)
    mean = np.mean(diffs)
    if units=='ms':
        mean *= 1e-3
    if units=='us':
        mean *= 1e-6
    if units=='ns':
        mean *= 1e-9
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

def compareHeaders(header_1, header_2):
    diffs = 0
    for item in header_1:
        if item in header_2:
            diffs +=1
    print("Diffs:", diffs)

imu_labels = ["timestamp_imu [ns]", "w_RS_S_x [rad s^-1]", "w_RS_S_y [rad s^-1]", "w_RS_S_z [rad s^-1]",
                                "a_RS_S_x [m s^-2]", "a_RS_S_y [m s^-2]", "a_RS_S_z [m s^-2]"]
truth_labels = ["timestamp_truth [ns]", "p_RS_R_x [m]", "p_RS_R_y [m]", "p_RS_R_z [m]",
                "q_RS_w []", "q_RS_x []", "q_RS_y []", "q_RS_z []"]
imu_data, imu_header = getData('./data/VI-TUM_calib_imu4_IMU.csv', separator=',', returnHeader=True)
truth_data, truth_header = getData('./data/VI-TUM_calib_imu4_Truth.csv', separator=',', returnHeader=True)
print("IMU Frequency:", idFrequency(imu_data, units='ns'), "Hz")
print("Truth Frequency:", idFrequency(truth_data, units='ns'), "Hz")
new_filename = "./data/VI-TUM_calib_imu4.csv"

compareHeaders(imu_labels, imu_header)

# imu_labels = ["timestamp_imu", "ax", "ay", "az", "gx", "gy", "gz"]
# truth_labels = ["timestamp_gt", "px", "py", "pz", "qx", "qy", "qz", "qw"]
# imu_data = getData('./data/imu_boxes_t.txt', separator=' ')
# truth_data = getData('./data/groundtruth_boxes_t.txt', separator=' ')
# print("IMU Frequency:", idFrequency(imu_data), "Hz")
# print("Truth Frequency:", idFrequency(truth_data), "Hz")
# new_filename = "./data/ETH-Boxes-t.csv"

# merged_data = mergeData(imu_data, truth_data)
# new_header = imu_labels + truth_labels
# np.savetxt(new_filename, merged_data, fmt='%f', delimiter=';', header=';'.join(new_header), comments='')