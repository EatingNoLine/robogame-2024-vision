import numpy as np
import math
from itertools import combinations

savedir = "./cam_data_L/"
inv_newcam_mtx = np.load(savedir + "inv_newcam_mtx.npy")
inv_R_mtx = np.load(savedir + "inv_R_mtx.npy")
s_arr = np.load(savedir + "s_arr.npy")
tvec1 = np.load(savedir + "tvec1.npy")
H_mtx = np.load(savedir + "H_mtx.npy")

def calculate(u, v):

    uv_1 = np.array([u, v, 1], dtype = np.float32)
    uv_1 = uv_1.T
    suv_1 = s_arr[0] * uv_1
    xyz_c = inv_newcam_mtx.dot(suv_1)

    xyz_cT = np.zeros((3, 1))
    xyz_cT[0, 0] = xyz_c[0]
    xyz_cT[1, 0] = xyz_c[1]
    xyz_cT[2, 0] = xyz_c[2]

    xyz_c = xyz_cT - tvec1

    xyz = inv_R_mtx.dot(xyz_c)

    xy1 = np.array([xyz[0, 0], xyz[1, 0], 1])
    xy1 = xy1.T
    hxy = H_mtx.dot(xy1)
    hx = hxy[0]/hxy[2]
    hy = hxy[1]/hxy[2]

    return (hx, hy)


def distance(p1, p2):
    d = math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)
    return d


def center(approxes):

    found = False
    center_points = []
    min_d_center_point = None
    n_cube = False

    # 取5个点

    for approx in approxes:

        if approx.shape[0] > 8:
            n_cube = True

        if 9 > approx.shape[0] > 4:
            points = np.zeros((5, 2))
            for i in range(5):
                points[i, 0] = calculate(approx[i, 0, 0], approx[i, 0, 1])[0]
                points[i, 1] = calculate(approx[i, 0, 0], approx[i, 0, 1])[1]

            num1 = [0, 1, 2, 3, 4]
            combos1 = combinations(num1, 3)

            # 5个点中取任意3个/遍历

            for combo1 in combos1:

                d = [(0,0), (0, 0), (0, 0)]

                d[0] = (distance(points[combo1[0]], points[combo1[1]]), 0)
                d[1] = (distance(points[combo1[0]], points[combo1[2]]), 1)
                d[2] = (distance(points[combo1[1]], points[combo1[2]]), 2)

                for i in range(3):
                    for j in range(3 - i - 1):
                        if d[j] < d[j + 1]:
                            temp = d[j]
                            d[j] = d[j + 1]
                            d[j + 1] = temp


                if (d[0][0] - 142.93) ** 2 < 600 and (d[1][0] - 101.08) ** 2 < 600 and (d[2][0] - 101.08) ** 2 < 600:


                    found = True

                    if d[0][1] == 0:
                        center_point = ((points[combo1[0], 0] + points[combo1[1], 0])/2, (points[combo1[0], 1] + points[combo1[1], 1])/2)
                    elif d[0][1] == 1:
                        center_point = ((points[combo1[0], 0] + points[combo1[2], 0])/2, (points[combo1[0], 1] + points[combo1[2], 1])/2)
                    elif d[0][1] == 2:
                        center_point = ((points[combo1[1], 0] + points[combo1[2], 0])/2, (points[combo1[1], 1] + points[combo1[2], 1])/2)

                    center_points.append(center_point)

                    break
        if approx.shape[0] < 5:
            found = True
            center_points.append((approx[0][0][0], approx[0][0][1]))

    if found:
        min_d_center_point = center_points[0]

        for c_point in center_points:
            if distance(c_point, (0, 0)) < distance(min_d_center_point, (0, 0)):
                min_d_center_point = c_point

        return found, min_d_center_point, n_cube

    else:
        return found, min_d_center_point, n_cube

