import cv2
import numpy as np
from matplotlib import pyplot as plt

# read image
img = cv2.imread('img_example.jpg')
img = cv2.resize(img, (0, 0), fx=0.3, fy=0.3)
img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

# convert to hsv, filter orange color
hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
lower = (0, 100, 50)
upper = (70, 255, 255)
mask = cv2.inRange(hsv, lower, upper)

plt.figure(figsize=(10, 5))
plt.subplot(121)
plt.imshow(img)
plt.subplot(122)
plt.imshow(mask, cmap='gray')

contours, hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
print(len(contours), "contour(s) in total.")
print("hierarchy of contour(s):\n", hierarchy)

img_all_contours = img.copy()
cv2.drawContours(img_all_contours, contours, -1, (0, 255, 0), 3)
plt.imshow(img_all_contours)

# get the largest one
contour = max(contours, key=cv2.contourArea)

img_contour = img.copy()
cv2.drawContours(img_contour, [contour], -1, (0, 255, 0), 3)
plt.figure(figsize=(10, 5))
plt.imshow(img_contour)

# vertices
epsilon = 0.01 * cv2.arcLength(contour, True)
vertices = cv2.approxPolyDP(contour, epsilon, True)

img_all_vertices = img.copy()
for v in vertices:
    cv2.circle(img_all_vertices, tuple(v[0]), 10, (0, 255, 0), -1)
plt.imshow(img_all_vertices)

img_all_vertices = img.copy()
for v in vertices:
    cv2.circle(img_all_vertices, tuple(v[0]), 10, (0, 255, 0), -1)
plt.figure(figsize=(10, 5))
plt.imshow(img_all_vertices)

plt.show()

# get 4 points of front face
# (x, y) zero point is at the top-left corner, x axis points right, y axis points down
points = vertices.reshape(-1, 2)
points = points[points[:, 1].argsort()]

d1 = abs(points[1][1] - points[0][1])
d2 = abs(points[2][1] - points[1][1])
if d1 < d2:
    FACES = 2
    points = points[points[:, 1] > points[1][1]]
elif d1 > d2:
    FACES = 3
    points = points[np.bitwise_and(points[:, 1] > points[0][1], points[:, 1] < points[5][1])]

# sort points: top-left, top-right, bottom-left, bottom-right
points[:2] = points[points[:2, 0].argsort()]
points[2:] = points[2:][points[2:, 0].argsort()]
print("FACES:", FACES)
print("points:\n", points)

img_points = img.copy()
for p in points:
    cv2.circle(img_points, tuple(p), 10, (0, 255, 0), -1)
plt.figure(figsize=(10, 5))
plt.imshow(img_points)

# the following is a example for 3d rebuild
def draw_coordsys(img, origin, axes_proj, thickness=5):
    '''
    Draw a 3D coordinate system on the image.
    origin: the origin of the coordinate system.
    axes_proj: 3 unit vectors of the coordinate system.
    '''
    img = cv2.line(img, origin, tuple(axes_proj[0].ravel()), (255, 0, 0), thickness)
    img = cv2.line(img, origin, tuple(axes_proj[1].ravel()), (0, 255, 0), thickness)
    img = cv2.line(img, origin, tuple(axes_proj[2].ravel()), (0, 0, 255), thickness)
    return img
import numpy as np

# solve pnp
fc = 1000
cx = img.shape[1] / 2
cy = img.shape[0] / 2
camera_matrix = np.array([[fc, 0, cx], [0, fc, cy], [0, 0, 1]])
dist_coeffs = np.zeros((4, 1))

if FACES == 2:
    obj_points = np.array([[0, 0, 0], [100, 0, 0], [0, 100, 0], [100, 100, 0]], dtype=np.float32)
    ret, rvec, tvec = cv2.solvePnP(obj_points, points.astype(np.float32), camera_matrix, dist_coeffs,
                                   flags=cv2.SOLVEPNP_IPPE)

elif FACES == 3:
    obj_points = np.array([[0, 0, 0], [141.4, 0, 0], [0, 100, 0], [141.4, 100, 0]], dtype=np.float32)
    ret, _r, tvec = cv2.solvePnP(obj_points, points.astype(np.float32), camera_matrix, dist_coeffs,
                                 flags=cv2.SOLVEPNP_IPPE)
    
    # perform another 45 degree rotation on y axis
    rotate = cv2.Rodrigues(_r)[0]
    R45 = np.array([[np.cos(np.pi / 4), 0, np.sin(np.pi / 4)], [0, 1, 0], [-np.sin(np.pi / 4), 0, np.cos(np.pi / 4)]])
    rotate = np.dot(rotate, R45)
    rvec = cv2.Rodrigues(rotate)[0]

# rvec and tvec are the rotation and translation vectors of the object's coordinate system in the camera's coordinate system
print("rvec:\n", rvec)
print("tvec:\n", tvec)

axes = np.float32([[50, 0, 0], [0, 50, 0], [0, 0, 50]]).reshape(-1, 3)
axes_proj, jac = cv2.projectPoints(axes, rvec, tvec, camera_matrix, dist_coeffs)
axes_proj = np.int32(axes_proj).reshape(-1, 2)

img_coordsys = img.copy()
img_coordsys = draw_coordsys(img_coordsys, points[0], axes_proj)
plt.figure(figsize=(10, 5))
plt.imshow(img_coordsys)
plt.show()
