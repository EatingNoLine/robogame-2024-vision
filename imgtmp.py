import time
import cv2

t0 = time.time()
cap1 = cv2.VideoCapture("/dev/video20")
cap2 = cv2.VideoCapture("/dev/video11")
cap3 = cv2.VideoCapture("/dev/video22")
t00 = time.time()
print(t00-t0)
if not cap1.isOpened():
    print("无法打开摄像头1")
if not cap1.isOpened():
    print("无法打开摄像头2")


while True:
    ret1, frame1 = cap1.read()
    if not ret1:
        print("ret1 empty")
    ret2, frame2 = cap2.read()
    if not ret2:
        print("ret2 empty")
    ret3, frame3 = cap3.read()
    if not ret3:
        print("ret3 empty")
    cv2.imshow("1", frame1)
    cv2.imshow("2", frame2)
    cv2.imshow("3", frame3)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break
cap1.release()
cap2.release()
cap3.release()


# cap0 = cv2.VideoCapture("/dev/video11")
# if not cap0.isOpened():
#     print("无法打开摄像头0")
# while True:
#     ret0, frame0 = cap0.read()
#     if not ret0:
#         print("ret0 empty")
#     cv2.imshow("0", frame0)
#     if cv2.waitKey(1) & 0xFF == ord("q"):
#         break
# cap0.release()