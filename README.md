# AI 图像超分辨率放大工具

一个基于 Real-ESRGAN 的图像超分辨率放大工具。网页可部署到 GitHub Pages；AI 推理需要连接一个运行 `server.py` + Real-ESRGAN 的后端。

## 网页使用

打开 GitHub Pages 后，在“AI 后端地址”中填写公网后端地址，例如：

```text
https://your-upscaler-backend.example.com
```

如果在本机运行，可以留空，页面会调用当前域名下的 `/api/health` 和 `/api/upscale`。

## 本机运行后端

1. 从 Real-ESRGAN 官方 Release 下载 `realesrgan-ncnn-vulkan` Windows 便携版。
2. 解压到 `vendor/realesrgan`，确保存在 `vendor/realesrgan/realesrgan-ncnn-vulkan.exe`。
3. 运行：

```text
python server.py 5173
```

4. 打开：

```text
http://localhost:5173/index.html
```

## 重要说明

GitHub Pages 只能托管静态网页，不能运行 Real-ESRGAN。要让其他电脑的用户也能直接使用 AI 放大，需要把 `server.py` 部署到一台公网可访问的服务器或 GPU 云主机。