import serial

class Serial:
    def __init__(self, port="/dev/my_serial0", baudrate=115200, timeout=10):
        self.s = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
        if not self.s.isOpen():
            raise SomeException("Serial open error")
    def readline(self):
        line = self.s.readline()
        return(line.decode('utf-8'))
    def writeline(self, str):
        if not str.endswith('\n'):
            str = str + '\n'
        self.s.write(str.encode())
        print("Wrote to Serial: " + str)

if __name__ == "__main__":
    s = Serial()
    s.readline()
    s.writeline("6l1111")
    s.readline()
