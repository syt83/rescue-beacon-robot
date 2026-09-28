from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from ament_index_python.packages import get_package_share_directory

import os


def generate_launch_description():
    # YAML 한 파일의 설정을 ROS 노드가 함께 사용한다.
    pkg_share = get_package_share_directory('rescue_beacon')
    config_file = os.path.join(pkg_share, 'config', 'rescue_beacon.yaml')

    enable_person = LaunchConfiguration('enable_person')
    camera_only = LaunchConfiguration('camera_only')
    enable_serial = LaunchConfiguration('enable_serial')
    enable_motion = LaunchConfiguration('enable_motion')
    enable_audio = LaunchConfiguration('enable_audio')
    max_linear_speed = LaunchConfiguration('max_linear_speed')
    max_angular_speed = LaunchConfiguration('max_angular_speed')
    log_motor_commands = LaunchConfiguration('log_motor_commands')
    serial_port = LaunchConfiguration('serial_port')

    return LaunchDescription([
        # 배선 전에는 Arduino 연결과 모터 전달이 기본적으로 꺼져 있다.
        DeclareLaunchArgument(
            'enable_person', default_value='true',
            description='Run the YOLO person-follow node',
        ),
        DeclareLaunchArgument(
            'camera_only', default_value='false',
            description='Short supervised camera trial without LiDAR navigation',
        ),
        DeclareLaunchArgument(
            'enable_serial', default_value='false',
            description='Open the Arduino USB serial port',
        ),
        DeclareLaunchArgument(
            'enable_motion', default_value='false',
            description='Forward nonzero motor commands after handshake',
        ),
        DeclareLaunchArgument(
            'enable_audio', default_value='true',
            description='Forward ALERT playback requests to Arduino',
        ),
        DeclareLaunchArgument(
            'max_linear_speed', default_value='0.20',
            description='Upper bound on commanded linear speed in m/s',
        ),
        DeclareLaunchArgument(
            'max_angular_speed', default_value='0.70',
            description='Upper bound on commanded angular speed in rad/s',
        ),
        DeclareLaunchArgument(
            'log_motor_commands', default_value='false',
            description='Log motor commands sent to Arduino during trials',
        ),
        DeclareLaunchArgument(
            'serial_port', default_value='/dev/ttyACM0',
            description='Arduino Nano Every serial port',
        ),

        Node(
            package='rescue_beacon',
            executable='lidar_nav_node',
            name='lidar_nav_node',
            output='screen',
            parameters=[config_file],
            condition=UnlessCondition(camera_only),
        ),

        Node(
            package='rescue_beacon',
            executable='person_follow_node',
            name='person_follow_node',
            output='screen',
            parameters=[
                config_file,
                {
                    'require_fallen': ParameterValue(
                        camera_only, value_type=bool
                    ),
                },
            ],
            condition=IfCondition(enable_person),
        ),

        Node(
            package='rescue_beacon',
            executable='mission_controller_node',
            name='mission_controller_node',
            output='screen',
            parameters=[
                config_file,
                {'enable_person': ParameterValue(enable_person, value_type=bool)},
                {'camera_only': ParameterValue(camera_only, value_type=bool)},
            ],
        ),

        Node(
            package='rescue_beacon',
            executable='serial_bridge_node',
            name='serial_bridge_node',
            output='screen',
            parameters=[
                config_file,
                {
                    'port': serial_port,
                    'enable_motion': ParameterValue(
                        enable_motion, value_type=bool
                    ),
                    'enable_audio': ParameterValue(
                        enable_audio, value_type=bool
                    ),
                    'max_linear_speed': ParameterValue(
                        max_linear_speed, value_type=float
                    ),
                    'max_angular_speed': ParameterValue(
                        max_angular_speed, value_type=float
                    ),
                    'log_motor_commands': ParameterValue(
                        log_motor_commands, value_type=bool
                    ),
                    'soft_motion': ParameterValue(camera_only, value_type=bool),
                    'trial_motion_window_sec': 2.0,
                },
            ],
            condition=IfCondition(enable_serial),
        ),
    ])
