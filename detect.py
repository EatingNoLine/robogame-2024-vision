import cv2
import time
import os
import shutil
import torch
from ultralytics import YOLO
import matplotlib.pyplot as plt
from PIL import Image
import numpy as np


EXACT_FAR_LENGTH = 1550
EXACT_LEFT_LENGTH = 1105
EXACT_RIGHT_LENGTH = 1105
EXACT_CLOSE_LENGTH = 750


def image_compress(img, scale_factor=0.8): # not_used
    width = int(img.shape[1] * scale_factor)
    height = int(img.shape[0] * scale_factor)
    dim = (width, height) 
    img_resized = cv2.resize(img, dim, interpolation=cv2.INTER_AREA)
    return img_resized

def clear_output():
    for item in os.listdir("./images/output"):
        item_path = os.path.join("./images/output", item)
        # 如果是文件，则删除
        if os.path.isfile(item_path):
            os.remove(item_path)
            print(f"已删除文件: {item_path}")
        # 如果是子目录，则递归删除
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)
            print(f"已删除目录及其内容: {item_path}")

def capture(num_of_video, bgr2rgb=True): # take a photo & yolo process

    # 打开摄像头
    cap = cv2.VideoCapture("/dev/video" + num_of_video)
    if not cap.isOpened():
        print("无法打开摄像头")
        exit()

    # 从摄像头读取一帧
    ret, frame = cap.read()
    
    if ret:
        # 保存帧
        # frame = image_compress(frame)
        if bgr2rgb:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        filename = "./images/input/" + num_of_video + ".jpg"
        cv2.imwrite(filename, frame)
        print(f"保存图像: {filename}") # time_waste around 3ms

    else:
        print("无法读取视频流")

    # 释放摄像头
    cap.release()

    # Load YOLO model
    model = YOLO("./new.pt")

    # Perform object detection on an image
    # image_paths = ["./images/input/"+num_of_video+".jpg"]
    results = model(source=frame, save=True, project="./images/output", show=False)
    boxes_list = []

    if not results:  # 如果 results 为空
        print("No results found.")
    else:
        # Extract and print bounding boxes
        for result in results:
            masks = result.masks
            mask_data = masks.data[0].numpy()
            print(mask_data)
    
            # 标准化到 0-255 范围
            normalized_mask = 255 * (mask_data / np.max(mask_data)).astype(np.uint8)
    
            # 将标准化后的数据转换为图像
            mask_image = Image.fromarray(normalized_mask)
            mask_image.save('images/masks/normalized_mask_image.png')
    
            # Visualize mask
            # plt.figure(figsize=(8, 6))
            # plt.imshow(mask_data, cmap='gray')
            # plt.title('Mask Visualization')
            # plt.show()
    
            # boundary_points = masks.xy[0]
    
            # Plot boundary points
            # plt.figure(figsize=(8, 6))
            # plt.imshow(mask_data, cmap='gray')
            # plt.plot(boundary_points[:, 0], boundary_points[:, 1], 'r-', lw=2)
            # plt.title('Mask Boundary')
            # plt.show()
    
            for box in result.boxes:
                if box.cls == torch.tensor([0.]):
                    tmp_list = box.xywh.tolist()[0]
                    tmp_list.append(int(num_of_video)) # 为每个数据记录vedio名以便后续使用
                    boxes_list.append(tmp_list)
    return boxes_list, frame.size, frame

def analyze(box_list):
    area_list = []
    print("Detected_boxes:")
    for box in box_list:
        print(box)
        area_list.append(box[2]*box[3])
    if area_list:
        max_area = max(area_list)
        max_index = area_list.index(max_area) # 如果有两个相同的最大值则会返回第一个
        video_chosed = box_list[max_index][-1] # 读取在capture中记录的vedio名
        print("在video_" + str(video_chosed) + "中追踪面积最大的实例")
        print("box xywhn:[center_x, center_y, width, height, video_num]")
        print(box_list[max_index])
        [center_x, center_y] = [box_list[max_index][0], box_list[max_index][1]]
        return [center_x, center_y]
    else:
        raise Exception("Error: area_list is empty")
        max_area = None


def perspective_trans(img, origin_point):
    img_width = int(img.shape[1])
    img_height = int(img.shape[0])
    print(img_width)
    print(img_height)
    # 定义原始图像中四个点
    pts1 = np.float32([[0, 0], [img_width, 0], [0, img_height], [img_width, img_height]])
    # 定义目标图像中对应的四个点
    pts2 = np.float32([[0, 0], [EXACT_FAR_LENGTH, 0], [(EXACT_FAR_LENGTH-EXACT_CLOSE_LENGTH)/2, EXACT_LEFT_LENGTH], [EXACT_FAR_LENGTH-(EXACT_FAR_LENGTH-EXACT_CLOSE_LENGTH)/2, EXACT_RIGHT_LENGTH]])
    # 计算透视变换矩阵
    pt_matrix = cv2.getPerspectiveTransform(pts1, pts2)
    # 应用透视变换
    result = cv2.warpPerspective(img, pt_matrix, (EXACT_FAR_LENGTH, EXACT_LEFT_LENGTH))
    # 保存和显示结果
    cv2.imwrite("img.jpg", img)
    cv2.imwrite('perspective_transformed.jpg', result)
    
    origin_point = np.float32(origin_point).reshape(-1, 1, 2)
    transformed_point = cv2.perspectiveTransform(origin_point, pt_matrix)
    print(transformed_point)

    return result, transformed_point



if __name__ == "__main__":
    # 清除输出文件夹
    clear_output() # time_waste less than 1ms

    # print("---------------vedio24---------------")
    # boxes_list_1, img_size_1, origin_img = capture("24")
    # analyze(boxes_list_1)

    # print("---------------vedio22---------------")
    # boxes_list_2, img_size_2, origin_img = capture("22")
    # analyze(boxes_list_2)

    # print("---------------vedio20---------------")  
    # boxes_list_3, img_size_3, origin_img = capture("20", bgr2rgb=False)
    # analyze(boxes_list_3)

    # 打开摄像头
    cap = cv2.VideoCapture("/dev/video" + "20")
    if not cap.isOpened():
        print("无法打开摄像头")
        exit()

    # 从摄像头读取一帧
    ret, frame = cap.read()
    perspective_trans(frame, (1,1))


