from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

import os


def generate_launch_description():
    pkg_share = get_package_share_directory('rescue_beacon')
    config_file = os.path.join(pkg_share, 'config', 'rescue_beacon.yaml')

    enable_person = LaunchConfiguration('enable_person')
    enable_serial = LaunchConfiguration('enable_serial')

    return LaunchDescription([
        DeclareLaunchArgument('enable_person', default_value='true'),
        DeclareLaunchArgument('enable_serial', default_value='true'),

        Node(
            package='rescue_beacon',
            executable='lidar_nav_node',
            name='lidar_nav_node',
            output='screen',
            parameters=[config_file],
        ),

        Node(
            package='rescue_beacon',
            executable='person_follow_node',
            name='person_follow_node',
            output='screen',
            parameters=[config_file],
            condition=IfCondition(enable_person),
        ),

        Node(
            package='rescue_beacon',
            executable='mission_controller_node',
            name='mission_controller_node',
            output='screen',
            parameters=[config_file],
        ),

        Node(
            package='rescue_beacon',
            executable='serial_bridge_node',
            name='serial_bridge_node',
            output='screen',
            parameters=[config_file],
            condition=IfCondition(enable_serial),
        ),
    ])
