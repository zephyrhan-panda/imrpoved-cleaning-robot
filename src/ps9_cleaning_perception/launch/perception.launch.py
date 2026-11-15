from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from pathlib import Path


def _launch(context):
    # Optional CLI overrides must not shadow values edited in the YAML.
    overrides = {}
    for key in ('model_path', 'image_topic', 'device'):
        value = LaunchConfiguration(key).perform(context)
        if value:
            overrides[key] = value
    return [Node(
        package='ps9_cleaning_perception', executable='detector_node',
        name='ps9_detector', namespace=LaunchConfiguration('namespace'),
        output='screen',
        parameters=[LaunchConfiguration('params_file'), overrides],
    )]


def generate_launch_description():
    share = Path(get_package_share_directory('ps9_cleaning_perception'))
    return LaunchDescription([
        DeclareLaunchArgument('namespace', default_value='ps9'),
        DeclareLaunchArgument('params_file', default_value=str(share / 'config/detector.yaml')),
        DeclareLaunchArgument('model_path', default_value=''),
        DeclareLaunchArgument('image_topic', default_value=''),
        DeclareLaunchArgument('device', default_value=''),
        OpaqueFunction(function=_launch),
    ])
