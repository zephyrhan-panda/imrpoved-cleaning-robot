

## 浏览器 2D 演示与检测示例（无需机器人）

`web_demo/` 已改为 2D 俯视场景：查看机器人与三类污渍，播放、暂停、重置和加速模拟过程，并可选择目标和重新布置。旁边附带已有验证图像上的实际模型检测输出。

[打开在线 2D 演示](https://ps9-cleaning-3d-demo.fhan08588.chatgpt.site)（私有，仅站点所有者可访问）。

```bash
# 在项目根目录运行，然后打开 http://127.0.0.1:8765
python3 -m http.server 8765 --bind 127.0.0.1 --directory web_demo
```

**演示中的场景、坐标、预设路线及清洁结果均为模拟数据，尚未连接相机、ROS 2 或真实机器人。** 不需要安装 Node.js、ROS 或 3D 图形依赖。检测图片是模型预测，不是人工真值标注。操作与后续接入说明见 [web_demo/README.md](web_demo/README.md)，验证记录见 [verification/WEB_DEMO_2D.md](verification/WEB_DEMO_2D.md)。

个人主页：[Fang Han — Industrial Experience](https://fang-han-portfolio.fhan08588.chatgpt.site/#industrial-experience)。该项目由 Fang Han 在 Sichuan Jiutian Embodied Intelligence 负责，时间为 Summer 2026。

## 1. 项目结构

```text
ps9_cleaning_ros2/
├── web_demo/                     # 2D 模拟演示与真实验证图像检测示例
├── src/ps9_cleaning_perception/
│   ├── package.xml / setup.py / setup.cfg
│   ├── resource/ps9_cleaning_perception
│   ├── ps9_cleaning_perception/
│   │   ├── core.py                 # 与 ROS 无关的原模型推理
│   │   ├── detector_node.py        # 图像 → 2D 检测 + 标注 + 状态
│   │   ├── image_source_node.py    # 图片、视频、USB 摄像头演示输入
│   │   ├── messages.py             # vision_msgs 转换
│   │   ├── buffering.py            # 单帧缓存和过期帧过滤
│   │   ├── paths.py                # 安装位置/源码位置的资源解析
│   │   └── offline.py              # 不启动 ROS 的单图推理
│   ├── launch/
│   │   ├── perception.launch.py    # 接入已有 ROS 相机话题
│   │   └── demo.launch.py          # 自带图像发布器
│   ├── config/detector.yaml
│   ├── models/best.onnx / best.pt
│   ├── samples/sample.png
│   └── test/                      # 算法一致性、边界和 ROS 通信测试
├── scripts/verify_ros.sh
├── legacy/                        # 原脚本和原类别文件，只作溯源
├── verification/                  # 此次真实测试记录与推理结果
├── SOURCE_MANIFEST.json            # 原文件路径、大小、SHA-256
├── requirements.txt
└── README.md
```

## 2. 安装依赖和构建

以下命令在已安装 ROS 2 Jazzy 的 Ubuntu 上执行。先解压项目并进入这个 README 所在目录。Humble 用户将下面的 `jazzy` 换成 `humble`；后面的 `${ROS_DISTRO}` 会自动使用该版本。

```bash
source /opt/ros/jazzy/setup.bash
sudo apt update
sudo apt install -y python3-venv python3-pip python3-rosdep \
  python3-colcon-common-extensions \
  ros-${ROS_DISTRO}-cv-bridge ros-${ROS_DISTRO}-vision-msgs \
  ros-${ROS_DISTRO}-diagnostic-msgs

# 仅第一次配置 rosdep 时需要 sudo rosdep init。
# 若提示 rosdep 未初始化，先运行 sudo rosdep init，再继续。
rosdep update
rosdep install --from-paths src --ignore-src -r -y

# 必须使用与 ROS 二进制一致的 Ubuntu 系统 Python。
/usr/bin/python3 -m venv --system-site-packages .venv
source .venv/bin/activate
touch .venv/COLCON_IGNORE
python -m pip install 'setuptools<80' wheel 'pytest<9' colcon-common-extensions

# CPU 默认方案，避免安装不需要的 CUDA 依赖。
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt

# colcon 使用刚创建的 venv 解释器构建节点入口。
colcon build --symlink-install
source install/setup.bash
```

如果 `.venv` 中已经有自行安装的不同版本 `torch/torchvision`，应使用一组相互兼容的版本。`requirements.txt` 固定了 Ultralytics、ONNX 和 CPU ONNX Runtime；`numpy==1.26.4` 用于兼容发行版 `cv_bridge`。不建议在此工作空间混用 Conda Python 与 Ubuntu 的 ROS 二进制。

以后每个新终端都执行：

```bash
source /opt/ros/jazzy/setup.bash
source .venv/bin/activate
source install/setup.bash
```

## 3. 启动

### 没有机器人：用自带样例演示

```bash
ros2 launch ps9_cleaning_perception demo.launch.py
```

默认每秒发布 5 张样例图像。另开一个配置好环境的终端查看检测：

```bash
ros2 topic echo /ps9/detections --once
ros2 topic echo /ps9/diagnostics --once
ros2 topic echo /ps9/class_map --qos-durability transient_local --once
```

用 `rqt_image_view` 查看标注图；如果没有安装，先安装对应 ROS 发行版的 `rqt-image-view` 包：

```bash
sudo apt install ros-${ROS_DISTRO}-rqt-image-view
ros2 run rqt_image_view rqt_image_view /ps9/annotated_image
```

标注图话题使用 Best Effort；若查看器发现了话题但没有图像，请将查看器的 Reliability 设为 Best Effort。

### 接入已有的 ROS 相机

```bash
ros2 launch ps9_cleaning_perception perception.launch.py \
  image_topic:=/camera/color/image_raw
```

输入类型为 `sensor_msgs/msg/Image`。相机会继续由原有驱动运行；本节点用 `cv_bridge` 转换为 BGR8，输出保留输入图像的 `stamp` 和 `frame_id`。压缩图像需先通过相机驱动或 `image_transport` 转为原始 `Image` 话题。

### USB 摄像头或本地视频

```bash
# 摄像头索引 0；也支持 Linux /dev/video0。
ros2 launch ps9_cleaning_perception demo.launch.py source:=0 fps:=10.0

# 替换为真实的视频路径；默认在结尾停止发布。
ros2 launch ps9_cleaning_perception demo.launch.py \
  source:=/absolute/path/to/video.mp4 loop_video:=true fps:=10.0
```

视频按指定 FPS 逐帧读取，时间戳为本次读取/发布时间；不是原视频时间。此演示发布器支持本地文件和摄像头，不提供网络流重连。已有相机驱动通常更适合持续运行。

### 使用 PyTorch 权重 / 已配置 CUDA 的机器人

CPU 模型切换：

```bash
ros2 launch ps9_cleaning_perception perception.launch.py \
  model_path:="$(pwd)/src/ps9_cleaning_perception/models/best.pt" device:=cpu
```

CUDA 环境使用匹配机器人 CUDA / JetPack 的 PyTorch，然后设置 `device:=0`。本项目的 ONNX 配置固定使用 CPU；GPU 入口使用 `.pt`。Jetson 的 CUDA 依赖不应套用上面的 CPU 安装命令，当前未验证 Jetson。

## 4. 话题与语义

默认命名空间为 `/ps9`，可通过 `namespace:=robot1` 修改。输入话题可独立指定。

| 话题 | 类型 | 内容 / QoS |
|---|---|---|
| `/camera/image_raw` | `sensor_msgs/msg/Image` | 输入；默认 Best Effort、depth 1 |
| `/ps9/detections` | `vision_msgs/msg/Detection2DArray` | 原图像素坐标的框、类别 ID、置信度；Reliable、depth 1 |
| `/ps9/annotated_image` | `sensor_msgs/msg/Image` | BGR8 标注图；Best Effort、depth 1 |
| `/ps9/class_map` | `std_msgs/msg/String` | JSON 类别映射；Reliable + Transient Local，迟加入的订阅者可读取 |
| `/ps9/diagnostics` | `diagnostic_msgs/msg/DiagnosticArray` | 每秒发布推理状态、成功/失败/丢帧计数和耗时 |

`Detection2D.results[0].hypothesis.class_id` 是字符串形式的模型数字 ID，例如 `"0"`；名称通过 `/ps9/class_map` 查询。`bbox.center.position.x/y` 是中心像素，`bbox.size_x/y` 是宽高像素，`theta=0`。坐标已回映到原始图像尺寸，不是 640×640 网络输入坐标。

只有真正完成推理、且没有检出目标时，才会发布空的 `Detection2DArray`。图像解码或推理失败会进入诊断错误状态，不伪装成空检测。推理前后均检查帧龄，超过 `max_image_age_sec` 的图像丢弃；新图像覆盖等待中的旧图像，避免排队累积延迟。

未收到有效图像时诊断为 WARN；已有成功结果但长时间没有更新时为 STALE。下游应检查时间戳和诊断，不能一直复用旧检测。相机时钟应与节点一致；rosbag 使用模拟时间时，在配置中添加 `use_sim_time: true` 并让 bag 发布 `/clock`。零时间戳只按本节点接收后的等待时间判断帧龄。

这是二维视觉识别组件，未计算真实距离、三维坐标或跟踪 ID，也未发布底盘/清洁执行机构控制命令。后续控制接入需结合你的相机标定、深度信息及控制接口。

## 5. 类别顺序：已处理原文件的不一致

模型实际元数据（ONNX 与 PT 一致）：

| ID | 名称 |
|---|---|
| 0 | `bigdirt` |
| 1 | `dirt` |
| 2 | `water` |
| 3 | `background` |

原 `classes.txt` 把前两个名称反过来了，`dataset.yaml` 与模型一致。运行时始终读取模型返回的类别，避免把 `bigdirt` 和 `dirt` 对调。原始文本保存在 `legacy/`，没有拿它覆盖模型。

为保留原脚本行为，默认会输出全部四类。若清洁策略只关心污物和水，可将配置中的 `exclude_classes` 改为 `"background"`；过滤发生在 NMS 之后，其他类别的推理结果保持原样。

## 6. 参数

编辑 `src/ps9_cleaning_perception/config/detector.yaml` 后重新启动节点。也可通过 `params_file:=/absolute/path/to/custom.yaml` 指定独立配置。`model_path`、`image_topic`、`device` 的非空 launch 参数优先于 YAML；不传时使用 YAML。

| 参数 | 默认值 | 用途 |
|---|---|---|
| `model_path` | 空 | 自动定位随包安装的 `best.onnx` |
| `image_topic` | `/camera/image_raw` | 输入图像话题 |
| `image_reliability` | `best_effort` | 可选 `reliable`，需要与发布者 QoS 匹配 |
| `confidence` | `0.30` | 置信度阈值 |
| `iou` | `0.70` | NMS IoU |
| `image_size` | `640` | 原 ONNX 为静态 640×640，其他尺寸会明确报错 |
| `device` | `cpu` | `.pt` 可使用匹配环境的 CUDA 设备或 MPS |
| `max_detections` | `300` | 单图 NMS 最大检测数 |
| `max_fps` | `10.0` | 推理调度上限，实际速度由设备决定 |
| `max_image_age_sec` | `2.0` | 过期输入及过期推理结果的丢弃阈值 |
| `publish_annotated` | `true` | 是否额外生成标注图 |
| `exclude_classes` | 空字符串 | 按名称过滤，多个名称用逗号分隔 |

这些业务参数是启动时只读参数，运行中 `ros2 param set` 会拒绝修改；需要调整时重新启动，避免参数值与模型实际状态不一致。

## 7. 不启动 ROS 的推理与验证

在已有推理依赖的环境中，可直接从源码执行：

```bash
PYTHONPATH=src/ps9_cleaning_perception \
  python -m ps9_cleaning_perception.offline --output demo_output

# 或在构建和 source 完成后：
ros2 run ps9_cleaning_perception predict_image --output demo_output
```

输出 `annotated.jpg` 和 `detections.json`。可添加 `--source /absolute/path/to/image.png`、`--model ...`、`--conf 0.30`。原 `legacy/predict.py` 是原文存档，请使用新的入口运行。

算法与非 ROS 测试：

```bash
PYTHONPATH=src/ps9_cleaning_perception \
  python -m pytest src/ps9_cleaning_perception/test -q
```

在 Ubuntu ROS 2 环境完成实际验收：

```bash
bash scripts/verify_ros.sh
```

此脚本先检查 ROS 依赖，随后执行构建、启动参数解析和全部测试，包含真实消息类型、DDS 发布订阅、空检测/解码失败区分，以及样例发布器 → 原 ONNX 模型 → 检测话题的联通测试。

## 8. 来源与验证边界

- `SOURCE_MANIFEST.json` 记录每份原始文件的来源和 SHA-256；模型字节未改动。
- 演示图片来自已有 `refsafe_v1` 的 **validation** 集，仅用于运行验证；未访问 test，也未用它重新选择阈值。
- 样例推理成功只能说明封装运行和结果一致性，不代表新的检测精度或机器人实测成绩。
- `package.xml` 中维护者邮箱是占位值，交接团队后可更新。原模型内的许可元数据保留原样；本次封装未重新授权原模型或数据。

实现参照：[ROS 2 Python 包结构](https://repo.test.ros2.org/en/jazzy/How-To-Guides/Developing-a-ROS-2-Package.html)、[ROS 2 Python 环境要求](https://repo.test.ros2.org/en/jazzy/How-To-Guides/Using-Python-Packages.html)、[vision_msgs 消息定义](https://github.com/ros-perception/vision_msgs/tree/4.1.0/vision_msgs/msg)、[Ultralytics 推理接口](https://docs.ultralytics.com/modes/predict/)。
