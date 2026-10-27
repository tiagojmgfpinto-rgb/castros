# Builds lidar/mdt.npy and lidar/mds.npy (Citânia de Briteiros) from the DGT LiDAR 2025 sheets in lidar/raw:
# sheets 184507 | 185507 side by side → array covering PT-TM06 x −16000…−14000, y 206000…207000 at 0.5 m (row 0 = north).
import numpy as np, rasterio
R = 'lidar/raw/{}-50cm-{}-07-2025_v02.tif'
for kind, out in (('MDT', 'lidar/mdt.npy'), ('MDS', 'lidar/mds.npy')):
    A = np.hstack([rasterio.open(R.format(kind, t)).read(1) for t in ('184507', '185507')]).astype(np.float32)
    np.save(out, A); print(out, A.shape)
