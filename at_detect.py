import cv2
import apriltag
import numpy as np
import math
import time

CAMERA_HEIGHT = 50
TOLERABLE_DEGREE = 8
TAG_LENGTH = 400
TAG_SPACING = 240
DOWN_SIDE_HEIGHT = 100
SIDE_HEIGHT = 200
FOCAL_LENGTH = 2.163

def calculate_distance(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    return distance

class At_detect:
    def __init__(self):
        self.detector = apriltag.Detector(apriltag.DetectorOptions(families='tag36h11'))

    def detect(self, img, rotated_grayed=False):

        if rotated_grayed:
            img_height, img_width = img.shape[:2]
            tags = self.detector.detect(img)
            corners = []
            midpoint_to_mid = []
            tag_mp_x = [0,0,0,0,0,0]
            tag_cp = [[],[],[],[],[],[]]
            at_num = 0
            if tags:
                for tag in tags:
                    at_num = at_num + 1
                    # print("tag_id: " + str(tag.tag_id))
                    # print(tag.corners)
                    tag_cp[tag.tag_id].append(tag.corners.tolist())
                    midpoint = np.mean(tag.corners, axis=0)
                    # print(midpoint)
                    tag_mp_x[tag.tag_id] = midpoint[0]
                    midpoint_to_mid.append((abs(midpoint[0]/img_width-1/2), tag.tag_id))
                    mp_array = midpoint.reshape(1,2)
                    corners.extend(tag.corners)
                    corners.extend(mp_array)
            else:
                return 0, 0, False, 0
            min_dis_to_mid, min_id = min(midpoint_to_mid)
            centerpoint_x = tag_mp_x[min_id]

            if centerpoint_x > img_width/2:
                loca_right = True
                p1 = 2
                p2 = 3
                p3 = 1
                p4 = 0
            else:
                loca_right = False
                p1 = 3
                p2 = 2
                p3 = 0
                p4 = 1

            # 测距
            diagonal_width = np.linalg.norm(np.array(tag_cp[min_id][0][p1]) - np.array(tag_cp[min_id][0][p4]))
            distance2center = (TAG_LENGTH * FOCAL_LENGTH) / diagonal_width
            distance2cam = math.sqrt(distance2center ** 2 - min_dis_to_mid ** 2)

            # 判断是否正向墙壁
            side_len = tag_cp[min_id][0][p3][1] - tag_cp[min_id][0][p1][1]
            print("side_len:"+str(side_len))
            upper_len = calculate_distance(tag_cp[min_id][0][p1], tag_cp[min_id][0][p2])
            print("upper_len:"+str(upper_len))
            if upper_len >= side_len:
                upper_len = side_len
            theta = math.degrees(math.acos(upper_len/side_len))
            if not loca_right:
                theta = -1*theta
            if abs(theta) > TOLERABLE_DEGREE:
                crooked = True
            else:
                crooked = False

            points = np.array(corners)
            for point in points:
                cv2.circle(img, (int(point[0]), int(point[1])), 10, (0, 0,  255), -1)  # 红色点，半径为10
            cv2.circle(img, (int(centerpoint_x), int(img_height/2)), 10, (0,255,0), -1)
            cv2.circle(img, (int(img_width/2),int(img_height/2)), 10, (255, 0,0), -1)

            cv2.imwrite("./images/atag/result.jpg", img)
            print("保存Apriltag识别结果到 ./images/atag/result.jpg")

            return min_id, at_num, distance2cam, crooked, theta

        else:
            img_height, img_width = img.shape[:2]
            gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            tags = self.detector.detect(gray_img)
            sum_tan = 0
            count = 0

            if tags:
                for tag in tags:
                    count = count + 1
                    sum_tan = sum_tan + (tag.corners[1][1]+tag.corners[2][1]-tag.corners[0][1]-tag.corners[3][1])/(tag.corners[0][0]+tag.corners[3][0]-tag.corners[1][0]-tag.corners[2][0])
            else:
                return -1, 0, 0, False, 0

            tan = sum_tan / count
            theta = math.degrees(math.atan(tan))
            M = cv2.getRotationMatrix2D((img_width/2, img_height/2), -theta, 1)
            rotated_img = cv2.warpAffine(gray_img, M, (img_width, img_height))
            cv2.imwrite("./images/atag/rotated_img.jpg", rotated_img)
            return self.detect(rotated_img, rotated_grayed=True)

if __name__ == "__main__":
    t1 = time.time()
    detect = At_detect()
    img = cv2.imread("./images/atag/newat7.jpg")
    t_id, at_num, distance2cam, crooked, theta = detect.detect(img)
    print("t_id:"+str(t_id))
    print("at_num:"+str(at_num))
    print("distance2cam:"+str(distance2cam))
    print("crooked:"+str(crooked))
    print("theta:"+str(theta))
    t2 = time.time()
    print("total time:"+str(t2-t1))