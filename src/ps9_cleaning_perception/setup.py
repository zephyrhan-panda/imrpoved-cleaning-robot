from glob import glob
from setuptools import find_packages, setup

PACKAGE = 'ps9_cleaning_perception'
setup(
    name=PACKAGE,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + PACKAGE]),
        ('share/' + PACKAGE, ['package.xml']),
        *[('share/' + PACKAGE + '/' + folder, glob(folder + '/*'))
          for folder in ('launch', 'config', 'models', 'samples')],
    ],
    install_requires=['setuptools'],
    extras_require={'test': ['pytest']},
    zip_safe=False,
    maintainer='PS9 Project',
    maintainer_email='maintainer@example.com',
    description='PS9 cleaning detector, preserving the original Ultralytics inference.',
    license='Proprietary',
    entry_points={'console_scripts': [
        'detector_node = ps9_cleaning_perception.detector_node:main',
        'image_source_node = ps9_cleaning_perception.image_source_node:main',
        'predict_image = ps9_cleaning_perception.offline:main',
    ]},
)
