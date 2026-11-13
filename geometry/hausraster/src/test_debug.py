import sys
sys.path.insert(0, "/workspace/ordnungssystem/src")
import FreeCAD as App
import Part
from hausraster_const import default_params, FUSS_PROFIL_HOEHE, LIPPE_HOEHE
from hausraster_geom import (
    make_plate_shape, make_box_shape, make_fuss_stumpf_shape,
    einzel_fuss, _stapel_lippe, loft_sections, _innen_hohlraum,
    seated_box_z_on_plate, plate_outer_size, box_outer_size, _r_ok,
    kasten_aussen,
)
from hausraster_const import ECKENRADIUS_BOX_OBEN

def bb(name, sh):
    b = sh.BoundBox
    print("  %s: type=%s solids=%d valid=%s vol=%.2f  size=%.3fx%.3fx%.3f  z=[%.3f,%.3f] xy=[%.3f..%.3f, %.3f..%.3f]" % (
        name, sh.ShapeType, len(sh.Solids), sh.isValid(), sh.Volume or 0,
        b.XLength, b.YLength, b.ZLength, b.ZMin, b.ZMax, b.XMin, b.XMax, b.YMin, b.YMax))

p = default_params(Einheiten_X=1, Einheiten_Y=1, Verbinder=0, Verriegelung=0)
plate = make_plate_shape(p)
bb("platte", plate)
soll = plate_outer_size(p)
print("  soll", soll)

# Slice widths
for z in (0.8, 1.5, 2.4, 3.3, 5.0, 5.4):
    sl = plate.slice(App.Vector(0,0,1), z)
    print("  slice z=%.2f  n=%d" % (z, len(sl)))
    for i,w in enumerate(sl):
        b=w.BoundBox
        print("    wire%d  %.3f x %.3f" % (i, b.XLength, b.YLength))

print("---- box parts ----")
pb = default_params(Einheiten_X=1, Einheiten_Y=1, Einheiten_Z=3, Stapellippe=1)
nx,ny,ez=1,1,3
wand=1.2
spiel=0.0
raster=42.0
aussen=kasten_aussen(1,0)
r_aussen=_r_ok(aussen,aussen,3.75)
z_fuss=FUSS_PROFIL_HOEHE
z_boden=z_fuss+2.25
z_wand=21.0
fuss=einzel_fuss(0,0,41.5,3.75,0)
bb("fuss", fuss)
korpus=loft_sections([(z_fuss,aussen,aussen,r_aussen),(z_wand,aussen,aussen,r_aussen)])
bb("korpus", korpus)
box=fuss.fuse(korpus)
bb("fuss+korpus", box)
innen=aussen-2*wand
r_innen=_r_ok(innen,innen,2.0)
hohl=_innen_hohlraum(innen,innen,z_boden,z_wand+LIPPE_HOEHE,r_innen)
bb("hohl", hohl)
box=box.cut(hohl)
bb("nach hohl", box)
lippe=_stapel_lippe(aussen,aussen,r_aussen,z_wand,wand,innen,innen,r_innen)
bb("lippe", lippe)
box2=box.fuse(lippe)
bb("box+lippe", box2)
print("soll box", box_outer_size(pb))

# XY gap with 1 mm lift
z = 0.8
fuss2=fuss.copy(); fuss2.translate(App.Vector(0,0,z+1.0))
print("dist after 1mm lift", plate.distToShape(fuss2)[0])
