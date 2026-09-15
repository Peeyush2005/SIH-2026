"""Offline schematic vector view; deliberately no accuracy or basemap claims."""
import html

def render_vectors(candidates,tracks,path):
    points=[]
    for group,color in [(tracks,'#667788'),(candidates,'#007eaa')]:
        for f in group:
            g=f.get('geometry')
            if g and g['type']=='Point':points.append((g['coordinates'],color,str(f['properties'].get('candidate_id',f['properties'].get('kind','track')))))
    body=[]
    if points:
        xs=[p[0][0] for p in points];ys=[p[0][1] for p in points];left,right=min(xs),max(xs);bottom,top=min(ys),max(ys);dx=max(right-left,1e-6);dy=max(top-bottom,1e-6)
        for (x,y),color,label in points:body.append(f'<circle cx="{40+720*(x-left)/dx:.3f}" cy="{440-380*(y-bottom)/dy:.3f}" r="5" fill="{color}"><title>{html.escape(label)}</title></circle>')
        body.append(f'<text x="20" y="485">WGS84 lon {left:.6f} … {right:.6f}; lat {bottom:.6f} … {top:.6f}. Schematic axes, not a distance scale.</text>')
    else:body.append('<text x="30" y="240">No geographic geometry available. All image detections remain in JSON/CSV/GeoJSON.</text>')
    path.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 510"><rect width="800" height="510" fill="#eef4f8"/><g font-family="sans-serif" font-size="12">'+''.join(body)+'</g></svg>')
