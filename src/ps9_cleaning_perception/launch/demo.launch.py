from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    share = Path(get_package_share_directory('ps9_cleaning_perception'))
    return LaunchDescription([
        DeclareLaunchArgument('namespace', default_value='ps9'),
        DeclareLaunchArgument('source', default_value=str(share / 'samples/sample.png')),
        DeclareLaunchArgument('image_topic', default_value='/camera/image_raw'),
        DeclareLaunchArgument('model_path', default_value=''),
        DeclareLaunchArgument('device', default_value=''),
        DeclareLaunchArgument('fps', default_value='5.0'),
        DeclareLaunchArgument('loop_video', default_value='false'),
        DeclareLaunchArgument('params_file', default_value=str(share / 'config/detector.yaml')),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(share / 'launch/perception.launch.py')),
            launch_arguments={key: LaunchConfiguration(key) for key in
                              ('namespace', 'image_topic', 'model_path', 'device', 'params_file')}.items(),
        ),
        Node(
            package='ps9_cleaning_perception', executable='image_source_node',
            name='ps9_image_source', namespace=LaunchConfiguration('namespace'),
            output='screen', parameters=[{
                'source': ParameterValue(LaunchConfiguration('source'), value_type=str),
                'image_topic': LaunchConfiguration('image_topic'),
                'fps': ParameterValue(LaunchConfiguration('fps'), value_type=float),
                'loop_video': ParameterValue(LaunchConfiguration('loop_video'), value_type=bool),
                'frame_id': 'camera_optical_frame',
            }],
        ),
    ])
