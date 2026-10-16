# Decode world-atlas TopoJSON land polygons and rasterize an equirectangular land mask.
import json, sys
import numpy as np
from PIL import Image, ImageDraw

src, out = sys.argv[1], sys.argv[2]
W, H = 3600, 1800
topo = json.load(open(src))
sx, sy = topo["transform"]["scale"]
tx, ty = topo["transform"]["translate"]
arcs = []
for arc in topo["arcs"]:
    x = y = 0
    pts = []
    for dx, dy in arc:
        x += dx; y += dy
        pts.append((x * sx + tx, y * sy + ty))
    arcs.append(pts)

def ring(idx_list):
    pts = []
    for i in idx_list:
        a = arcs[i] if i >= 0 else arcs[~i][::-1]
        pts.extend(a if not pts else a[1:])
    return pts

def proj(lon, lat):
    return ((lon + 180) / 360 * W, (90 - lat) / 180 * H)

img = Image.new("L", (W, H), 0)
d = ImageDraw.Draw(img)
for geom in topo["objects"]["land"]["geometries"]:
    polys = geom["arcs"] if geom["type"] == "MultiPolygon" else [geom["arcs"]]
    for poly in polys:
        for k, r in enumerate(poly):
            raw = ring(r)
            # unwrap longitudes so rings crossing the antimeridian stay contiguous
            un = [raw[0]]
            for lon, lat in raw[1:]:
                prev = un[-1][0]
                while lon - prev > 180: lon -= 360
                while lon - prev < -180: lon += 360
                un.append((lon, lat))
            for off in (-360, 0, 360):
                pts = [proj(lon + off, lat) for lon, lat in un]
                d.polygon(pts, fill=255 if k == 0 else 0)
img.save(out)
print("saved", out, np.asarray(img).mean() / 255)
