"""Class-correct source-pixel IoU matching; scopes are supplied by the caller."""
import numpy as np

def iou(a,b):
    inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter
    return inter/union if union>0 else 0.

def evaluate(items,classes,match_iou=.5):
    counts={str(k):{'class_name':v,'tp':0,'fp':0,'fn':0,'matched_ious':[]} for k,v in classes.items()}
    for item in items:
        truth=item['truth'];used=set()
        for p in sorted(item['predictions'],key=lambda p:-p['score']):
            c=counts[str(p['class_id'])]
            choices=[(iou(p['xyxy'],g['xyxy']),j) for j,g in enumerate(truth) if j not in used and p['class_id']==g['class_id']]
            best=max(choices,default=(0,-1))
            if best[0]>=match_iou:used.add(best[1]);c['tp']+=1;c['matched_ious'].append(best[0])
            else:c['fp']+=1
        for j,g in enumerate(truth):
            if j not in used:counts[str(g['class_id'])]['fn']+=1
    for c in counts.values():
        c['precision']=c['tp']/(c['tp']+c['fp']) if c['tp']+c['fp'] else None
        c['recall']=c['tp']/(c['tp']+c['fn']) if c['tp']+c['fn'] else None
        c['mean_matched_iou']=float(np.mean(c.pop('matched_ious'))) if c['tp'] else None
    totals={k:sum(c[k] for c in counts.values()) for k in ['tp','fp','fn']}
    totals['precision']=totals['tp']/(totals['tp']+totals['fp']) if totals['tp']+totals['fp'] else None
    totals['recall']=totals['tp']/(totals['tp']+totals['fn']) if totals['tp']+totals['fn'] else None
    return {'matching_iou':match_iou,'per_class':counts,'total':totals}
