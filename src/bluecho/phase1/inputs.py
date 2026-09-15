"""Decoded images, georeferenced rasters and bounded streaming XTF windows."""
from datetime import datetime,timezone
import ctypes
import io
import json
from pathlib import Path
import struct
import time
import numpy as np
from PIL import Image
from bluecho.engine import InputError,read_image,SUFFIXES
from .download import digest,atomic_json
from .geography import load_sidecar


def xtf_packets(path):
    """Use existing pyxtf structures without its automatic pickle-index loader."""
    import pyxtf
    from pyxtf.xtf_ctypes import XTFPacketClasses,XTFUnknownPacket
    path=Path(path);size=path.stat().st_size
    with path.open('rb') as f:
        header=pyxtf.XTFFileHeader.create_from_buffer(f)
        if header.FileFormat!=123:raise InputError('Invalid XTF file signature')
        if header.channel_count()>6:raise InputError('XTF with more than six channels is unsupported')
        yield header,None,None
        while f.tell()<size:
            pos=f.tell();prefix=f.read(14)
            if len(prefix)!=14 or struct.unpack_from('<H',prefix)[0]!=0xFACE:raise InputError(f'Invalid/truncated XTF packet at byte {pos}')
            length=struct.unpack_from('<I',prefix,10)[0]
            if not 14<=length<=32*1024**2 or pos+length>size:raise InputError(f'Invalid XTF packet size at byte {pos}')
            # Only sonar packets are decoded; preserve other record boundaries.
            if prefix[2]==0:
                f.seek(pos)
                payload=io.BytesIO(f.read(length))
                try:packet=pyxtf.XTFPingHeader.create_from_buffer(payload,file_header=header)
                except (ValueError,RuntimeError,IndexError,KeyError) as exc:raise InputError(f'Invalid XTF sonar payload at byte {pos}: {exc}') from exc
                if payload.tell()>length:raise InputError('XTF decoded beyond packet boundary')
                yield header,packet,pos
            f.seek(pos+length)


def xtf_info(path):
    g=xtf_packets(path);h,_,_=next(g)
    data={'format':'XTF','nav_units_code':int(h.NavUnits),'navigation_datum_text':bytes(h.SpheriodType).rstrip(b'\0').decode(errors='replace'),'projection_text':bytes(h.ProjectionType).rstrip(b'\0').decode(errors='replace'),'channels':[{'channel':i,'type_code':int(c.TypeOfChannel),'side':{1:'port',2:'starboard'}.get(c.TypeOfChannel),'frequency_khz':float(c.Frequency),'bytes_per_sample':int(c.BytesPerSample)} for i,c in enumerate(h.ChanInfo[:h.NumberOfSonarChannels])],'index_pickle_used':False}
    try:
        _,p,offset=next(g);data['first_ping']={'ping_index':int(p.PingNumber),'packet_offset':offset,'samples':[int(c.NumSamples) for c in p.ping_chan_headers]}
    except StopIteration:raise InputError('XTF contains no supported sonar packets')
    finally:g.close()
    return data


def inspect_input(path):
    path=Path(path).resolve()
    if not path.is_file():raise InputError('Input file does not exist')
    if path.stat().st_size>2*1024**3:raise InputError('Input exceeds 2 GiB per-file limit; select a recording segment')
    info={'path':str(path),'name':path.name,'bytes':path.stat().st_size,'sha256':digest(path)}
    if path.suffix.lower()=='.xtf':return {**info,**xtf_info(path),'modality':'SSS','model_sensor_transfer':'unvalidated'}
    if path.suffix.lower() not in SUFFIXES:raise InputError('Supported inputs: decoded images, GeoTIFF and XTF; no advertised SL2/ARIS decoder in this phase')
    image=read_image(path);info.update(format='decoded_image',width=image.width,height=image.height,modality=None)
    if path.suffix.lower() in ('.tif','.tiff'):
        import rasterio
        with rasterio.open(path) as ds:
            if ds.crs:info.update(format='georeferenced_raster',crs=str(ds.crs),transform=list(ds.transform)[:6],nodata=ds.nodata,positioning_scope=ds.tags().get('positioning_scope','Supplied raster transform, accuracy unvalidated'))
    return info


def decoded_input(path,out,modality,sidecar=None):
    path=Path(path).resolve();out=Path(out);out.mkdir(parents=True,exist_ok=True)
    info=inspect_input(path);image=read_image(path)
    if not modality:raise InputError('Declare sonar modality; it cannot be inferred from an ordinary image')
    metadata=None
    if sidecar:metadata=load_sidecar(sidecar,path,image.width,image.height)
    elif info['format']=='georeferenced_raster':
        metadata={'schema_version':'1.0','source_sha256':info['sha256'],'image_width':image.width,'image_height':image.height,'modality':modality,'mapping':'affine','crs':info['crs'],'transform':info['transform'],'assumptions':['Pixel georeferencing is supplied by the raster; real positioning accuracy is not independently validated.'],'metadata_provenance':{'source':path.name,'sha256':info['sha256'],'input_provenance':'embedded_geotiff_transform'},'pixel_convention':'pixel_edge'}
    if metadata and metadata.get('modality')!=modality:raise InputError('Sidecar modality differs from selected input modality')
    if metadata and info.get('positioning_scope'):metadata['positioning_scope']=info['positioning_scope']
    nodata_rows=[]
    if info['format']=='georeferenced_raster':
        import rasterio
        with rasterio.open(path) as ds:
            mask=ds.dataset_mask();nodata_rows=np.where(np.all(mask==0,axis=1))[0].tolist()
    image.save(out/'original.png')
    return {'image_path':out/'original.png','original_source':str(path),'source_sha256':info['sha256'],'modality':modality,'metadata':metadata,'reference':{'file':path.name,'channel':None,'ping_start':None,'ping_end':None,'sample_start':0,'sample_end':image.width},'invalid_rows':nodata_rows,'coverage':{'complete_input':True,'unassessed':[]},'decoding':{'method':'unchanged decoded uint8 RGB','georeferencing':info.get('crs')}}


def xtf_windows(path,out,*,channel,start_ping=0,max_pings=128,chunk_pings=128,nav_crs=None,progress=None):
    """Yield unchanged sample geometry. max_pings=0 scans all supported pings."""
    if channel is None:raise InputError('XTF requires an explicit --channel selection from inspect-input')
    if not 1<=chunk_pings<=512 or max_pings<0 or start_ping<0:raise InputError('Invalid ping window limits')
    path=Path(path).resolve()
    if path.stat().st_size>2*1024**3:raise InputError('Input exceeds 2 GiB per-file limit')
    out=Path(out);out.mkdir(parents=True,exist_ok=True);source_hash=digest(path)
    info=xtf_info(path);match=next((c for c in info['channels'] if c['channel']==channel),None)
    if not match or match['side'] not in ('port','starboard'):raise InputError('Choose a supported port/starboard XTF sonar channel')
    # XTF NavUnits=3 says degrees, not a datum. No silent WGS84 assumption.
    if nav_crs:
        from pyproj import CRS
        crs=CRS.from_user_input(nav_crs)
        if info['nav_units_code']==3 and not crs.is_geographic:raise InputError('XTF navigation is in degrees; projected CRS is incompatible')
    scanned=selected=0;rows=[];records=[];index=0;last_shape=None;g=xtf_packets(path);h,_,_=next(g);exhausted=True
    def emit(complete=False):
        nonlocal rows,records,index
        if not rows:return None
        dest=out/f'window_{index:04d}';dest.mkdir(exist_ok=True)
        array=np.stack(rows);image=np.clip(array.astype(np.float64)/np.iinfo(array.dtype).max*255,0,255).astype(np.uint8)
        Image.fromarray(image).convert('RGB').save(dest/'original.png')
        np.savez_compressed(dest/'raw_samples.npz',samples=array)
        metadata={'schema_version':'1.0','source_sha256':source_hash,'image_width':array.shape[1],'image_height':array.shape[0],'modality':'SSS','mapping':'ping_rows','pings':records,'assumptions':['XTF sensor heading used as true heading; no independent attitude/navigation accuracy reference','Navigation CRS explicitly supplied by caller: '+str(nav_crs)],'raw_source':path.name}
        atomic_json(dest/'decoded_metadata.json',metadata)
        result={'image_path':dest/'original.png','original_source':str(path),'source_sha256':source_hash,'modality':'SSS','metadata':metadata,'reference':{'file':path.name,'channel':channel,'ping_start':records[0]['ping_index'],'ping_end':records[-1]['ping_index'],'sample_start':0,'sample_end':array.shape[1],'window_index':index},'invalid_rows':[],'coverage':{'complete_input':complete and start_ping==0 and index==0,'unassessed':['Other sonar channels not selected','All pings outside this explicit window; see recording index for aggregate coverage'],'selected_pings':len(records)},'decoding':{'method':'uint16/uint8 full-scale linear display; raw samples preserved separately','dtype':str(array.dtype),'display_min':0,'display_max':int(np.iinfo(array.dtype).max),'original_pixel_geometry':'one row per selected ping; one column per stored sample, near-to-far','frequency_khz':match['frequency_khz'],'raw_samples':'raw_samples.npz','transfer_evidence':'new sensor/frequency/display; model accuracy unvalidated'}}
        rows=[];records=[];index+=1;return result
    try:
        for _,p,offset in g:
            if scanned<start_ping:scanned+=1;continue
            if max_pings and selected>=max_pings:exhausted=False;break
            scanned+=1
            pair=next(((ch,data) for ch,data in zip(p.ping_chan_headers,p.data) if int(ch.ChannelNumber)==channel),None)
            if pair is None:continue
            ch,data=pair
            if data.dtype.kind!='u' or data.dtype.itemsize not in (1,2):raise InputError('XTF sample dtype is unsupported; select an explicit decoding policy')
            if not 0<len(data)<=32768:raise InputError('Invalid or unsupported XTF sample count')
            if rows and (len(data),data.dtype.str)!=last_shape:
                yield emit()
            if rows and int(p.PingNumber)<=records[-1]['ping_index']:raise InputError('Non-increasing ping IDs; recording requires explicit segment selection')
            if rows and int(p.PingNumber)>records[-1]['ping_index']+1:
                # Preserve time gaps in metadata rather than inventing sampled rows.
                records[-1]['quality_flags']=['following_ping_gap']
            try:stamp=datetime(int(p.Year),int(p.Month),int(p.Day),int(p.Hour),int(p.Minute),int(p.Second),int(p.HSeconds)*10000,tzinfo=timezone.utc).isoformat()
            except ValueError:stamp=None
            sx,sy=float(p.SensorXcoordinate),float(p.SensorYcoordinate)
            navvalid=bool(nav_crs and np.isfinite([sx,sy]).all() and (sx!=0 or sy!=0))
            record={'row':len(rows),'ping_index':int(p.PingNumber),'packet_offset_bytes':offset,'channel':channel,'timestamp':stamp,'timestamp_reference':'XTF date/time interpreted as UTC; real clock accuracy unvalidated','sensor_position':{'x':sx,'y':sy,'crs':nav_crs,'reference':'sonar_sensor','valid':navvalid},'vessel_position_raw':{'x':float(p.ShipXcoordinate),'y':float(p.ShipYcoordinate)},'heading_degrees':float(p.SensorHeading)%360,'heading_reference':'true_north','side':match['side'],'range_start':0.,'range_end':float(ch.SlantRange),'range_unit':'m','range_geometry':'slant','sample_count':len(data),'sample_direction':'near_to_far','altitude':float(p.SensorPrimaryAltitude) if p.SensorPrimaryAltitude>0 else None,'altitude_unit':'m','altitude_reference':'seabed','sensor_depth_below_surface_m':float(p.SensorDepth),'time_delay_seconds':float(ch.TimeDelay),'time_duration_seconds':float(ch.TimeDuration)}
            if record['time_delay_seconds']!=0:
                record['range_start']=None;record['quality_flags']=['nonzero_time_delay_requires_range_origin_resolution']
            rows.append(data.copy());records.append(record);last_shape=(len(data),data.dtype.str);selected+=1
            if progress:progress(selected,max_pings or None)
            if len(rows)>=chunk_pings:yield emit()
        if rows:yield emit(complete=exhausted)
    finally:
        g.close()
        atomic_json(out/'partial_coverage.json',{'source_sha256':source_hash,'selected_channel':channel,'start_ping_ordinal':start_ping,'decoded_selected_pings':selected,'emitted_windows':index,'status':'decoding_receipt_not_inference_completion','other_channels':'unassessed','unprocessed':'See recording.json for completed inference windows; remaining requested extent may be unprocessed'})
    if not selected:raise InputError('No sonar pings selected')
    atomic_json(out/'recording_coverage.json',{'source_sha256':source_hash,'selected_channel':channel,'start_ping_ordinal':start_ping,'selected_pings':selected,'windows':index,'read_to_end':exhausted,'other_channels':'unassessed','position_crs_override':nav_crs,'accuracy':'unvalidated sensor/model transfer and geographical accuracy'})
