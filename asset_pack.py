"""Package dependency and original asset inclusion, following G-16 Gas Impact."""
from pathlib import Path
import importlib.util
import hashlib
import json
import struct
import zipfile
# preview11-perf: assets and sibling projects stay in the parent P-35 workspace.
HERE=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('mine_archive_builder',HERE.parent/'Mine-Deployer-Swap/build.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
archive,parse_package,rh=helper.archive,helper.parse_package,helper.rh

def merged_package(package_name='caustic_dart_gun'):
 base=HERE/'assets/packages/generated/loadout'
 header,first=parse_package((base/(package_name+'.package.main')).read_bytes())
 second=[]
 if package_name=='caustic_dart_gun':
  _,second=parse_package((base/'harpoon_gun.package.main').read_bytes())
 _,ems=parse_package((base/'ems_mortar.package.main').read_bytes())
 _,effects=parse_package((base/'ems_effect.package.main').read_bytes())
 ems=list(dict.fromkeys(ems+effects))
 second=list(dict.fromkeys(second+ems))
 assert len(first)==len(set(first)) and len(second)==len(set(second))
 merged=first+[r for r in second if r not in set(first)]
 assert set(first+second)==set(merged)
 return struct.pack('<4sIII',header[0],header[1],len(merged),header[2])+b''.join(struct.pack('<QQ',*r)for r in merged)

SHARED_G16_AUDIO=(0x2786FB10B10C6843,0x504B55235D21440E)

def without_resources(data,removed):
 # Preserve all remaining resource offsets and stream/GPU bytes.
 from collections import Counter
 magic,types,count=struct.unpack_from('<III',data)
 assert magic==0xf0000011
 entries=list(struct.iter_unpack('<7Q6I',data[72+types*32:72+types*32+count*80]))
 kept=[r for r in entries if r[:2] not in removed]
 assert len(kept)==count-len(removed)
 counts=Counter(r[1]for r in kept)
 old_types=list(struct.iter_unpack('<IIQIIII',data[72:72+types*32]))
 type_bytes=b''.join(struct.pack('<IIQIIII',r[0],r[1],r[2],counts[r[2]],*r[4:])for r in old_types if counts[r[2]])
 entry_bytes=b''.join(struct.pack('<7Q6I',*r[:-1],index)for index,r in enumerate(kept))
 result=bytearray(data)
 struct.pack_into('<II',result,4,len(counts),len(kept))
 result[72:72+len(type_bytes)+len(entry_bytes)]=type_bytes+entry_bytes
 return bytes(result)

def without_shared_audio(data):
 return without_resources(data,{SHARED_G16_AUDIO})

def resource_rows(data):
 types,count=struct.unpack_from('<II',data,4)
 return list(struct.iter_unpack('<7Q6I',data[72+types*32:72+types*32+count*80]))

EMS_PARTICLE=(0xBFE8E0D13DAFBE5E,0xA8193123526FAD64)
EMS_PARTICLE_SHA256='1cbaea97550c869058b87ddbbede563c9a75276f12a85c8a18c31e3e98e9f953'
# preview19: shrink the lingering EMS field. Diagnostic recolouring (preview16
# and preview18) showed the blue smoke and air streaks are systems 15-19 of
# this effect. Every spatial value of those systems is halved: spawn sphere
# [3,0,min,max], disc/cylinder radius and height (types 0xD/0xC), sprite size
# (channel 0x28) and streak range (channel 0x30). Timing, rates and colours stay.
EMS_FIELD_SCALE=0.5
EMS_FIELD_VALUES=[
 (25644,(4.0,12.0)),(25596,(2.0,6.0)),                      # 15: spawn sphere, size
 (27472,(12.0,)),(27420,(3.0,8.0)),                         # 16: disc radius, size
 (29352,(4.0,13.0)),(29296,(10.0,)),(29304,(10.0,)),(29260,(1.5,3.0)),  # 17: sphere, cylinder r/h, size
 (31368,(4.0,11.0)),(31336,(3.0,14.0)),                     # 18: sphere, streak range
 (33768,(12.0,12.0)),(33736,(3.0,10.0)),                    # 19: sphere, streak range
]

def shrink_ems_field(data):
 assert hashlib.sha256(data).hexdigest()==EMS_PARTICLE_SHA256,'EMS particle changed'
 out=bytearray(data)
 for offset,values in EMS_FIELD_VALUES:
  fmt='<%df'%len(values)
  assert struct.unpack_from(fmt,out,offset)==values
  struct.pack_into(fmt,out,offset,*(v*EMS_FIELD_SCALE for v in values))
 return bytes(out)

def merge_asset_archives(folders):
 from collections import Counter
 resources={}
 for folder in folders:
  base=HERE/'assets'/folder
  provenance=json.loads((base/'provenance.json').read_text())
  name=provenance['source_archive']
  files=[]
  for suffix in ('','.stream','.gpu_resources'):
   data=(base/(name+suffix)).read_bytes()
   assert hashlib.sha256(data).hexdigest()==provenance['files'][suffix]['sha256']
   files.append(data)
  for row in resource_rows(files[0]):
   if row[:2]==SHARED_G16_AUDIO:continue
   parts=tuple(data[offset:offset+size] for data,offset,size in zip(files,row[2:5],row[7:10]))
   assert all(len(part)==size for part,size in zip(parts,row[7:10]))
   if row[:2] in resources:
    assert resources[row[:2]][1]==parts,'shared asset bytes differ'
   else:resources[row[:2]]=(row,parts)
 if EMS_PARTICLE in resources:
  row,parts=resources[EMS_PARTICLE]
  resources[EMS_PARTICLE]=(row,(shrink_ems_field(parts[0]),)+parts[1:])
 ordered=sorted(resources.items(),key=lambda item:(item[0][1],item[0][0]))
 counts=Counter(key[1]for key,_ in ordered)
 types=b''.join(struct.pack('<IIQIIII',0,0,kind,count,0,16,16)for kind,count in sorted(counts.items()))
 start=(72+len(types)+80*len(ordered)+15)&~15
 main,stream,gpu=bytearray(start),bytearray(),bytearray()
 entries=bytearray();buffer_offset=0
 for index,(key,(row,parts))in enumerate(ordered):
  offsets=[]
  for destination,part in zip((main,stream,gpu),parts):
   offsets.append(len(destination)if part else 0)
   destination.extend(part);destination.extend(b'\0'*(-len(destination)%16))
  entries.extend(struct.pack('<7Q6I',*key,*offsets,buffer_offset,row[6],*map(len,parts),row[10],row[11],index))
  buffer_offset=(buffer_offset+len(parts[0])+15)&~15
 header=struct.pack('<III20sQQ24s',0xF0000011,len(counts),len(ordered),b'',len(main),buffer_offset,b'')
 main[:72+len(types)+len(entries)]=header+types+entries
 return bytes(main),bytes(stream),bytes(gpu)

def include_assets(output,resource,payload):
 with zipfile.ZipFile(output)as z: files={n:z.read(n)for n in z.namelist()}
 manifest=json.loads(files['manifest.json'])
 manifest['Description']='Requires Bingus Shared Loader API 1 and Suzukas G-16 Impact Gas Grenade v1.6.1 (including preview1). Shared audio supplied by G-16.'
 for option in manifest['Options']:option['Description']=manifest['Description']
 files['manifest.json']=json.dumps(manifest,indent=2).encode()
 resources={(rh(resource),rh('lua')):struct.pack('<II',len(payload),2)+payload,
  (rh('packages/generated/loadout/caustic_dart_gun'),rh('package')):merged_package()}
 files['Addon/9ba626afa44a3aa3.patch_0']=archive(resources)
 # Mount complete payloads through the P-35's own loadout archive, matching
 # the verified G16 fix. GP-31 is no longer modified (preview12).
 for destination,folders in [('1b006880ac88d1cd',('speargun','ems','ems_effect'))]:
  parts=merge_asset_archives(folders)
  for suffix,data in zip(('', '.stream','.gpu_resources'),parts):
   files['Addon/'+destination+'.patch_0'+suffix]=data
 with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED)as z:
  for n,data in sorted(files.items()):z.writestr(n,data)
