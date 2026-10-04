import gzip
from pathlib import Path
import struct
import sys
import unittest
sys.path.insert(0,str(Path(__file__).parent.parent/'test-deps'))
from lupa.luajit21 import LuaRuntime
import build

class NativeMenuTest(unittest.TestCase):
 def test_native_switch_preserves_inventory_and_restores_configuration(self):
  lua=LuaRuntime(encoding=None,unpack_returned_tuples=True)
  module=lua.execute((build.HERE/'native_ammo_menu.lua').read_bytes())
  memory={};writes=[]
  def add(a,b): memory[a]=bytearray(b)
  def read(a,n):
   for base,b in memory.items():
    if base<=a and a+n<=base+len(b):return bytes(b[a-base:a-base+n])
  def write(a,b):
   for base,data in memory.items():
    if base<=a and a+len(b)<=base+len(data):
     data[a-base:a-base+len(b)]=b;writes.append((a,b));return True
   return False
  def ptr(b):return struct.unpack('<Q',b)[0] if b and len(b)==8 else None
  def pointer(a,v):add(a,struct.pack('<Q',v))
  def mapping(a,key,index,base):
   add(a,struct.pack('<QIII',base,1,0xffffffff,1));add(base,struct.pack('<II',key,index))
  entities=gzip.decompress(build.SAMPLE.read_bytes())
  wm,wi,wr=build.component(entities,'WeaponDataComponentData',11680,1232,build.DOMINATOR)
  pm,pi,pr=build.component(entities,'ProjectileWeaponComponentData',8672,616,build.DOMINATOR)
  game,owner,data,projectile=0x100000,0x200000,0x300000,0x400000
  pointer(game+0x3326B90,owner)
  pointer(owner+0xF11798,data);add(data,wm);row=data+len(wm)+wi*1232;add(row,wr)
  pointer(owner+0xF10000,projectile);add(projectile,pm);projectile_row=projectile+len(pm)+pi*616;add(projectile_row,pr)
  player,inventory,manager=0x500000,0x600000,0x700000
  pointer(game+0x3326468,player);pointer(game+0x3326738,inventory);pointer(game+0x3326CE0,manager)
  add(player+0x3A8,struct.pack('<I',101))
  avatar=struct.pack('<QIIII',99,102,101,0,0);weapon=struct.pack('<QIIII',build.DOMINATOR,103,104,0,0)
  mapping(owner+0xF21A88,101,0,0x800000);add(owner+0xF31AD8,avatar)
  mapping(owner+0xF19A70,103,1,0x800100);add(owner+0xF31AD8+24,weapon)
  mapping(inventory+40,102,0,0x800200);pointer(inventory+64,0x800300);pointer(0x800300,owner+0xF31AD8)
  pointer(inventory+80,0x800400);ammo=struct.pack('<12I',0,103,0,0,3,6,2,2,0,0,0,0);add(0x800400,ammo)
  mapping(manager+48,103,0,0x800500);pointer(manager+88,0x800600);pointer(manager+96,0x800a00)
  add(0x800600,bytes(1008));add(0x800a00,bytes(12))
  api=lua.table_from({b'read':read,b'read_blob':read,b'read_module':read,b'pointer':ptr,b'write':write})
  ref=lua.table_from({b'weapon_map':wm,b'weapon_index':wi,b'weapon_row':wr,b'map':pm,b'row':pr})
  hit=lua.table_from({b'slot_rva':0xF10000,b'row':projectile_row});spec=lua.table()
  state=module[b'new'](api,game,owner,ref,struct.pack('<Q',build.DOMINATOR),hit,spec)
  policy=lua.execute(b'return {set_ems=function(self,v)self.enabled=v end}')
  state[b'step'](state,policy);self.assertEqual(state[b'status'],b'NATIVE_GAS');self.assertFalse(policy[b'enabled'])
  memory[0x800a00][4:8]=struct.pack('<I',4)
  state[b'step'](state,policy);self.assertEqual(state[b'status'],b'NATIVE_EMS');self.assertTrue(policy[b'enabled'])
  self.assertEqual(read(0x800400,48),ammo)
  self.assertEqual(set(a for a,b in writes),{row+184,projectile_row+576,0x800600+0x350})
  memory[0x800a00][4:8]=struct.pack('<I',12)
  count=len(writes);state[b'step'](state,policy)
  self.assertEqual(state[b'status'],b'UNKNOWN_AMMO_MODE_NO_WRITE');self.assertEqual(len(writes),count)
  self.assertTrue(policy[b'enabled']);self.assertEqual(read(0x800400,48),ammo)
  state[b'stop'](state)
  self.assertEqual(read(row,1232),wr);self.assertEqual(read(projectile_row,616),pr)
  self.assertEqual(read(0x800600,1008),bytes(1008))
  memory[row][0]=memory[row][0]^1
  count=len(writes)
  rejected=module[b'new'](api,game,owner,ref,struct.pack('<Q',build.DOMINATOR),hit,lua.table())
  self.assertEqual(rejected[b'status'],b'WEAPON_DATA_MISMATCH_NO_WRITE');self.assertEqual(len(writes),count)

if __name__=='__main__':unittest.main()
