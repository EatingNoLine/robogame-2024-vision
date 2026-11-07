/*
 * STP-23 lidar packet decoder - offline probe from the 2024 season.
 *
 * This program is not part of the vision pipeline and is not built by CI; it is
 * kept because it documents the lidar frame layout the team reverse-engineered.
 * `main()` decodes a zero-filled frame with a self-consistent checksum, which is
 * enough to exercise the parser.
 *
 * Frame layout (for reference):
 *
 *   offset  size  field
 *   0       4     start of frame, 0xAA 0xAA 0xAA 0xAA
 *   4       1     device address
 *   5       1     command code
 *   6       1     chunk offset
 *   7       1     data length
 *   8       180   12 measurement points, 15 bytes each
 *   188     1     checksum (8-bit sum, see calculate_checksum)
 *
 * The 2024 version declared the point struct without packing, so
 * sizeof(LidarPointTypedef) was 20 instead of the 15-byte wire layout and every
 * field after `confidence` was read at the wrong offset. See native/lidar/README.md.
 */

#include <stdint.h>
#include <stdio.h>
#include <string.h>

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

_Static_assert(sizeof(LidarPointTypedef) == POINT_BYTES, "point struct must pack to 15 bytes");

uint8_t calculate_checksum(const uint8_t *data, size_t length) {
    uint8_t checksum = 0;
    for (size_t i = 0; i < length; i++) {
        checksum += data[i];
    }
    return checksum;
}

void decode_data(const uint8_t *buffer, size_t length) {
    if (memcmp(buffer, "\xAA\xAA\xAA\xAA", 4) != 0) {
        printf("Invalid start symbol\n");
        return;
    }

    printf("frame: addr=0x%02X cmd=0x%02X chunk=0x%02X payload=%u B\n", buffer[4], buffer[5],
           buffer[6], buffer[7]);

    const uint8_t checksum_received = buffer[length - 1];
    const uint8_t checksum_calculated = calculate_checksum(buffer + 4, length - 5);
    if (checksum_received != checksum_calculated) {
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

int main(void) {
    uint8_t packet[8 + POINTS_PER_FRAME * POINT_BYTES + 1];
    memset(packet, 0, sizeof(packet));

    const uint8_t header[8] = {0xAA, 0xAA, 0xAA, 0xAA, 0x00, 0x02, 0x00, 0x00};
    memcpy(packet, header, sizeof(header));
    packet[sizeof(packet) - 1] = calculate_checksum(packet + 4, sizeof(packet) - 5);

    decode_data(packet, sizeof(packet));
    return 0;
}
