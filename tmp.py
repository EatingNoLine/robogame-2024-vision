import time

import cv2
import recognition
import realworld_L
import realworld_R
import threading

from USBcommunicate import *
from controller import *
from detect import *
from atdetect import *

VIDEO_LEFT = "20"
VIDEO_LEFT_BGR2RGB = False
VIDEO_RIGHT = "22"
VIDEO_RIGHT_BGR2RGB = False
# VIDEO_FRONT = "11"
# VIDEO_FRONT_BGR2RGB = True

D_HEIGHT = 1080
D_WIDTH = 1920

MOVE_DELAY = 1

FETCH_DEVIATION_TOLERANCE = 30

count = 0

class Camera():
    def __init__(self, video, bgr2rgb, d_width=D_WIDTH, d_height=D_HEIGHT):
        self.video = video
        self.cap = cv2.VideoCapture("/dev/video" + video)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, d_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, d_height)
        self.bgr2rgb = bgr2rgb
        if not self.cap.isOpened():
            raise Exception("无法打开摄像头"+video)
    def get_img(self):
        ret, frame = self.cap.read()
        if ret:
            if self.bgr2rgb:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            filename = "./images/input/" + self.video + ".jpg"
            cv2.imwrite(filename, frame)
            print(f"保存图像: {filename}")  # time_waste around 3ms
        else:
            print("无法读取视频流")
            return None
        return frame
    def release(self):
        self.cap.release()


def yolo_process(video, bgr2rgb):
    print("-----------video"+video+"-yolo--------------")
    boxes_list, img_size, time, origin_img = capture(video, bgr2rgb=bgr2rgb)
    box_center = analyze(boxes_list)
    result, transformed_point = perspective_trans(origin_img, box_center)
    print("进行到未完成的yolo代码")

def april_tag_detect():

    print("Starting april_tag_detect")

    detector = AtDetect()
    img = condition.img_f
    t_id, at_num, distance2cam, crooked, theta = detector.detect(img)
    condition.update_distance(distance2cam)
    condition.update_crooked(crooked)
    condition.update_tagid(t_id)

    while True:
        img = condition.img_f
        t_id, at_num, distance2cam, crooked, theta = detector.detect(img)
        condition.update_distance(distance2cam)
        condition.update_crooked(crooked)
        condition.update_tagid(t_id)


def grab_and_shoot(id):
    if id == 1:
        ctl.grab("l")
    else:
        ctl.grab("r")

    if condition.distance2wall > 0:
        ctl.shoot()
    else:
        ctl.move(400, "b")

    return True

def main_detect():
    # 左右摄像头识别方块
    # 识别到方块：返回方块顶部中心点坐标
    # 未识别到方块：返回False

    print("Starting main_detect")

    img_L = condition.img_l
    if img_L is None:
        warnings.warn("img_L empty", Warning)
    found_L = False
    n_cube_L = False
    have_cube_L, approxes_L = recognition.recognition(img_L) # have_cube 判定视野中是否有橙色部分

    img_R = condition.img_r
    cv2.imwrite("./imtryr.jpg", img_R)
    if img_R is None:
        warnings.warn("img_R empty", Warning)
    found_R = False
    n_cube_R = False
    have_cube_R, approxes_R = recognition.recognition(img_R) # have_cube 判定视野中是否有橙色部分

    distance2 = []

    if have_cube_L:
        print("左侧看到方块")
        found_L, xy_L, n_cube_L = realworld_L.center(approxes_L) # found 判定能否找到顶面中心点   n_cube 视野中是否有方块重合
        if found_L:
            distance2_L = xy_L[0]**2 + xy_L[1]**2
            if distance2_L <= FETCH_DEVIATION_TOLERANCE**2:
                print("左侧方块坐标：" + str(xy_L[0]) + str(xy_L[1]) + "可以抓取！")
                return (0, 0, 1)
            distance2.append((distance2_L, "L"))
        else:
            print("L摄像头只有特殊情况方块")
            # option：use n_cube
    else:
        print("左侧没有看到方块")

    if have_cube_R:
        print("右侧看到方块")
        found_R, xy_R, n_cube_R = realworld_R.center(approxes_R) # found 判定能否找到顶面中心点   n_cube 视野中是否有方块重合
        if found_R:
            distance2_R = xy_R[0]**2 + xy_R[1]**2
            if distance2_R <= FETCH_DEVIATION_TOLERANCE**2:
                print("右侧方块坐标：" + str(xy_L[0]) + str(xy_L[1]) + "可以抓取！")
                return (0, 0, 2)
            distance2.append((distance2_R, "R"))
        else:
            print("R摄像头只有特殊情况方块")
            # option：use n_cube
    else:
        print("右侧没有看到方块")

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
            return False
        elif have_cube_R:
            clear_output() # time_waste less than 1ms
            # yolo_process(VIDEO_RIGHT, VIDEO_RIGHT_BGR2RGB)
            return False
        else:
            print("左右视野均无方块")
            return False
    print("当前方块坐标：")
    print(xy)
    return xy

class Condition():
    # 保存车的状态
    # distance2wall 前置摄像头距离墙壁的距离
    # crooked 车身是否不正
    # tag_id 当前车头所朝向的Apriltag的id (从左到右依次为 0，1，2，3，4，5)
    def __init__(self):
        self.distance2wall = 1500
        self.crooked = False
        self.tag_id = 5

        self.img_l = None
        self.img_r = None
    def update_distance(self, new_d):
        self.distance2wall = new_d
    def update_crooked(self, new_c):
        self.crooked = new_c
    def update_tagid(self, new_tagid):
        self.tag_id = new_tagid


class MainThread(threading.Thread):

    def __init__(self, threadID, name='MainThread'):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name

    def run(self):

        time.sleep(12)
        print("Starting " + self.name)

        # Check controller
        ctl.hello()
        time.sleep(0.1)
        print(s.readline())

        while True:
            if condition.crooked:
                warnings.warn("车头不正，需要调整", Warning)

            xy = main_detect()

            if not xy:  # 视野中没有方块
                global count
                if count == 0:
                    ctl.move(200, "b")
                    count = 1
                else:
                    ctl.move(200, "f")
                    count = 0
                continue
            elif xy == (0, 0, 1): # 距离足够近可以抓取
                grab_and_shoot(1)
            elif xy == (0, 0, 2):
                grab_and_shoot(2)
            else:
                if abs(xy[1]) <= 15:
                    ctl.stay()
                elif xy[1] < 0:  # 往后走
                    ctl.move(int(abs(xy[1])), "b")
                else:  # 往前走
                    ctl.move(int(abs(xy[1])), "f")
                if abs(xy[0]) <= 15:
                    ctl.stay()
                elif xy[0] < 0:  # 往左走
                    ctl.move(int(abs(xy[0])), "l")
                else:  # 往右走
                    ctl.move(int(abs(xy[0])), "r")
        print("Exiting " + self.name)

class CapThread(threading.Thread):

    def __init__(self, threadID, name='CapThread'):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name

    def run(self):
        print("Starting " + self.name)
        while True:
            condition.img_l = cap_l.get_img()
            condition.img_r = cap_r.get_img()
        print("Exiting " + self.name)


if __name__ == "__main__":
    print("Starting initialize")
    t_0 = time.time()

    # Create a globally accessible controller
    s = Serial()
    ctl = Controller(s)

    # Open cameras
    cap_l = Camera(VIDEO_LEFT, VIDEO_LEFT_BGR2RGB, D_WIDTH, D_HEIGHT)
    cap_r = Camera(VIDEO_RIGHT, VIDEO_RIGHT_BGR2RGB, D_WIDTH, D_HEIGHT)

    # Create the condition instance
    condition = Condition()

    t_1 = time.time()
    print("初始化所用时间：" + str(t_1-t_0))

    cap_thread = CapThread(2)
    cap_thread.start()
    main_thread = MainThread(1)
    main_thread.start()

