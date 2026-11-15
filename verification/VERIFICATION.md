# 验证记录 — 2026-10-29

## 已执行

| 检查 | 结果 |
|---|---|
| `colcon list` | 识别到 `ps9_cleaning_perception`，类型为 `ros.ament_python` |
| `colcon build --symlink-install` | 1 个包构建成功，三个可执行入口已安装 |
| 安装资源检查 | launch、YAML、ONNX、PT、样例图片均可从安装目录访问 |
| `colcon test --python-testing pytest` | 17 passed，1 skipped；0 errors / 0 failures |
| 原始 ONNX 一致性 | 同一样例上，封装与原脚本调用的框、分数、类别通过数值比较 |
| PT 模型 | 随包 `best.pt` 成功完成真实图像推理 |
| 安装后命令行入口 | `predict_image` 成功，结果与源码方式一致 |
| 参数及后处理边界 | 类别映射、背景过滤、像素裁切、无效参数、空检测、单帧缓存及帧龄检查通过 |
| 语法与配置 | Python 3.10 语法解析、package.xml、YAML、Bash 脚本语法检查通过 |
| 原始资产完整性 | 模型与归档脚本 SHA-256 记录于 `SOURCE_MANIFEST.json`，复制字节未修改 |

`1 skipped` 指整个 ROS 集成测试模块因为找不到 `rclpy` 而跳过，**不是 ROS 通信测试通过**。该模块包含三个测试：真实 vision_msgs 字段转换、DDS 图像/检测/空结果/错误状态往返、样例发布器连接真实 ONNX 模型。

## 真实样例输出

输入为已存在的 validation 图片，2448×2048；检测到 1 个 `bigdirt`，置信度约 0.958621。结果在 `sample_result/detections.json`，标注图在 `sample_result/annotated.jpg`。

这次检查验证的是封装与原算法的一致性，不是新模型精度评估。没有重训、调阈值或访问 test 集。

## 环境与未验证部分

实际执行环境是 macOS ARM64 / Python 3.13.9 / Ultralytics 8.4.10 / ONNX Runtime 1.23.2，完整版本保存在 `environment.json`。本机复用已有推理库，NumPy 与 OpenCV 版本不同于面向 Ubuntu 的 `requirements.txt`。

本机没有 ROS 2、rclpy、cv_bridge 或 Docker。上述构建成功表示 Python 包及其资源正确安装；没有声称已在 Ubuntu Jazzy/Humble 启动 ROS 节点，也没有执行 DDS、相机或机器人实机联调。Ubuntu 上从零安装依赖、GUI 图像显示、CUDA/Jetson/MPS 路径均未实测。

在目标 ROS 2 机器按 README 安装后，执行：

```bash
bash scripts/verify_ros.sh
ros2 launch ps9_cleaning_perception demo.launch.py
```

随后把 `image_topic` 改为机器人的真实图像话题，检查 `/ps9/detections`、`/ps9/annotated_image` 和 `/ps9/diagnostics`。
