// Query the YDLIDAR SDK directly, without ROS or any robot motor command.
#include "src/CYdLidar.h"
#include "src/ydlidar_sdk.h"

#include <cmath>
#include <cstdio>
#include <string>

int main(int argc, char **argv) {
  const std::string port = argc > 1 ? argv[1] : "/dev/ttyUSB0";
  ydlidar::os_init();
  CYdLidar lidar;
  lidar.setlidaropt(LidarPropSerialPort, port.c_str(), port.size());
  int baudrate = 128000;
  lidar.setlidaropt(LidarPropSerialBaudrate, &baudrate, sizeof(baudrate));
  int lidar_type = TYPE_TRIANGLE;
  lidar.setlidaropt(LidarPropLidarType, &lidar_type, sizeof(lidar_type));
  int device_type = YDLIDAR_TYPE_SERIAL;
  lidar.setlidaropt(LidarPropDeviceType, &device_type, sizeof(device_type));
  int sample_rate = 5;
  lidar.setlidaropt(LidarPropSampleRate, &sample_rate, sizeof(sample_rate));
  bool single_channel = true;
  lidar.setlidaropt(LidarPropSingleChannel, &single_channel, sizeof(single_channel));
  bool motor_dtr = false;
  lidar.setlidaropt(LidarPropSupportMotorDtrCtrl, &motor_dtr, sizeof(motor_dtr));
  float frequency = 10.0f;
  lidar.setlidaropt(LidarPropScanFrequency, &frequency, sizeof(frequency));
  float range_min = 0.1f;
  float range_max = 12.0f;
  lidar.setlidaropt(LidarPropMinRange, &range_min, sizeof(range_min));
  lidar.setlidaropt(LidarPropMaxRange, &range_max, sizeof(range_max));

  if (!lidar.initialize()) {
    std::fprintf(stderr, "LiDAR init failed: %s\n", lidar.DescribeError());
    return 1;
  }
  if (!lidar.turnOn()) {
    std::fprintf(stderr, "LiDAR start failed: %s\n", lidar.DescribeError());
    lidar.disconnecting();
    return 1;
  }

  int successful_scans = 0;
  int attempts = 0;
  while (successful_scans < 10 && attempts++ < 25) {
    LaserScan scan;
    if (!lidar.doProcessSimple(scan)) {
      std::fprintf(stderr, "Scan read failed: %s\n", lidar.DescribeError());
      continue;
    }
    int valid = 0;
    int zero = 0;
    for (const auto &point : scan.points) {
      valid += std::isfinite(point.range) && point.range >= range_min &&
               point.range <= range_max;
      zero += point.range == 0.0f;
    }
    std::printf("scan %d: SDK points=%zu, valid=%d, zero=%d\n",
                ++successful_scans, scan.points.size(), valid, zero);
    std::fflush(stdout);
  }

  lidar.turnOff();
  lidar.disconnecting();
  ydlidar::os_shutdown();
  return successful_scans == 10 ? 0 : 1;
}
