import warnings

import serial

class Serial:
    def __init__(self, port="/dev/my_serial0", baudrate=115200, timeout=10):
        self.s = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
        if not self.s.isOpen():
            raise Exception("Serial open error")
    def readline(self):
        line = self.s.readline()
        try:
            return line.decode('utf-8')
        except UnicodeDecodeError:
            warnings.warn("无法解码字节，返回'0'", Warning)
            return '0'
    def writeline(self, str):
        if not str.endswith('\n'):
            str = str + '\n'
        self.s.write(str.encode())
        print("Wrote to Serial: " + str)

if __name__ == "__main__":
    s = Serial(port="/dev/ttyACM0")
    for _ in range(20):
        print(s.readline())
    # s.writeline("1f1111")

