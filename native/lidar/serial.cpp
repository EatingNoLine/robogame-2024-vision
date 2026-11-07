/*
 * STP-23 lidar over a real serial port - probe program from the 2024 season.
 *
 * Not part of the vision pipeline, not built by CI, and not exercised since the
 * robot was retired. It needs libserial (https://github.com/crayzeewulf/libserial)
 * and a lidar on /dev/ttyACM0 at 230400 baud.
 *
 * Known limitation: the frame is binary, but this probe reads it with
 * SerialPort::ReadLine(), which stops at the first 0x0A byte inside the payload.
 * A production reader must accumulate bytes until the frame length in the header
 * is satisfied. The 2024 code never got that far - the lidar was not used on the
 * final robot.
 *
 * The point struct is packed to the 15-byte wire layout; without the attribute
 * the compiler inserts padding and every field after `confidence` is misread.
 */

#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <string>
#include <thread>

#include <libserial/SerialPort.h>
#include <libserial/SerialStream.h>

#define POINTS_PER_FRAME 12
#define POINT_BYTES 15

typedef struct __attribute__((packed)) {
    int16_t distance;   /* 2 B - distance in millimetres */
    uint16_t noise;     /* 2 B - noise level */
    uint32_t peak;      /* 4 B - peak intensity */
    uint8_t confidence; /* 1 B - confidence level */
    uint32_t intg;      /* 4 B - integration time */
    int16_t reftof;     /* 2 B - reference time of flight */
} LidarPointTypedef;

static_assert(sizeof(LidarPointTypedef) == POINT_BYTES, "point struct must pack to 15 bytes");

uint8_t calculate_checksum(const uint8_t* data, size_t length) {
    uint8_t checksum = 0;
    for (size_t i = 0; i < length; i++) {
        checksum += data[i];
    }
    return checksum;
}

void decode_data(const uint8_t* buffer, size_t length) {
    if (memcmp(buffer, "\xAA\xAA\xAA\xAA", 4) != 0) {
        printf("Invalid start symbol\n");
        return;
    }

    printf("frame: addr=0x%02X cmd=0x%02X chunk=0x%02X payload=%u B\n", buffer[4], buffer[5],
           buffer[6], buffer[7]);

    const uint8_t checksum_received = buffer[length - 1];
    const uint8_t checksum_calculated = calculate_checksum(buffer + 4, length - 5);
    if (checksum_received != checksum_calculated) {
        // The 2024 probe logged the mismatch and kept decoding; this one stops.
        printf("Checksum mismatch\n");
        return;
    }

    LidarPointTypedef points[POINTS_PER_FRAME];
    memcpy(points, buffer + 8, sizeof(LidarPointTypedef) * POINTS_PER_FRAME);

    for (int i = 0; i < POINTS_PER_FRAME; i++) {
        printf("Point %d: Distance = %d, Noise = %u, Peak = %u, Confidence = %u, Intg = %u, Reftof = %d\n",
               i + 1, points[i].distance, points[i].noise, points[i].peak, points[i].confidence,
               points[i].intg, points[i].reftof);
    }
}

int main() {
    LibSerial::SerialPort serial_port;

    try {
        serial_port.Open("/dev/ttyACM0");
    } catch (const std::exception& e) {
        std::cerr << "Failed to open serial port: " << e.what() << std::endl;
        return 1;
    }

    serial_port.SetBaudRate(LibSerial::BaudRate::BAUD_230400);
    serial_port.SetCharacterSize(LibSerial::CharacterSize::CHAR_SIZE_8);
    serial_port.SetParity(LibSerial::Parity::PARITY_NONE);
    serial_port.SetStopBits(LibSerial::StopBits::STOP_BITS_1);
    serial_port.SetFlowControl(LibSerial::FlowControl::FLOW_CONTROL_NONE);

    std::string received_data;
    for (int i = 0; i <= 20; i++) {
        try {
            std::this_thread::sleep_for(std::chrono::seconds(1));
            serial_port.ReadLine(received_data);
            decode_data(reinterpret_cast<const uint8_t*>(received_data.data()), received_data.size());
        } catch (const std::exception& e) {
            std::cerr << "Error reading from serial port: " << e.what() << std::endl;
        }
    }

    serial_port.Close();
    return 0;
}
