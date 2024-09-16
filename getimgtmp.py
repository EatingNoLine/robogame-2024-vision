from main import *

for i in range(20):
    print("yubei "+str(i))
    time.sleep(3)
    img = get_img("24",False)
    cv2.imwrite("./tmp"+str(i)+".jpg", img)