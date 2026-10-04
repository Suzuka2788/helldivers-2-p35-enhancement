import struct
import gzip
import json
import unittest
import zipfile
import build
from asset_pack import HERE,merged_package,parse_package,rh,without_shared_audio,SHARED_G16_AUDIO

def rows(data):
 magic,types,count=struct.unpack_from('<III',data)
 assert magic==0xf0000011
 return list(struct.iter_unpack('<7Q6I',data[72+32*types:72+32*types+80*count]))

class AssetPackTest(unittest.TestCase):
 def test_gp31_is_not_shipped(self):
  # preview12 leaves GP-31 untouched (Contact Detonation Repair owns its record).
  gp=rh('packages/generated/loadout/grenade_pistol')
  with zipfile.ZipFile(build.OUT) as z:
   main=z.read('Addon/9ba626afa44a3aa3.patch_0')
   self.assertFalse([r for r in rows(main)if r[0]==gp])
   self.assertNotIn('Addon/'+f'{gp:016x}'+'.patch_0',z.namelist())
 def test_ems_package_is_selected_by_current_entity(self):
  _,_,row=build.component(gzip.decompress(build.SAMPLE.read_bytes()),'LoadoutPackageComponentData',17344,32,0xB2053A1838092F8B)
  self.assertEqual(struct.unpack_from('<Q',row,8)[0],0x524A07E02060D7AB)
 def test_complete_dependency_union(self):
  base=HERE/'assets/packages/generated/loadout'
  _,p35=parse_package((base/'caustic_dart_gun.package.main').read_bytes())
  _,spear=parse_package((base/'harpoon_gun.package.main').read_bytes())
  _,ems=parse_package((base/'ems_mortar.package.main').read_bytes())
  _,effects=parse_package((base/'ems_effect.package.main').read_bytes())
  _,merged=parse_package(merged_package())
  self.assertEqual(set(merged),set(p35+spear+ems+effects))
  self.assertEqual(len(merged),len(set(merged)))
 def test_zip_assets_and_package(self):
  with zipfile.ZipFile(build.OUT) as z:
   self.assertIsNone(z.testzip())
   main=z.read('Addon/9ba626afa44a3aa3.patch_0')
   entries=rows(main)
   key=(rh('packages/generated/loadout/caustic_dart_gun'),rh('package'))
   record,=[r for r in entries if r[:2]==key]
   self.assertEqual(main[record[2]:record[2]+record[7]],merged_package())
   for destination,folders in [('1b006880ac88d1cd',('speargun','ems','ems_effect'))]:
    packed=[z.read('Addon/'+destination+'.patch_0'+suffix)for suffix in ('','.stream','.gpu_resources')]
    actual={}
    for r in rows(packed[0]):
     self.assertNotIn(r[:2],actual)
     actual[r[:2]]=tuple(data[off:off+size]for data,off,size in zip(packed,r[2:5],r[7:10]))
     self.assertEqual(tuple(map(len,actual[r[:2]])),r[7:10])
    expected={}
    for folder in folders:
     base=HERE/'assets'/folder;name=json.loads((base/'provenance.json').read_text())['source_archive']
     native=[(base/(name+suffix)).read_bytes()for suffix in ('','.stream','.gpu_resources')]
     for r in rows(native[0]):
      if r[:2]!=SHARED_G16_AUDIO:
       expected[r[:2]]=tuple(data[off:off+size]for data,off,size in zip(native,r[2:5],r[7:10]))
    self.assertEqual(actual,expected)
 def test_g16_resource_sets_do_not_overlap(self):
  def resources(z):
   found={}
   for name in z.namelist():
    if '.patch_' not in name or name.endswith(('.stream','.gpu_resources')):continue
    data=z.read(name)
    for r in rows(data):
     parts=[]
     for off,size,suffix in [(r[2],r[7],''),(r[3],r[8],'.stream'),(r[4],r[9],'.gpu_resources')]:
      part=z.read(name+suffix)if size else b''
      parts.append(part[off:off+size])
     found[r[:2]]=parts
   return found
  for name in ['Suzukas-Impact-Gas-Grenade-v1.6.1-preview1.zip','Suzukas-Impact-Gas-Grenade-v1.6.1.zip']:
   with zipfile.ZipFile(build.OUT)as p35,zipfile.ZipFile(HERE.parent/'G16-Gas-Impact'/name)as g16:
    a,b=resources(p35),resources(g16)
    self.assertFalse(a.keys()&b.keys())
    self.assertIn(SHARED_G16_AUDIO,b)
    original=(HERE/'assets/speargun/70d708e5fd627493').read_bytes()
    record,=[r for r in rows(original)if r[:2]==SHARED_G16_AUDIO]
    original_parts=[]
    for off,size,suffix in [(record[2],record[7],''),(record[3],record[8],'.stream'),(record[4],record[9],'.gpu_resources')]:
     original_parts.append((HERE/'assets/speargun'/('70d708e5fd627493'+suffix)).read_bytes()[off:off+size])
    self.assertEqual(b[SHARED_G16_AUDIO],original_parts)
 def test_ems_payloads_are_mounted_by_p35(self):
  with zipfile.ZipFile(build.OUT)as z:
   self.assertNotIn('Addon/62c192b6ee416f89.patch_0',z.namelist())
   self.assertNotIn('Addon/f35f2da49e6c7081.patch_0',z.namelist())
   base=HERE/'assets/packages/generated/loadout'
   _,ems=parse_package((base/'ems_mortar.package.main').read_bytes())
   _,effects=parse_package((base/'ems_effect.package.main').read_bytes())
   for weapon in ('caustic_dart_gun',):
    archive='Addon/'+f'{rh("packages/generated/loadout/"+weapon):016x}'+'.patch_0'
    r=rows(z.read(archive));keys={record[:2]for record in r}
    self.assertEqual(len(keys),len(r))
    self.assertLessEqual({(name,typ)for typ,name in ems+effects},keys|{SHARED_G16_AUDIO})
    self.assertIn((0xBFE8E0D13DAFBE5E,rh('particles')),keys)
    ranges=[]
    for record in r:
     self.assertNotIn(SHARED_G16_AUDIO,[record[:2]])
     for suffix,off,size in zip(('','.stream','.gpu_resources'),record[2:5],record[7:10]):
      if size:self.assertLessEqual(off+size,len(z.read(archive+suffix)))
     if record[7]:ranges.append((record[5],record[5]+record[7]))
    ranges.sort()
    self.assertTrue(all(a[1]<=b[0]for a,b in zip(ranges,ranges[1:])))
if __name__=='__main__':unittest.main()
