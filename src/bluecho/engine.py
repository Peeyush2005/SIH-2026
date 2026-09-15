"""One implementation for the Python API, CLI and local web adapter."""
from __future__ import annotations
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path
import numpy as np
from PIL import Image, UnidentifiedImageError
from .geometry import crops, render_tile, map_box, merge_nms

# The pinned detector library patches Image.open to try optional HEIF plugins on
# decode failures. This image-only service keeps Pillow's original decoder so an
# invalid upload remains an input error, without optional imports or downloads.
_pillow_open = getattr(sys.modules.get('ultralytics.utils.patches'), '_image_open', Image.open)

SCHEMA_VERSION = '1.0.0'
PREPROCESSING_VERSION = 'phase2b-rgb255-640-s480-v1'
SUFFIXES = {'.png', '.pbm', '.bmp', '.jpg', '.jpeg', '.tif', '.tiff'}


class InputError(ValueError):
    pass


class ModelError(ValueError):
    pass


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def local_path(root, value):
    if not isinstance(value, str) or '\\' in value or ':' in value:
        raise ModelError('Model artifact must be a relative local path')
    relative = Path(value)
    if relative.is_absolute() or '..' in relative.parts:
        raise ModelError('Model artifact path escapes the release')
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ModelError('Model artifact path escapes the release')
    if not path.is_file():
        raise ModelError(f'Model artifact missing: {value}; install the approved release locally')
    return path


def read_image(path, max_pixels=30_000_000):
    path = Path(path)
    if not path.is_file():
        raise InputError(f'Image file does not exist: {path.name}')
    if path.suffix.lower() not in SUFFIXES:
        raise InputError('Unsupported input; use PNG, PBM, BMP, JPEG or 8-bit TIFF. Raw sonar is unsupported.')
    try:
        with _pillow_open(path, formats=['PNG', 'PPM', 'BMP', 'JPEG', 'TIFF']) as source:
            if source.width * source.height > max_pixels:
                raise InputError(f'Image exceeds the {max_pixels} pixel limit')
            if getattr(source, 'n_frames', 1) != 1:
                raise InputError('Multiple-frame images are unsupported; select an explicit frame')
            if source.mode not in ('1', 'L', 'RGB', 'P', 'RGBA'):
                raise InputError(f'Unsupported pixel mode {source.mode}; require 8-bit image without intensity rescaling')
            if source.mode == 'RGBA' and source.getextrema()[3] != (255, 255):
                raise InputError('Transparent images are unsupported; provide an opaque sonar image')
            if 'transparency' in source.info:
                raise InputError('Palette transparency is unsupported; provide an opaque sonar image')
            source.load()
            return source.convert('RGB')
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise InputError(f'Cannot decode image: {path.name}') from exc


class Engine:
    def __init__(self, manifest, device='cpu', backend='native'):
        manifest = Path(manifest).resolve()
        if not manifest.is_file():
            raise ModelError('Release manifest missing; supply a local manifest.json')
        self.manifest = json.loads(manifest.read_text())
        self.root = manifest.parent
        m = self.manifest
        if m.get('schema_version') != SCHEMA_VERSION:
            raise ModelError('Unsupported model manifest schema')
        if m.get('modality') != 'SSS_LF' or m.get('classes') != {'0': 'Pipeline'}:
            raise ModelError('This release supports only the bound SSS_LF Pipeline model')
        self.prep = m['preprocessing']; self.protocol = m['inference']; self.thresholds = m['thresholds']
        if (self.prep.get('tile_size'), self.prep.get('stride'), self.prep.get('padding_rgb'), self.prep.get('mode')) != (640, 480, [114, 114, 114], 'tiles'):
            raise ModelError('Unsupported preprocessing geometry')
        if self.prep.get('scale') != 1.0 or self.prep.get('intensity') != 'Preserve source uint8 RGB /255; no stretching/filtering':
            raise ModelError('Unsupported intensity normalization')
        if m.get('preprocessing_version') != PREPROCESSING_VERSION or set(self.thresholds) != {'0'}:
            raise ModelError('Missing or incompatible preprocessing/threshold binding')
        if any(type(v) not in (int,float) or not math.isfinite(v) or not 0 <= v <= 1 for v in self.thresholds.values()):
            raise ModelError('Invalid frozen score threshold')
        if backend not in ('native', 'onnx'):
            raise ModelError('Use native or onnx backend')
        if backend == 'onnx' and m.get('onnx', {}).get('status') != 'PASS':
            raise ModelError('ONNX is not verified for this release; use native')
        artifact = m[backend]
        weights = local_path(self.root, artifact['path'])
        if sha256(weights) != artifact['sha256']:
            raise ModelError('Model checksum mismatch; reinstall the approved model file')
        self.device = str(device)
        if self.device.isdigit():
            self.device = 'cuda:' + self.device
        if self.device != 'cpu' and not (self.device.startswith('cuda:') and self.device[5:].isdigit()):
            raise ModelError('Use explicit cpu or cuda:N device')
        self.backend = backend; self.model_hash = artifact['sha256']
        # No network dependency, autoinstall or name-based weight resolution.
        os.environ['YOLO_AUTOINSTALL'] = 'False'
        os.environ['YOLO_OFFLINE'] = 'True'
        os.environ['DO_NOT_TRACK'] = '1'
        os.environ.setdefault('OMP_NUM_THREADS', '4')
        import torch
        torch.set_num_threads(4)
        if backend == 'native':
            from ultralytics import YOLO
            self.model = YOLO(str(weights)).model.float().to(torch.device(self.device)).eval()
            self.model.fuse(verbose=False)
            if {str(k): v for k, v in self.model.names.items()} != m['classes']:
                raise ModelError('Checkpoint class map differs from the manifest')
        else:
            if self.device != 'cpu':
                raise ModelError('ONNX is verified on CPU only; choose native for GPU')
            import onnxruntime as ort
            opts = ort.SessionOptions(); opts.intra_op_num_threads = 4
            self.session = ort.InferenceSession(str(weights), sess_options=opts, providers=['CPUExecutionProvider'])
            self.input_name = self.session.get_inputs()[0].name

    def info(self):
        return {**self.manifest, 'loaded_device': self.device, 'loaded_backend': self.backend,
                'raw_xtf': False, 'raw_aris': False, 'raw_sl2': False, 'geolocation': False,
                'metric_dimensions': False, 'material_identification': False}

    def tile(self, image):
        import torch
        from ultralytics.utils.nms import non_max_suppression
        x = np.ascontiguousarray(np.asarray(image.convert('RGB')).transpose(2, 0, 1)[None]).astype(np.float32)/255.
        if self.backend == 'native':
            with torch.inference_mode():
                pred = self.model(torch.from_numpy(x).to(self.device))
                raw = (pred[0] if isinstance(pred, (tuple, list)) else pred).cpu()
        else:
            raw = torch.from_numpy(self.session.run(None, {self.input_name: x})[0])
        if not torch.isfinite(raw).all():
            raise FloatingPointError('Model produced nonfinite output')
        out = non_max_suppression(raw.clone(), conf_thres=self.protocol['score_floor'],
                iou_thres=self.protocol['tile_nms_iou'], nc=1,
                max_det=self.protocol['max_det_per_tile'], max_time_img=10.)[0]
        boxes = []
        for a, b, c, d, score, cls in out.numpy():
            a, c = np.clip([a, c], 0, image.width); b, d = np.clip([b, d], 0, image.height)
            if c > a and d > b:
                boxes.append({'xyxy': [float(a), float(b), float(c), float(d)], 'score': float(score),
                              'class_id': int(cls), 'class_name': self.manifest['classes'][str(int(cls))]})
        return boxes

    def original_raw(self, path, progress=None):
        start = time.perf_counter(); rgb = read_image(path); width, height = rgb.size
        windows = crops(width, height); boxes = []; tiles = []
        for k, crop in enumerate(windows):
            predictions = self.tile(render_tile(rgb, crop))
            tiles.append({'tile_index': k, 'crop_xyxy': crop, 'predictions': predictions})
            for box in predictions:
                mapped = map_box(box['xyxy'], crop)
                if mapped[2] > mapped[0] and mapped[3] > mapped[1]:
                    boxes.append({**box, 'xyxy': mapped, 'tile_index': k})
            if progress:
                progress(k+1, len(windows))
        return {'original_size': [width, height], 'tile_count': len(windows), 'tiles': tiles,
                'predictions': merge_nms(boxes, self.protocol['source_nms_iou']),
                'end_to_end_seconds': time.perf_counter()-start}

    def predict(self, source, *, modality, progress=None, source_reference=None):
        if modality != self.manifest['modality']:
            raise InputError(f'Unsupported modality {modality!r}; this model requires an explicitly declared SSS_LF image')
        source = Path(source); result = self.original_raw(source, progress)
        source_hash = sha256(source); width, height = result['original_size']
        reference = source_reference or source.name; detections = []
        for box in result['predictions']:
            if box['score'] < self.thresholds[str(box['class_id'])]:
                continue
            a, b, c, d = box['xyxy']
            identity = json.dumps([source_hash, self.model_hash, box], sort_keys=True).encode()
            detections.append({'detection_id': hashlib.sha256(identity).hexdigest()[:24],
                'source_reference': reference, 'image_dimensions': {'width': width, 'height': height},
                'class_id': box['class_id'], 'class_name': box['class_name'], 'material': None,
                'model_score': box['score'], 'score_type': 'yolo_class_confidence_uncalibrated',
                'box_xyxy_pixels': box['xyxy'], 'pixel_dimensions': {'width': c-a, 'height': d-b},
                'metric_dimensions': None, 'coordinates': None, 'crs': None,
                'position_method': 'original_image_pixels', 'uncertainty': None,
                'quality_flags': ['geographical_metadata_unavailable', 'pipeline_may_be_a_segment'],
                'review_status': 'unreviewed', 'model_version': self.manifest['model_version'],
                'model_sha256': self.model_hash, 'preprocessing_version': PREPROCESSING_VERSION})
        return {'schema_version': SCHEMA_VERSION, 'source_reference': reference, 'source_sha256': source_hash,
                'image_dimensions': {'width': width, 'height': height}, 'modality': modality,
                'model_version': self.manifest['model_version'], 'model_sha256': self.model_hash,
                'preprocessing_version': PREPROCESSING_VERSION, 'thresholds': self.thresholds,
                'tile_count': result['tile_count'], 'detections': detections,
                'inference_provenance': {'tiles': [{**t,'crop_xyxy':list(t['crop_xyxy'])} for t in result['tiles']], 'post_source_nms_predictions': result['predictions'], 'source_nms_iou': self.protocol['source_nms_iou'] if 'source_nms_iou' in self.protocol else 0.5, 'tile_nms_iou': self.protocol.get('tile_nms_iou'), 'policy': 'Unchanged class-aware source NMS; no long-object stitching; pre-tile-NMS candidates unavailable'},
                'coordinates': None, 'crs': None, 'quality_flags': ['geographical_metadata_unavailable'],
                'end_to_end_seconds': result['end_to_end_seconds']}

    def batch(self, folder, *, modality, progress=None):
        folder = Path(folder)
        if not folder.is_dir():
            raise InputError('Batch source must be a folder')
        files = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in SUFFIXES)
        if not files:
            raise InputError('Folder contains no supported image files')
        for index, path in enumerate(files):
            yield path, self.predict(path, modality=modality)
            if progress:
                progress(index+1, len(files))
