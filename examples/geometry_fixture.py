"""Controlled software fixture; these coordinates are not a field measurement."""
from bluecho.inspection.geometry import position
m={'mapping':'ping_rows','modality':'SSS','flat_seabed_verified':True,'level_sensor_verified':True,'pings':[{'row':0,'ping_index':1,'timestamp':'2026-01-01T00:00:00Z','sensor_position':{'x':0,'y':0,'crs':'EPSG:4326','reference':'sonar_sensor','valid':True},'heading_degrees':0,'heading_reference':'true_north','side':'starboard','sample_count':100,'sample_direction':'near_to_far','range_start':0,'range_end':100,'range_unit':'m','range_geometry':'slant','altitude':30,'altitude_unit':'m','altitude_reference':'seabed','altitude_provenance':'manually_supplied','error_bounds':{'navigation_m':1,'heading_degrees':1,'altitude_m':.5,'slant_range_m':.2}}]}
r=position(50,0,m);assert r['coordinates'][0]>0 and r['uncertainty']['radius_m']>1
print(r)
