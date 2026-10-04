import gzip
from pathlib import Path
import struct
import sys
import unittest
sys.path.insert(0,str(Path(__file__).parent.parent/'test-deps'))
from lupa.luajit21 import LuaRuntime
import build

MODE,CAPACITY,SPARES=b'tongz.p35.magazine_mode',b'tongz.p35.magazine_capacity',b'tongz.p35.single_load_spares'

class MagazineMenuTest(unittest.TestCase):
 def setup_policy(self,delayed=False,saved=None):
  lua=LuaRuntime(unpack_returned_tuples=True,encoding=None)
  mapping,index,row=build.component(gzip.decompress(build.SAMPLE.read_bytes()),'WeaponMagazineComponentData',8640,160,build.DOMINATOR)
  self.original=row;self.mapping=mapping;self.index=index;self.lua=lua
  lua.globals().blob=mapping+bytes(index*160)+row
  lua.execute(b"""
   local function ptr(n) local t={} for i=1,8 do t[i]=string.char(n%256);n=math.floor(n/256)end return table.concat(t)end
   slots={[0x200000+0xF10000]=0x300000}
   writes=0
   api={read=function(at,n)
    if slots[at] then return ptr(slots[at])end
    local o=at-0x300000
    if o>=0 and o+n<=#blob then return blob:sub(o+1,o+n)end
   end,pointer=function(s)if not s then return nil end local v=0 for i=8,1,-1 do v=v*256+s:byte(i)end return v end,
   query=function(at)return {base=0x300000,size=#blob,readable=true}end,
   read_blob=function(at,n)return at==0x300000 and blob:sub(1,n) or nil end,
   write=function(at,s)writes=writes+1;local o=at-0x300000;blob=blob:sub(1,o)..s..blob:sub(o+#s+1);return true end}
   specs,callbacks,saved={},{},{}
   menu={api=1,register_option=function(id,spec)specs[id]=spec;return true end,
    get=function(id)return saved[id] or specs[id].default end,on_change=function(id,fn)callbacks[id]=fn end}
  """)
  for key,value in (saved or {}).items():lua.globals().saved[key]=value
  if not delayed:lua.globals().ModOptionsMenu=lua.globals().menu
  module=lua.execute((Path(__file__).parent/'magazine_menu.lua').read_bytes())
  ref=lua.table_from({b'mag_map':mapping,b'mag_index':index,b'mag_row':row})
  return module.new(lua.globals().api,0x200000,ref)
 def run_frames(self,policy,n=60):
  for _ in range(n):policy.step(policy)
 def choose(self,option,index):
  self.lua.globals().callbacks[option](index)
 def row(self):return self.lua.globals().blob[-160:]
 def fields(self):return struct.unpack_from('<6I',self.row(),136)
 def test_options_registered_with_defaults(self):
  policy=self.setup_policy();self.run_frames(policy,420)
  self.assertEqual(policy.menu_status,b'REGISTERED')
  specs=self.lua.globals().specs
  self.assertEqual(list(specs[MODE].choices.values()),[b'Magazine',b'Single load'])
  self.assertEqual(list(specs[CAPACITY].choices.values()),[b'2',b'3',b'4',b'5',b'6'])
  self.assertEqual(list(specs[SPARES].choices.values()),[b'1',b'2',b'3',b'4',b'5',b'6'])
  self.assertEqual((specs[MODE].default,specs[CAPACITY].default,specs[SPARES].default),(1,2,6))
  self.assertEqual(policy.mode,b'MAGAZINE');self.assertEqual(self.fields(),(3,2,2,2,6,0))
 def test_magazine_choices_only_change_capacity_and_restore(self):
  policy=self.setup_policy();self.run_frames(policy,420)
  for capacity in [2,3,4,5,6,2]:
   self.choose(CAPACITY,capacity-1);self.run_frames(policy)
   expected=self.mapping+bytes(self.index*160)+self.original[:136]+struct.pack('<I',capacity)+self.original[140:]
   self.assertEqual(self.lua.globals().blob,expected)
  policy.stop(policy)
  self.assertEqual(policy.status,b'MAGAZINE_RESTORED')
  self.assertEqual(self.lua.globals().blob,self.mapping+bytes(self.index*160)+self.original)
 def test_single_load_spares_one_to_six(self):
  policy=self.setup_policy();self.run_frames(policy,420)
  self.choose(MODE,2);self.run_frames(policy)
  self.assertEqual(policy.mode,b'SINGLE_LOAD');self.assertEqual(self.fields(),(1,6,6,6,0,0))
  for spares in [1,2,3,4,5,6,1]:
   self.choose(SPARES,spares);self.run_frames(policy)
   self.assertEqual(self.fields(),(1,spares,spares,spares,0,0))
   self.assertEqual(self.row()[:136],self.original[:136])
  # The capacity option is ignored while single load is active.
  self.choose(CAPACITY,4);self.run_frames(policy);self.assertEqual(self.fields(),(1,1,1,1,0,0))
  self.choose(MODE,1);self.run_frames(policy);self.assertEqual(self.fields(),(5,2,2,2,6,0))
  self.choose(MODE,2);self.run_frames(policy)
  policy.stop(policy)
  self.assertEqual(policy.status,b'MAGAZINE_RESTORED');self.assertEqual(self.row(),self.original)
 def test_saved_single_load_applies_on_start(self):
  policy=self.setup_policy(saved={MODE:2,SPARES:3});self.run_frames(policy,420)
  self.assertEqual(self.fields(),(1,3,3,3,0,0));self.assertEqual(policy.status,b'APPLIED_MAGAZINE_CAPACITY')
 def test_delayed_menu_and_invalid_values(self):
  policy=self.setup_policy(delayed=True);self.run_frames(policy,420)
  self.assertEqual(policy.menu_status,b'WAITING')
  self.lua.globals().ModOptionsMenu=self.lua.globals().menu
  self.run_frames(policy);self.assertEqual(policy.menu_status,b'REGISTERED')
  for value in [0,7,2.5,b'3']:self.assertFalse(policy.set_capacity(policy,value)[0])
  for value in [0,7,1.5,b'3']:self.assertFalse(policy.set_spares(policy,value)[0])
  self.assertFalse(policy.set_mode(policy,b'OTHER')[0])
  self.choose(MODE,3);self.choose(SPARES,0);self.choose(SPARES,7)
  self.assertEqual((policy.mode,policy.capacity,policy.spares),(b'MAGAZINE',3,6))
 def test_default_three_without_menu(self):
  policy=self.setup_policy(delayed=True);self.run_frames(policy,420)
  self.assertEqual(self.fields(),(3,2,2,2,6,0))
 def test_external_change_refuses_overwrite(self):
  policy=self.setup_policy();self.run_frames(policy,420)
  writes=self.lua.globals().writes
  self.lua.globals().blob=b'X'+self.lua.globals().blob[1:]
  self.choose(MODE,2);self.run_frames(policy)
  self.assertEqual(policy.status,b'MAGAZINE_CONTEXT_CHANGED_NO_WRITE')
  self.assertEqual(self.lua.globals().writes,writes)
if __name__=='__main__':unittest.main()
