# -*- coding: utf-8 -*-
from __future__ import annotations
import sys
sys.path.insert(0, "/workspace/ordnungssystem/src")
import FreeCAD as App
import Part
from hausraster_phase3_geom import VEC

pts = [(0.0, 0.0), (0.0, 1.6), (0.0, 13.6), (1.2, 13.6), (1.2, 1.6), (40.0, 1.6), (40.0, 36.6), (80.0, 36.6), (80.0, 71.6), (120.0, 71.6), (120.0, 96.6), (120.0, 0.0)]

def try_face(label, pts_yz):
    verts = [VEC(0, y, z) for y, z in pts_yz]
    verts.append(verts[0])
    wire = Part.makePolygon(verts)
    print(label, "wire closed", wire.isClosed(), "valid", wire.isValid())
    try:
        print("  wire.check", wire.check())
    except Exception as e:
        print("  wire.check exc:", e)
    try:
        face = Part.Face(wire)
        print("  face valid", face.isValid(), "area", face.Area)
        if not face.isValid():
            try:
                print("  face.check", face.check())
            except Exception as e:
                print("  face.check exc:", e)
            face.fix()
            print("  after fix", face.isValid(), "area", face.Area)
        body = face.extrude(VEC(180, 0, 0))
        print("  body valid", body.isValid(), "solids", len(body.Solids), "vol", body.Volume)
        if not body.isValid():
            try:
                print("  body.check", body.check())
            except Exception as e:
                print("  body.check exc:", e)
            b2 = body.removeSplitter()
            print("  removeSplitter", b2.isValid(), b2.Volume)
            b3 = Part.Solid(body)
            print("  Part.Solid", b3.isValid() if b3 else None, getattr(b3,'Volume',None))
    except Exception as e:
        print("  FAIL", type(e), e)

# original
try_face("orig", pts)
# drop colinear (0,1.6)
pts2 = [pts[0]] + pts[2:]
try_face("nocolinear", pts2)
# no lip
pts3 = [(0,0),(0,1.6),(40,1.6),(40,36.6),(80,36.6),(80,71.6),(120,71.6),(120,96.6),(120,0)]
try_face("nolip", pts3)
# reverse nolip
try_face("nolip_rev", list(reversed(pts3)))
# CCW: along floor first
pts4 = [(0,0),(120,0),(120,96.6),(120,71.6),(80,71.6),(80,36.6),(40,36.6),(40,1.6),(0,1.6)]
try_face("ccw", pts4)
