import time

import cv2
import recognition
import realworld_L
import realworld_R
import threading
import queue

from USBcommunicate import *
from controller import *
from detect import *
from at_detect import *

VIDEO_LEFT = "20"
VIDEO_LEFT_BGR2RGB = False
VIDEO_RIGHT = "22"
VIDEO_RIGHT_BGR2RGB = False
VIDEO_FRONT = "11"
VIDEO_FRONT_BGR2RGB = True

D_HEIGHT = 1080
D_WIDTH = 1920

MOVE_DELAY = 1

count = 0

def get_img(video, bgr2rgb, d_width=D_WIDTH, d_height=D_HEIGHT):
    print("get_img start video"+video)
    cap = cv2.VideoCapture("/dev/video" + video)
    # cap.set(cv2.CAP_PROP_FRAME_WIDTH, d_width)
    # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, d_height)
    if not cap.isOpened():
        raise Exception("无法打开摄像头")
    t_r1 = time.time()
    ret, frame_tmp = cap.read()
    frame = frame_tmp

    print(frame.shape)
    print("read time:")

    t_r2 = time.time()
    print(t_r2-t_r1)

    if bgr2rgb:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        filename = "./images/input/" + video + ".jpg"
        cv2.imwrite(filename, frame)
    '''
    if ret:
        if bgr2rgb:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        filename = "./images/input/" + video + ".jpg"
        cv2.imwrite(filename, frame)
        print(f"保存图像: {filename}") # time_waste around 3ms
    else:
        raise Exception("无法读取视频流")
    '''
    cap.release()
    return frame

def yolo_process(video, bgr2rgb):
    print("-----------video"+video+"-yolo--------------")
    boxes_list, img_size, time, origin_img = capture(video, bgr2rgb=bgr2rgb)
    box_center = analyze(boxes_list)
    result, transformed_point = perspective_trans(origin_img, box_center)
    print("进行到未完成的yolo代码")

def april_tag_detect(video, bgr2rgb, q_distance2wall, q_crooked, q_tag_id):

    print("april_tag_detect start")

    detector = At_detect()
    img = get_img(video, bgr2rgb)
    t_id, at_num, distance2cam, crooked, theta = detector.detect(img)
    q_distance2wall.put(distance2cam)
    q_crooked.put((crooked, theta))
    q_tag_id.put(t_id)

    while True:
        img = get_img(video, bgr2rgb)
        t_id, at_num, distance2cam, crooked, theta = detector.detect(img)
        q_distance2wall.get()
        q_crooked.get() 
        q_tag_id.get()

        q_distance2wall.put(distance2cam)
        q_crooked.put((crooked, theta))
        q_tag_id.put(t_id)

def grab_and_shoot(distance=1000):
    ctl.stay()
    ctl.grab("r")
    while True:
        if s.readline() == "OK\n":
            print("---抓取成功---")
            break

    while True:
        if distance > 0:
            ctl.shoot()
            while True:
                if s.readline() == "OK\n":
                    print("---发射成功---")
                    break
            break
        else:
            ctl.move(400, "b")
            while True:
                if s.readline() == "OK\n":
                    print("move backward:"+str(400))
                    break
            break

    return True

def main_detect():

    # 左右摄像头识别方块
    # 识别到方块：返回方块顶部中心点坐标
    # 未识别到方块：返回False

    print("main_detect start")

    t_1 = time.time()

    img_L = get_img(VIDEO_LEFT, VIDEO_LEFT_BGR2RGB)

    t_2 = time.time()
    print("获取图像用时：")
    print(t_2 - t_1)
    t_s1 = time.time()
    if img_L is None:
        print("img_L empty")
    found_L = False
    n_cube_L = False
    have_cube_L, approxes_L = recognition.recognition(img_L) # have_cube 判定视野中是否有橙色部分
    t_s2 = time.time()
    print("shibieyongshi:")
    print(t_s2 - t_s1)

    img_R = get_img(VIDEO_RIGHT, VIDEO_RIGHT_BGR2RGB)
    cv2.imwrite("./imtryr.jpg", img_R)
    if img_R is None:
        print("img_R empty")
    found_R = False
    n_cube_R = False
    have_cube_R, approxes_R = recognition.recognition(img_R) # have_cube 判定视野中是否有橙色部分

    distance2 = []

    if have_cube_L:
        print("左侧看到方块")
        found_L, xy_L, n_cube_L = realworld_L.center(approxes_L) # found 判定能否找到顶面中心点   n_cube 视野中是否有方块重合
        if found_L:
            distance2_L = xy_L[0]**2 + xy_L[1]**2
            if distance2_L <= 400:
                grab_and_shoot()
            distance2.append((distance2_L, "L"))
        else:
            print("L摄像头只有特殊情况方块")
            # option：use n_cube
    if have_cube_R:
        print("右侧看到方块")
        found_R, xy_R, n_cube_R = realworld_R.center(approxes_R) # found 判定能否找到顶面中心点   n_cube 视野中是否有方块重合
        if found_R:
            distance2_R = xy_R[0]**2 + xy_R[1]**2
            if distance2_R <= 400:
                grab_and_shoot()
            distance2.append((distance2_R, "R"))
        else:
            print("R摄像头只有特殊情况方块")
            # option：use n_cube

    if distance2:
        closest_pair = min(distance2, key=lambda x: x[0])
        target = closest_pair[1] # str: L or R
        match target:
            case "L":
                xy = xy_L
            case "R":
                xy = xy_R
    else:
        if have_cube_L:
            clear_output() # time_waste less than 1ms
            # yolo_process(VIDEO_LEFT, VIDEO_LEFT_BGR2RGB)
        elif have_cube_R:
            clear_output() # time_waste less than 1ms
            # yolo_process(VIDEO_RIGHT, VIDEO_RIGHT_BGR2RGB)
        else:
            print("左右视野均无方块")
        return False
    print(xy)
    return xy

class mainThread(threading.Thread):

    def __init__(self, threadID, name):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name

    def run(self):
        print("Starting " + self.name)
        print("main_loop start")
        ctl.hello()
        print(s.readline())

        while True:

            # distance2wall = q_distance2wall.get()
            # crooked = q_crooked.get()
            # tag_id = q_tag_id.get()

            # q_distance2wall.put(distance2wall)
            # q_crooked.put(crooked)
            # q_tag_id.put(tag_id)
            # if crooked[0]:
            #     print("WARNING: 车头不正，需要调整")

            xy = main_detect()

            if not xy:  # 视野中没有方块
                # if q_tag_id == -1:
                global count
                if count == 0:
                    ctl.move(500, "b")
                    while True:
                        if s.readline() == "OK\n":
                            print("move backward:" + str(1000))
                            break

                    count = 1
                else:
                    ctl.move(500, "f")
                    while True:
                        if s.readline() == "OK\n":
                            print("move foward:" + str(1000))
                            break
                    count = 0
                continue

            if abs(xy[1]) <= 15:
                ctl.stay()
            elif xy[1] < 0:  # 往后走
                ctl.move(int(abs(xy[1])), "b")
                while True:
                    if s.readline() == "OK\n":
                        print("move backward:" + str(int(abs(xy[1]))))
                        break
                # while abs(xy[1]) > 15:
                #     xy = main_detect()
                # ctl.stay()
                # while True:
                #     if s.readline() == "OK\n":
                #         print("stay")
                #         break
            else:  # 往前走
                ctl.move(int(abs(xy[1])), "f")
                while True:
                    if s.readline() == "OK\n":
                        print("move forward:" + str(int(abs(xy[1]))))
                        break
                # while abs(xy[1]) > 15:
                #     xy = main_detect()
                # ctl.stay()
                # while True:
                #     if s.readline() == "OK\n":
                #         print("stay")
                #         break

            if abs(xy[0]) <= 15:
                ctl.stay()
                while True:
                    if s.readline() == "OK\n":
                        print("stay")
                        break
            elif xy[0] < 0:  # 往左走
                ctl.move(int(abs(xy[0])), "l")
                while True:
                    if s.readline() == "OK\n":
                        print("move left:" + str(int(abs(xy[0]))))
                        break
                # while abs(xy[0]) > 15:
                #     xy = main_detect()
                # ctl.stay()
                # while True:
                #     if s.readline() == "OK\n":
                #         print("stay")
                #         break
            else:  # 往右走
                ctl.move(int(abs(xy[0])), "r")
                while True:
                    if s.readline() == "OK\n":
                        print("move right:" + str(int(abs(xy[0]))))
                        break
                # while abs(xy[0]) > 15:
                #     xy = main_detect()
                # ctl.stay()
                # while True:
                #     if s.readline() == "OK\n":
                #         print("stay")
                #         break
        print("Exiting " + self.name)

if __name__ == "__main__":

    # # Create a globally accessible controller
    # s = Serial()
    # ctl = controller(s)
    #
    # # q_distance2wall = queue.Queue()
    # # q_crooked = queue.Queue()
    # # q_tag_id = queue.Queue()
    # # thread1 = threading.Thread(target=main_loop, args=(q_distance2wall, q_crooked, q_tag_id))
    # # thread2 = threading.Thread(target=april_tag_detect, args=(VIDEO_FRONT, VIDEO_FRONT_BGR2RGB, q_distance2wall, q_crooked, q_tag_id))
    #
    # thread1 = mainThread(1, "Thread-1")
    #
    # thread1.start()
    # # thread2.start()
    #
    # # thread2.join()
    # thread1.join()
    #
    # print("it's all over")

    t_start = time.time()
    xy = main_detect()
    print(xy)
    t_over = time.time()
    print("最终时间：")
    print(t_over-t_start)