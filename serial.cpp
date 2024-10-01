#include <iostream>
#include <libserial/SerialPort.h>
#include <libserial/SerialStream.h>
#include <thread>
#include <chrono>

#include <stdio.h>
#include <stdint.h>
#include <string.h>


typedef struct {
    int16_t distance;    // 2B
    uint16_t noise;      // 2B
    uint32_t peak;       // 4B
    uint8_t confidence;   // 1B
    uint32_t intg;       // 4B
    int16_t reftof;      // 2B
} LidarPointTypedef;

uint8_t calculate_checksum(uint8_t *data, size_t length) {
    uint8_t checksum = 0;
    for (size_t i = 0; i < length; i++) {
        checksum += data[i];
    }
    return checksum;
}

void decode_data(uint8_t *buffer, size_t length) {
    // 解析起始符
    if (memcmp(buffer, "\xAA\xAA\xAA\xAA", 4) != 0) {
        printf("Invalid start symbol\n");
        return;
    }

    // 提取字段
    uint8_t device_address = buffer[4];
    uint8_t command_code = buffer[5];
    uint8_t chunk_offset = buffer[6];
    uint8_t data_length = buffer[7];

    // 校验和
    uint8_t checksum_received = buffer[length - 1];
    uint8_t checksum_calculated = calculate_checksum(buffer + 4, length - 5);

    if (checksum_received != checksum_calculated) {
        printf("Checksum mismatch\n");
//        return;
    }

    // 解析数据域
    LidarPointTypedef points[12];
    memcpy(points, buffer + 8, sizeof(LidarPointTypedef) * 12);

    // 输出解析结果
    for (int i = 0; i < 12; i++) {
        printf("Point %d: Distance = %d, Noise = %u, Peak = %u, Confidence = %u, Intg = %u, Reftof = %d\n",
               i + 1, points[i].distance, points[i].noise, points[i].peak,
               points[i].confidence, points[i].intg, points[i].reftof);
    }
}

int main() {
    // 创建串口对象
    LibSerial::SerialPort serial_port;

    // 打开串口
    try {
        serial_port.Open("/dev/ttyACM0");
    } catch (const std::exception& e) {
        std::cerr << "Failed to open serial port: " << e.what() << std::endl;
        return 1;
    }

    // 设置串口参数
    serial_port.SetBaudRate(LibSerial::BaudRate::BAUD_230400);    // 设置波特率
    serial_port.SetCharacterSize(LibSerial::CharacterSize::CHAR_SIZE_8); // 数据位
    serial_port.SetParity(LibSerial::Parity::PARITY_NONE);   // 奇偶校验
    serial_port.SetStopBits(LibSerial::StopBits::STOP_BITS_1); // 停止位
    serial_port.SetFlowControl(LibSerial::FlowControl::FLOW_CONTROL_NONE); // 流控

    // 接收数据
    std::string received_data;
    for (int i=0; i<=20; i++){
        try {
            std::this_thread::sleep_for(std::chrono::seconds(1)); // 等待设备响应
            serial_port.ReadLine(received_data);
            decode_data(reinterpret_cast<uint8_t*>(const_cast<char*>(received_data.data())), received_data.size());
//            std::cout << "Received: " << received_data << std::endl;
        } catch (const std::exception& e) {
            std::cerr << "Error reading from serial port: " << e.what() << std::endl;
        }
    }


    // 关闭串口
    serial_port.Close();

    return 0;
}