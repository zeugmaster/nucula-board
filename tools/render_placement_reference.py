#!/usr/bin/env python3
"""Draw actual source copper and native CPL anchors for supplier alignment."""
import argparse,csv,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from kicad_sexpr import parse,children,child,uq
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('export',type=Path);a=ap.parse_args()
    geometry=json.loads((ROOT/'docs/pcb/routing-geometry.json').read_text())
    cpl={r['Designator']:r for r in csv.DictReader((a.export/'assembly/jlcpcb-cpl.csv').open())}
    fig,axes=plt.subplots(3,2,figsize=(11.7,16.5),layout='constrained')
    for ax,ref in zip(axes.flat,['U3','DS1','J2','U6','U4','U10']):
        pads=[p for p in geometry['items'] if p['type']=='pad' and p['ref']==ref and 0 in p['layers']]
        bounds=[]
        for p in pads:
            for poly in p['poly']:
                points=[(x-50,160-y) for x,y in poly];bounds+=points
                ax.add_patch(Polygon(points,facecolor='#dfbd69',edgecolor='#66511d',linewidth=.5))
            x,y=p['xy'][0]-50,160-p['xy'][1]
            ax.text(x,y,p['num'],ha='center',va='center',fontsize=6,color='#152e3b',weight='bold')
            if p['num']=='1':ax.scatter([x],[y],s=100,facecolors='none',edgecolors='#d03f32',linewidths=1.2)
        row=cpl[ref];x,y=float(row['Mid X']),float(row['Mid Y'])
        ax.scatter([x],[y],marker='+',s=170,color='#d03f32',linewidths=1.5,zorder=8)
        xs=[p[0] for p in bounds]+[x];ys=[p[1] for p in bounds]+[y]
        ax.set(xlim=(min(xs)-.8,max(xs)+.8),ylim=(min(ys)-.8,max(ys)+.8),
               aspect='equal',xlabel='CPL X (mm)',ylabel='CPL Y (mm)',
               title=f'{ref}  |  anchor ({x:.4f}, {y:.4f}) mm  |  {float(row["Rotation"]):g}° top')
        ax.grid(alpha=.15);ax.tick_params(labelsize=7)
    fig.suptitle('Placement reference — source PCB copper, top view\nRed + = native KiCad/CPL anchor; red circle = pad 1. Align supplier leads to numbered pads.\nDo not translate anchors to body centers. Positive Y points up; origin KiCad (50,160) mm.',fontsize=12)
    for suffix in ['pdf','png']:fig.savefig(a.export/'drawings'/('placement-reference.'+suffix),dpi=180)
    plt.close(fig)
if __name__=='__main__':main()
