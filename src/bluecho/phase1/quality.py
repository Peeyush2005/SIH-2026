"""Recording quality observations, never a class or material decision."""
import numpy as np
from PIL import Image,ImageDraw
from .geography import geotag_box


def assess_quality(image,*,invalid_rows=(),metadata=None,coverage=None):
    a=np.asarray(image.convert('L'));h,w=a.shape;invalid=set(invalid_rows)
    if any(type(r)!=int or not 0<=r<h for r in invalid):raise ValueError('Invalid row references')
    regions=[]
    def add(kind,rows,evidence,confidence):
        if not rows:return
        runs=[];start=previous=rows[0]
        for y in rows[1:]:
            if y!=previous+1:runs.append((start,previous+1));start=y
            previous=y
        runs.append((start,previous+1))
        for y0,y1 in runs:
            box=[0,y0,w,y1]
            regions.append({'flag':kind,'box_xyxy_pixels':box,'evidence':evidence,'assessment':confidence,'position':geotag_box(box,metadata),'recommendation':'Review source coverage and consider rescanning this interval if confirmed unusable; this is not a navigation plan'})
    add('invalid_or_missing_rows',sorted(invalid),'Explicit raw validity record or raster no-data mask','demonstrated_invalid')
    saturated=np.where(np.mean(a>=254,axis=1)>=.98)[0].tolist()
    add('high_end_saturation',saturated,'At least 98% of displayed row samples are >=254/255','display_observation_not_physical_cause')
    low=np.where((np.max(a,axis=1)<=1)&(~np.isin(np.arange(h),list(invalid))))[0].tolist()
    add('uniform_low_signal_uncertain',low,'Entire displayed row <=1/255; can include legitimate margins or shadows','uncertain_not_missing_data')
    rowmeans=a.mean(axis=1);striped=np.where((np.abs(np.diff(rowmeans,prepend=rowmeans[0]))>80)&(np.std(a,axis=1)<12))[0].tolist()
    add('strong_row_striping_uncertain',striped,'Row mean changes >80 display levels and within-row standard deviation <12; cause unresolved','display_observation_not_dropout')
    if metadata and metadata.get('mapping')=='ping_rows':
        gaps=[r['row'] for r in metadata['pings'] if 'following_ping_gap' in r.get('quality_flags',[])]
        add('following_ping_gap',gaps,'Explicit nonconsecutive stored ping identifiers; no synthetic rows inserted','unassessed_gap')
    summary={'invalid_rows':len(invalid),'saturated_rows':len(saturated),'uncertain_low_signal_rows':len(low),'saturated_pixel_fraction':float(np.mean(a>=254)),'regions':regions,'coverage':coverage or {'complete_input':True,'unassessed':[]},'policy':'No quality-based rejection of detections. Dark shadows are not treated as missing rows. Originals remain unchanged.'}
    overlay=image.convert('RGB').copy();draw=ImageDraw.Draw(overlay)
    for r in regions:
        color={'invalid_or_missing_rows':'red','high_end_saturation':'orange','uniform_low_signal_uncertain':'purple','following_ping_gap':'cyan','strong_row_striping_uncertain':'yellow'}[r['flag']]
        x0,y0,x1,y1=r['box_xyxy_pixels'];draw.rectangle((x0,y0,x1-1,max(y0,y1-1)),outline=color,width=2)
    return summary,overlay


def corruption(image,truth,kind,seed=42):
    """Frozen synthetic diagnostic; motion boxes are transformed as envelopes."""
    a=np.asarray(image.convert('RGB'));h,w=a.shape[:2];rng=np.random.default_rng(seed)
    boxes=[{**b,'xyxy':list(b['xyxy'])} for b in truth];invalid=[]
    if kind=='speckle':out=np.clip(a*rng.lognormal(-.2**2/2,.2,(h,w,1)),0,255).astype(np.uint8)
    elif kind=='intensity':out=np.rint(a*.65).astype(np.uint8)
    elif kind=='resolution':out=np.asarray(image.resize((max(1,w//2),max(1,h//2)),Image.Resampling.BILINEAR).resize((w,h),Image.Resampling.BILINEAR))
    elif kind=='row_dropout':
        out=a.copy();invalid=list(range(h//3,min(h,h//3+max(1,h//20))));out[invalid]=0
    elif kind=='motion':
        shifts=np.rint(6*np.sin(2*np.pi*np.arange(h)/max(1,h))).astype(int);out=np.zeros_like(a)
        for y,dx in enumerate(shifts):
            if dx>=0:out[y,dx:]=a[y,:w-dx]
            else:out[y,:w+dx]=a[y,-dx:]
        for b in boxes:
            x0,y0,x1,y1=b['xyxy'];ys=shifts[max(0,int(np.floor(y0))):min(h,int(np.ceil(y1)))]
            b['xyxy']=[float(max(0,x0+ys.min())),y0,float(min(w,x1+ys.max())),y1]
    else:raise ValueError('Unknown frozen corruption')
    return Image.fromarray(out),boxes,invalid
