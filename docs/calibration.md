# Camera calibration

Each side camera has thirteen NumPy arrays in `data/calibration/{left,right}/`.
They were produced offline before the competition by an OpenCV stereo/chessboard
calibration script that **was not preserved in the repository**; what survived is the
output. Treat the numbers as opaque calibration data you can reuse but cannot
re-derive from this repository alone.

## Files

| File | Shape | Used by the code | Meaning |
| --- | --- | --- | --- |
| `inverse_camera_matrix.npy` | 3×3 | **yes** | `inv(newcam_mtx)` |
| `inverse_rotation.npy` | 3×3 | **yes** | `inv(R_mtx)` |
| `depth_scale.npy` | (1,) | **yes** | assumed depth along the optical axis, mm |
| `translation.npy` | (3,) | **yes** | `tvec1`, camera origin in the arena frame, mm |
| `ground_homography.npy` | 3×3 | **yes** | plane → robot-frame homography |
| `camera_matrix.npy` | 3×3 | no | `cv2.calibrateCamera` intrinsics |
| `distortion.npy` | (1,5) | no | distortion coefficients |
| `rectified_camera_matrix.npy` | 3×3 | no | `getOptimalNewCameraMatrix` result |
| `projection_matrix.npy` | 3×4 | no | `newcam_mtx @ [R \| t]` |
| `extrinsic.npy` | 3×4 | no | `[R \| t]` before inversion |
| `rotation_vector.npy` | (3,1) | no | `rvec1` from `solvePnP` |
| `rotation.npy` | 3×3 | no | `R_mtx`, `Rodrigues(rvec1)` |
| `valid_roi.npy` | (4,) | no | `roi` from `getOptimalNewCameraMatrix` |

The five matrices that are actually used are enough to run the pipeline; the other
eight are kept because they document how the calibration was obtained and are what you
would need to re-project the same camera differently.

## Values

Left (fx ≈ 1049.9, fy ≈ 1047.2, cx ≈ 969.8, cy ≈ 575.7):

```
camera_matrix            [[1049.9061    0.      969.8038] [   0.     1047.23    575.6686] [0 0 1]]
rectified_camera_matrix  [[ 969.8148    0.     1000.2578] [   0.      961.0997  589.4623] [0 0 1]]
ground_homography        [[   1.3528    0.1466    7.0751] [   0.2139    1.0606    3.7646] [0.0017 0.0008 1]]
depth_scale              [450.4716]
translation              [-40.3839 83.3544 439.6566]
valid_roi                [70 53 1818 1003]
```

Right (fx ≈ 1054.4, fy ≈ 1050.9, cx ≈ 989.8, cy ≈ 578.4):

```
camera_matrix            [[1054.4118    0.      989.7688] [   0.     1050.9498  578.3817] [0 0 1]]
rectified_camera_matrix  [[ 970.2006    0.     1009.6141] [   0.      971.4042  599.351 ] [0 0 1]]
ground_homography        [[   1.3464   -0.1837   -5.6513] [  -0.2154    1.0752    3.311 ] [-0.0017 0.0008 1]]
depth_scale              [444.433 ]
translation              [17.7235 86.6053 435.3839]
valid_roi                [81 56 1799 1008]
```

The two rotation matrices are mirror images of each other in `x`, as expected for two
cameras looking outwards to the left and right. The translations differ by only ~58 mm,
which is one more reason there is no stereo triangulation: the baseline is too small.

## The projection

For a pixel `(u, v)`:

```
                   camera frame                       arena frame
suv     = s · [u, v, 1]            (s = depth_scale)
xyz_cam = inv(newcam_mtx) · suv - tvec
xyz_arena = inv(R) · xyz_cam
[x, y] = homography([xyz_arena.x, xyz_arena.y])
```

`homography` is a projective map (`ground_homography`), so the whole chain from pixel
to ground is a single homography: every step before it is affine in `(u, v)`. That is
also why the map can be inverted - the migration script that produced the parity data
used the inverse to synthesise cubes at known arena positions.

## Caveats

* **Fixed depth.** `depth_scale` is a constant (~450 mm), so the projection assumes the
  observed point sits at that depth along the optical axis. It is a calibrated
  approximation, not a measurement. A cube very close to the camera is still mapped
  onto the ground plane with a small bias.
* **Installation specific.** The arrays encode the camera height, tilt and mounting
  position on the 2024 robot. Move a camera and they are worthless.
* **float32 in the original.** The 2024 code multiplied by a `float32` depth-scale
  array; this version stays in `float64`. The difference is below 6·10⁻⁵ mm and the
  parity tests allow 10⁻³ mm.
* **Unused arrays are not endorsed.** `projection_matrix.npy` and friends contain the
  raw calibration; they are not sanity-checked against each other here.

## Re-calibrating

There is no calibration tool in this repository. Any standard OpenCV chessboard
workflow that produces the three arrays above (`camera_matrix`, `distortion`, `rvec`,
`tvec`, `R`) can be extended to write the five files the code reads:

1. `newcam_mtx, roi = cv2.getOptimalNewCameraMatrix(camera_matrix, distortion, size, 0)`
   - if `roi` is all zeros in your OpenCV version, use `alpha=0`.
2. `inverse_camera_matrix = np.linalg.inv(newcam_mtx)`.
3. Choose the constant depth `depth_scale` in millimetres.
4. `ground_homography` maps arena-plane `(x, y)` to the robot frame; derive it from the
   known robot-to-floor geometry and store its 3×3 form.
5. `translation = tvec`, `inverse_rotation = np.linalg.inv(R)`.

Then re-run `pytest`; the parity tests will fail until the golden data is regenerated
for the new mounting.
