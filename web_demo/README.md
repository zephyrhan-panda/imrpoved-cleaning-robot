# PS9 2D 清洁机器人演示

用户要求的 2D 俯视场景，替代原 Three.js 3D 演示。纯 HTML / CSS / SVG / JavaScript，不需要 ROS、相机、WebGL、Node.js 或 CDN。

场景可以播放、暂停、继续、重置、加速及重新布置；点击污渍或编号按钮可查看模拟位置与状态。旁边附带真实验证图像上的模型检测输出。

## 启动

从项目根目录运行：

```bash
python3 -m http.server 8765 --bind 127.0.0.1 --directory web_demo
```

打开 <http://127.0.0.1:8765>。不要直接双击 HTML，因为浏览器会限制本地 JavaScript 模块的加载。

## 数据说明

- 2D 房间、污渍坐标、机器人运动、预设路线和清理状态均为模拟数据。没有执行检测推理、真实规划、避障或机器人控制。
- `assets/cleaning-detection.jpg` 原样复制自 `verification/sample_result/annotated.jpg`，是原始 ONNX 模型在已有验证样例上的检测输出。`bigdirt` 原始分数为 0.9586209058761597，图中显示为 0.96；这是置信度，不是准确率。
- 绿色框属于模型预测，不是人工真值标注。
- 进度是模拟目标清理数量，不是地面覆盖率。

## 结构

- `scene2d.mjs` / `demo.css`：可嵌入个人主页的 SVG 场景和控制界面。
- `simulation.mjs`：复用的确定性模拟状态与预设路线，目标类别对应模型的 `bigdirt`、`dirt`、`water`。
- `index.html` / `style.css` / `app.mjs`：独立演示页及实际检测图片。

该项目在 Fang Han 的个人主页中属于 **Industrial Experience**：Sichuan Jiutian Embodied Intelligence，Summer 2026。

后续若接入 ROS 2，需要将二维检测定位到地面坐标，并处理相机标定、时间同步和跨帧关联。当前模拟坐标不能作为实测数据。
