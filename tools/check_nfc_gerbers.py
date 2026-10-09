#!/usr/bin/env python3
"""Boolean copper/mask comparison of production Gerbers with submitted rev A."""
import argparse,hashlib,json,math
from pathlib import Path
from gerbonara import GerberFile
from gerbonara.utils import approximate_arc, MM
from shapely.geometry import Polygon,box
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parents[1]
REGION=box(9.5,68.5,52,111)  # KiCad (59.5,49)-(102,91.5), translated/flipped origin.

def shape(primitive):
    poly=primitive.to_arc_poly();points=[]
    for p1,p2,(clockwise,center) in poly.segments:
        if clockwise is None:points.append(p1)
        else:
            points.extend(list(approximate_arc(*center,*p1,*p2,clockwise,
                                               max_error=.0001,clip_max_error=True))[:-1])
    return Polygon(points).buffer(0)

def copper(path):
    positive=[];negative=[]
    for obj in GerberFile.open(path).objects:
        (x1,y1),(x2,y2)=obj.bounding_box(MM)
        if not REGION.intersects(box(x1,y1,x2,y2)):continue
        local=Polygon()
        for primitive in obj.to_primitives():
            area=shape(primitive)
            local=local.union(area) if primitive.polarity_dark else local.difference(area)
        (positive if obj.polarity_dark else negative).append(local)
    return unary_union(positive).difference(unary_union(negative)).intersection(REGION)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('export',type=Path);a=ap.parse_args()
    old=ROOT/'manufacturing/jlcpcb-2026-09-21-r2/gerbers';new=a.export/'gerbers'
    baseline_manifest=json.loads((old.parent/'manifest.json').read_text())
    results={}
    for suffix in ['F_Cu.gtl','In1_Cu.g1','In2_Cu.g2','B_Cu.gbl','F_Mask.gts','B_Mask.gbs']:
        name='nucula-v2-'+suffix
        assert hashlib.sha256((old/name).read_bytes()).hexdigest() == baseline_manifest['artifacts_sha256']['gerbers/'+name]
        x,y=copper(old/name),copper(new/name)
        delta=x.symmetric_difference(y).area
        results[suffix]={'difference_mm2':delta,'baseline_area_mm2':x.area,'current_area_mm2':y.area,
                         'passed':delta<1e-7,
                         'baseline_sha256':hashlib.sha256((old/name).read_bytes()).hexdigest(),
                         'current_sha256':hashlib.sha256((new/name).read_bytes()).hexdigest()}
    report={'passed':all(r['passed'] for r in results.values()),'layers':results,
            'region_export_mm':[9.5,68.5,52,111],'curve_approximation_mm':.0001,
            'scope':'Independent Gerber readback against submitted rev-A copper and mask in the frozen NFC area. No EM or material measurements.'}
    (a.export/'validation/nfc-gerber-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
