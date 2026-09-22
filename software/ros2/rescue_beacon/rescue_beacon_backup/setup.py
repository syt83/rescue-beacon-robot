from setuptools import find_packages, setup

package_name = 'rescue_beacon'

setup(
    name=package_name,
    version='0.1.0',

    packages=find_packages(
        exclude=['test']
    ),

    data_files=[
        (
            'share/ament_index/resource_index/packages',
            ['resource/' + package_name]
        ),
        (
            'share/' + package_name,
            ['package.xml']
        ),
    ],

    install_requires=[
        'setuptools'
    ],

    zip_safe=True,

    maintainer='Rescue Beacon Robot Team',
    maintainer_email='team@example.com',

    description='ROS2 package for the Rescue Beacon Robot',

    license='MIT',

    entry_points={
        'console_scripts': [
            'lidar_nav_node = rescue_beacon.lidar_nav_node:main',
        ],
    },
)