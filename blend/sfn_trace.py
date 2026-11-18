# Citânia de Sanfins: wall lines traced by eye on the DGT 2021 orthophoto (app/t3/<id>-c.jpg, 4 px/m) and on the LiDAR 2025
# surface model (local metres from the site point PT-TM06 (-21224.03, 183783.55): x east, y north).
# lidar/sfn_lines.py snaps them onto the standing wall (maximum of MDS − MDT) -> blend/sfn_lines.json.
LINES = {
 # rampart enclosing the excavated quarters on the north-west and west, and running south to the lower gate area
 'M1': [(45, 190), (30, 184), (15, 178), (0, 170), (-15, 163), (-30, 155), (-45, 148), (-60, 138), (-75, 128), (-90, 115), (-100, 100), (-103, 85),
        (-102, 70), (-98, 58), (-92, 48), (-84, 38), (-75, 28), (-66, 18), (-58, 8), (-52, -2), (-48, -15), (-45, -30), (-42, -45), (-38, -62),
        (-34, -80), (-30, -100), (-24, -118), (-18, -132), (-14, -142)],
 # long walls of the southern area (outside the excavated quarters)
 'S1': [(-6, -104), (20, -105), (65, -105), (109, -103)],
 'S2': [(36, -51), (43, -81), (48, -111), (53, -146), (58, -181)],
 'S3': [(36, -52), (70, -52), (99, -51)],
}
