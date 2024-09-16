import cv2
import numpy as np

low_orange = np.array([5, 100, 0])
up_orange = np.array([20, 255, 255])

def recognition(img):

    have_cube = False
    contours = None
    filtered_contours = []
    approxes = []

    hsv_img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv_img, low_orange, up_orange)

    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))

    contours, _ = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)


    if contours == None:
        return have_cube, approxes

    else:
        for contour in contours:
            if 10000 < cv2.contourArea(contour) < 350000:
                filtered_contours.append(contour)

        if len(filtered_contours) == 0:
            return have_cube, approxes

        # 视野内存在方块/近似轮廓为多边形

        else:
            have_cube = True

            for contour in filtered_contours:

                epsilon = 0.008 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)

                approxes.append(approx)

                # 绘制多边形
                cv2.drawContours(img, [approx], -1, (0, 255, 0), 2)

                # 绘制角点
                for point in approx:
                    cv2.circle(img, tuple(point[0]), 5, (0, 0, 255), -1)

########################################################################################################################

            # 将拐点根据y值递增排序

            for approx in approxes:

                temp = np.zeros((1, 2))

                for i in range(len(approx)):
                    for j in range(len(approx) - i - 1):
                        if approx[j, 0, 1] > approx[(j + 1), 0, 1]:
                            temp[0, 0] = approx[j, 0, 0]
                            temp[0, 1] = approx[j, 0, 1]
                            approx[j] = approx[j + 1]
                            approx[j + 1] = temp

                # cv2.imshow("img", img)
                # cv2.waitKey(0)
                # approx ： (i, 1, 3)数组

            return have_cube, approxes