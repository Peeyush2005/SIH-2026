"""Lossless binary-mask mapping for adapters, independent of a model's class claim."""
import numpy as np
import cv2


def decode_binary_mask(mask):
    """Decode our explicit row-major RLE, preserving holes and thin regions."""
    w,h=mask['width'],mask['height'];counts=mask['counts']
    if mask.get('encoding')!='binary_rle_row_major_zero_first' or type(w)!=int or type(h)!=int or not 0<w*h<=30_000_000:
        raise ValueError('Invalid mask encoding or dimensions')
    if any(type(n)!=int or n<0 for n in counts) or sum(counts)!=w*h:raise ValueError('Mask RLE length mismatch')
    return np.repeat(np.arange(len(counts),dtype=np.int64)%2,counts).astype(np.uint8).reshape(h,w)


def map_binary_mask(mask,source_size,*,crop_xyxy,padding_ltrb=(0,0,0,0)):
    """Undo explicit padding/resize then place a tile mask in original pixels."""
    w,h=source_size;x0,y0,x1,y1=map(int,crop_xyxy);l,t,r,b=padding_ltrb
    if not (0<=x0<x1<=w and 0<=y0<y1<=h):raise ValueError('Mask crop outside source')
    a=np.asarray(mask)
    if a.ndim!=2 or not np.isin(a,[0,1,False,True]).all():raise ValueError('Require a binary 2D model mask')
    if min(l,t,r,b)<0 or l+r>=a.shape[1] or t+b>=a.shape[0]:raise ValueError('Invalid mask padding')
    unpadded=a[t:a.shape[0]-b,l:a.shape[1]-r].astype(np.uint8)
    resized=cv2.resize(unpadded,(x1-x0,y1-y0),interpolation=cv2.INTER_NEAREST)
    full=np.zeros((h,w),dtype=np.uint8);full[y0:y1,x0:x1]=resized
    flat=full.ravel();counts=[];last=0;run=0
    for value in flat:
        if value==last:run+=1
        else:counts.append(run);run=1;last=int(value)
    counts.append(run)
    contours,_=cv2.findContours(full,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    polygons=[c[:,0,:].astype(float).tolist() for c in contours if len(c)>=3]
    return {'encoding':'binary_rle_row_major_zero_first','width':w,'height':h,'counts':counts,'polygons':polygons,'coordinate_space':'original_pixels','foreground_pixels':int(full.sum())}
