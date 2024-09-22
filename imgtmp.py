import time
import cv2
import threading

t0 = time.time()
cap1 = cv2.VideoCapture("/dev/video20")
cap2 = cv2.VideoCapture("/dev/video22")
t00 = time.time()
print(t00-t0)
if not cap1.isOpened():
    print("无法打开摄像头1")
if not cap1.isOpened():
    print("无法打开摄像头2")

th1 =

while True:
    t1 = time.time()
    # ret1, frame1 = cap1.read()
    # if not ret1:
    #     print("ret1 empty")
    t2 = time.time()
    ret2, frame2 = cap2.read()
    if not ret2:
        print("ret2 empty")
    # cv2.imshow("1", frame1)
    cv2.imshow("2", frame2)
    print("t2-t1: "+str(t2-t1))
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break
cap1.release()
cap2.release()
