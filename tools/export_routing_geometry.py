#!/usr/bin/env python3
"""Export KiCad pad, via and trace shapes. Run with pcbnew-enabled Python."""
import pcbnew as k,json,sys
from pathlib import Path
import argparse, hashlib
ROOT=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser(description='Export physical copper geometry for the independent routing-quality audit.')
ap.add_argument('--board',type=Path,default=ROOT/'nucula-v2.kicad_pcb')
ap.add_argument('--out',type=Path,default=ROOT/'docs/pcb/routing-geometry.json')
a=ap.parse_args();b=k.LoadBoard(str(a.board))
layers=[k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu]
def xy(v):return [v.x/1e6,v.y/1e6]
def polygons(o):
 return [[xy(o.Outline(i).CPoint(j)) for j in range(o.Outline(i).PointCount())] for i in range(o.OutlineCount())]
items=[]
for f in b.GetFootprints():
 for q in f.Pads():
  ls=[i for i,l in enumerate(layers) if q.IsOnLayer(l)]
  if not ls:continue
  poly=k.SHAPE_POLY_SET();q.TransformShapeToPolygon(poly,k.F_Cu,0,2000,k.ERROR_OUTSIDE)
  items.append({'id':q.m_Uuid.AsString(),'type':'pad','ref':f.GetReference(),'num':q.GetNumber(),'net':q.GetNetname(),'layers':ls,'xy':xy(q.GetPosition()),'poly':polygons(poly),'drill':xy(q.GetDrillSize()),'smd':q.GetAttribute()==k.PAD_ATTRIB_SMD,'exposed':q.IsOnLayer(k.F_Mask), 'size':xy(q.GetSize()),'angle':q.GetOrientationDegrees(),'shape':q.GetShape(),'mask_margin':k.ToMM(q.GetLocalSolderMaskMargin()) if q.GetLocalSolderMaskMargin() is not None else 0})
for t in b.GetTracks():
 v=isinstance(t,k.PCB_VIA)
 items.append({'id':t.m_Uuid.AsString(),'type':'via' if v else 'track','net':t.GetNetname(),'layers':list(range(4)) if v else [layers.index(t.GetLayer())],'xy':xy(t.GetPosition()),'start':xy(t.GetStart()),'end':xy(t.GetEnd()),'w':k.ToMM(t.GetWidth(k.F_Cu) if v else t.GetWidth()),'drill':k.ToMM(t.GetDrillValue()) if v else 0,'locked':t.IsLocked()})
rules=[]
for z in list(b.Zones())+[z for f in b.GetFootprints() for z in f.Zones()]:
 if z.GetIsRuleArea():rules.append({'name':z.GetZoneName(),'layers':[i for i,l in enumerate(layers) if z.IsOnLayer(l)],'poly':polygons(z.Outline()),'tracks':z.GetDoNotAllowTracks(),'vias':z.GetDoNotAllowVias(),'pours':z.GetDoNotAllowZoneFills()})
outline=k.SHAPE_POLY_SET();b.GetBoardPolygonOutlines(outline,False)
a.out.write_text(json.dumps({'source_board_sha256':hashlib.sha256(a.board.read_bytes()).hexdigest(),'items':items,'rules':rules,'outline':polygons(outline)},separators=(',',':'))+'\n')
print(len(items),'copper objects')
