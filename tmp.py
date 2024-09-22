import v4l2
import fcntl
import mmap
import numpy as np
import cv2

# 打开摄像头设备
device = '/dev/video20'
fd = open(device, 'r+b')

# 设置视频格式
fmt = v4l2.v4l2_format()
fmt.type = v4l2.V4L2_BUF_TYPE_VIDEO_CAPTURE
fmt.fmt.pix.width = 640
fmt.fmt.pix.height = 480
fmt.fmt.pix.pixelformat = v4l2.V4L2_PIX_FMT_YUYV
fcntl.ioctl(fd, v4l2.VIDIOC_S_FMT, fmt)

# 请求缓冲区
req = v4l2.v4l2_requestbuffers()
req.count = 1
req.type = v4l2.V4L2_BUF_TYPE_VIDEO_CAPTURE
req.memory = v4l2.V4L2_MEMORY_MMAP
fcntl.ioctl(fd, v4l2.VIDIOC_REQBUFS, req)

# 查询缓冲区
buf = v4l2.v4l2_buffer()
buf.type = v4l2.V4L2_BUF_TYPE_VIDEO_CAPTURE
buf.memory = v4l2.V4L2_MEMORY_MMAP
fcntl.ioctl(fd, v4l2.VIDIOC_QUERYBUF, buf)

# 映射缓冲区
buffer = mmap.mmap(fd.fileno(), buf.length, offset=buf.m.offset)

# 读取帧
fcntl.ioctl(fd, v4l2.VIDIOC_QBUF, buf)
fcntl.ioctl(fd, v4l2.VIDIOC_DQBUF, buf)

# 处理图像
frame = np.frombuffer(buffer, dtype=np.uint8)
frame = frame.reshape((480, 640, 2))  # 适配为 YUYV 格式
frame = cv2.cvtColor(frame, cv2.COLOR_YUYV2BGR)  # 转换为 BGR 格式

# 显示图像
cv2.imwrite('tmp/frame.jpg', frame)

# 清理
buffer.close()
fd.close()
