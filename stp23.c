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
        return;
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
    // 接收到的数据

//    uint8_t example_packet[] = {
//        0xAA, 0xAA, 0xAA, 0xAA, // 起始符
//        0x00,                   // 设备地址
//        0x02,                   // 命令码
//        0x00,                   // 偏移地址
//        0x00,                   // 数据长度
//        0xB8,                   // 数据长度 (后续数据)
//        0x00,                   // 校验和
//        // 12个测量点数据...
//    };



    decode_data(data_packet, sizeof(data_packet));

    return 0;
}