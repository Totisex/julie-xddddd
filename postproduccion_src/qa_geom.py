"""Compara la rasante del PDF (vector, medida en pixeles a 400 dpi) con la geometria usada en las laminas."""
import sys; sys.path.insert(0,'.')
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS=None
from scene import VIAS, surf_z
sc=51.0
cfg={1:('v1',432.5),2:('v2',304.5),3:('v3',293.5)}
for vid,(k,x0) in cfg.items():
    v=VIAS[vid]
    a=np.array(Image.open(f'../src/{k}_crop.png').convert('L'))<110
    def center(xm):
        x=int(round(x0+xm*sc)); col=a[650:830,x]; ys=np.where(col)[0]
        runs=[]
        for y in ys:
            if runs and y-runs[-1][1]<=1: runs[-1][1]=y
            else: runs.append([y,y])
        runs=[(r[0]+650,r[1]+650) for r in runs if r[1]-r[0]>=5 and r[1]-r[0]<=9]
        return (runs[0][0]+runs[0][1])/2 if runs else None
    # nivel de calzada en el PDF: carril central
    lane_x=[ (v['xs'][i]+v['xs'][i+1])/2 for i,s_ in enumerate(v['segs']) if s_[0]=='lane'][0]
    y_lane=center(lane_x)
    errs=[]
    for xm in np.arange(0.3,v['L']-0.2,0.2):
        # omitir bordes (+-0.12 m de un limite entre elementos: lineas verticales/bordillos)
        if np.min(np.abs(v['xs']-xm))<0.12: continue
        y=center(xm)
        if y is None: continue
        z_pdf=(y_lane-y)/sc
        errs.append((xm,z_pdf,surf_z(v,xm)))
    e=np.array([abs(b-c) for _,b,c in errs])
    print(f'Via {vid}: {len(e)} muestras  error medio {e.mean()*100:.1f} cm  max {e.max()*100:.1f} cm  (resolucion de medida ~2 cm)')
