from USBcommunicate import Serial
from pynput import keyboard

RETURNED_MESSAGE = "OK\n"

class Controller:
    def __init__(self, serial):
        self.serial = serial

    def hello(self):
        self.serial.writeline("hello")

    def stay(self):
        self.serial.writeline("000000")
        while True:
            if self.serial.readline() == RETURNED_MESSAGE:
                print("Successfully issued the command " + "stay" + " and received the returned information")
                break

    def grab(self, arm_dir):
        if not isinstance(arm_dir, str):
            arm_dir = str(arm_dir)
        self.serial.writeline("6" + arm_dir + "0000")
        while True:
            if self.serial.readline() == RETURNED_MESSAGE:
                print("Successfully issued the command " + "grab" + " and received the returned information")
                break

    def move(self, distance, direction, gear=0): #gear:挡位 distance(mm)
        match distance:
            case d if 0 < d <= 150:
                gear = 1
            case d if 150 < d <= 60:
                gear = 2
            case d if 600 < d <= 1800:
                gear = 3
            case d if 1800 < d <= 2500:
                gear = 4
            case d if 2500 < d <= 4000:
                gear = 5
            case _:
                raise Exception("Wrong distance for moving")
        line = str(gear) + direction + str(distance).zfill(4)
        self.serial.writeline(line)
        while True:
            if self.serial.readline() == RETURNED_MESSAGE:
                print("Successfully issued the command " + "move " + line + " and received the returned information")
                break

    def rotate(self):
        raise Exception("未完成的代码")

    def shoot(self):
        self.serial.writeline("8" + "00000")
        while True:
            if self.serial.readline() == RETURNED_MESSAGE:
                print("Successfully issued the command " + "shoot" + " and received the returned information")
                break

    def readline(self):
        return self.serial.readline()

# def ctl_on_press(ctl):
#     def on_press(key):
#         try:
#             print('alphanumeric key {0} pressed'.format(
#                 key.char))
#             match key.char:
#                 case "w":
#                     ctl.move(100, "f")
#                 case "a":
#                     ctl.move(100, "l")
#                 case "s":
#                     ctl.move(100, "b")
#                 case "d":
#                     ctl.move(100, "r")
#                 case "j":
#                     ctl.grab("l")
#                 case "k":
#                     ctl.grab("r")
#                 case _:
#                     ctl.stay()
#         except AttributeError:
#             print('special key {0} pressed'.format(
#                 key))
#     return on_press
# 
# def on_release(key):
#     print('{0} released'.format(
#         key))
#     if key == keyboard.Key.esc:
#         # Stop listener
#         return False

def ctl_on_press(ctl):
    def on_press(key):
        try:
            print('alphanumeric key {0} pressed'.format(
                key.char))
            match key.char:
                case "w":
                    ctl.move(1000, "f")
                case "a":
                    ctl.move(1000, "l")
                case "s":
                    ctl.move(1000, "b")
                case "d":
                    ctl.move(1000, "r")
                case "j":
                    ctl.grab("l")
                case "k":
                    ctl.grab("r")
                case "c":
                    ctl.shoot()
                case _:
                    ctl.stay()
        except AttributeError:
            print('special key {0} pressed'.format(
                key))
        ctl.readline()
    return on_press

def ctl_on_release(ctl):
    def on_release(key):
        try:
            print('alphanumeric key {0} released'.format(
                key.char))
            # match key.char:
            #     case _:
            #         ctl.stay()
        except AttributeError:
            print('special key {0} released'.format(
                key))
    return on_release

if __name__ == "__main__":
    serial = Serial()
    controller = Controller(serial)
    print("open serial")
    with keyboard.Listener(
        on_press=ctl_on_press(controller),
        on_release=ctl_on_release(controller)) as listener:
        listener.join()


