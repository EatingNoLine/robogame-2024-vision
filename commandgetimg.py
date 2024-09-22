from main import *

import subprocess

def capture_image(filename):
    # 调用fswebcam命令
    command = ['fswebcam',
               '-d', '/dev/video22',
               '-r', '640x480',
               '--no-banner',
               '--jpeg',
               '5', filename]
    try:
        subprocess.run(command, check=True)
        print(f"Image captured and saved as {filename}")
    except subprocess.CalledProcessError as e:
        print(f"Error capturing image: {e}")

if __name__ == "__main__":
    t1 = time.time()
    capture_image("captured_image.jpg")
    t2 = time.time()
    print("time:" + str(t2-t1))