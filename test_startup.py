import gzip
import struct
import unittest
from test_lua_runtime import LuaRuntime
import build

SHA=b'2e2c3b7c2500646dadd5f2b4c6e0504dbb7e7896139f64cddc0d1813c718f51e'

class StartupTest(unittest.TestCase):
 def setup_runtime(self):
  lua=LuaRuntime(encoding=None,unpack_returned_tuples=True)
  memory={};self.reads=0;self.writes=[]
  def add(a,b):memory[a]=bytearray(b)
  def read(a,n):
   self.reads+=1
   for base,b in memory.items():
    if base<=a and a+n<=base+len(b):return bytes(b[a-base:a-base+n])
  def write(a,b):
   for base,data in memory.items():
    if base<=a and a+len(b)<=base+len(data):data[a-base:a-base+len(b)]=b;self.writes.append(a);return True
   return False
  def ptr(b):return struct.unpack('<Q',b)[0]if b and len(b)==8 else None
  entities=gzip.decompress(build.SAMPLE.read_bytes())
  game,owner,table=0x100000,0x200000,0x300000
  mapping,index,row=build.component(entities,'ProjectileWeaponComponentData',8672,616,build.DOMINATOR)
  _,bi,bolt=build.component(entities,'ProjectileWeaponComponentData',8672,616,build.BOLT_CANDIDATE)
  _,gi,gp=build.component(entities,'ProjectileWeaponComponentData',8672,616,0x52E4334E6A128CAF)
  components=bytearray(mapping+bytes(252*616))
  for i,r in [(index,row),(bi,bolt),(gi,gp)]:components[len(mapping)+i*616:len(mapping)+(i+1)*616]=r
  add(table,components);add(owner+0xF11A40,struct.pack('<Q',table));add(game+0x3326B90,struct.pack('<Q',owner))
  wm,wi,wr=build.component(entities,'WeaponDataComponentData',11680,1232,build.DOMINATOR)
  _,gwi,gwr=build.component(entities,'WeaponDataComponentData',11680,1232,0x52E4334E6A128CAF)
  add(owner+0xF11798,struct.pack('<Q',0x500000));add(0x500000,wm)
  add(0x500000+len(wm)+wi*1232,wr);add(0x500000+len(wm)+gwi*1232,gwr)
  mm,mi,mr=build.component(entities,'WeaponMagazineComponentData',8640,160,build.DOMINATOR)
  add(owner+0xF11060,struct.pack('<Q',0x600000));add(0x600000,mm);add(0x600000+len(mm)+mi*160,mr)
  projectiles=(build.HERE/'reference_projectile_table.bin').read_bytes()
  damage=(build.HERE/'reference_damage_table.bin').read_bytes()
  for rva,offset,base,name,stride,records in [(0x348E2F8,4,0x700000,'ProjectileSettings',272,projectiles),(0x348E1F8,60,0x800000,'DamageSettings',76,damage),(0x348EC88,4,0x900000,'ExplosionSettings',152,bytes(422*152))]:
   header=struct.pack('<IIII8xQQ',0x444c444c,1,build.dlhash(name),67800 if name=='ExplosionSettings' else 16+len(records),base+offset+40,len(records)//stride)
   add(base+offset,header+records);add(game+rva,struct.pack('<Q',base))
  def projectile(kind):
   return next(projectiles[o:o+272]for o in range(0,len(projectiles),272)if struct.unpack_from('<I',projectiles,o)[0]==kind)
  ds=(build.HERE/'reference_damage_current.bin').read_bytes();dt=bytearray(ds[76:]);struct.pack_into('<7I',dt,0,67,163,69,3,3,3,3)
  ref={b'map':mapping,b'row':row,b'bolt':bolt,b'bolt_id':struct.pack('<Q',build.BOLT_CANDIDATE),b'jar_projectile':projectile(343),b'bolt_projectile':projectile(125),b'damage_original':ds[:76],b'damage_source':ds[76:],b'damage_target':bytes(dt),b'ems_projectile':projectile(154),b'gas_icon':struct.pack('<Q',0x3B975896BC689499),b'ems_icon':struct.pack('<Q',0x2D9268907FB9420E),b'weapon_map':wm,b'weapon_index':wi,b'weapon_row':wr,b'mag_map':mm,b'mag_index':mi,b'mag_row':mr,b'alternate_type':332,b'alternate_original':projectile(332)}
  gp_ref={b'map':mapping,b'row':gp,b'index':gi,b'id':struct.pack('<Q',0x52E4334E6A128CAF),b'weapon_map':wm,b'weapon_index':gwi,b'weapon_row':gwr,b'projectile_type':263,b'projectile':projectile(263),b'ems_projectile':projectile(154),b'ems_icon':ref[b'ems_icon'],b'alternate_type':333,b'alternate_original':projectile(333)}
  api=lua.table_from({b'read':read,b'read_blob':read,b'read_module':read,b'pointer':ptr,b'write':write,b'excluded':lambda a,n:False,b'module':lambda name:game,b'module_hash':lambda base:SHA})
  g=lua.globals();g.api=api;g.ref=lua.table_from(ref);g.gp_ref=lua.table_from(gp_ref);g.jar_id=struct.pack('<Q',build.DOMINATOR)
  lua.execute(b'CowboyBingusModLoader={api=1};update=function()return 123 end;create_api=function()return api end;layout_resolver={new=function()return {status="IDLE",candidates={},step=function()error("full scan invoked")end}end}')
  for name,file in [(b'bolt_locator','locator.lua'),(b'magazine_menu','magazine_menu.lua'),(b'projectile_sync','projectile_sync.lua'),(b'native_ammo_menu','native_ammo_menu.lua'),(b'fixed_projectile','fixed_projectile.lua')]:g[name]=lua.execute((build.HERE/file).read_bytes())
  g.settings_locator=lua.execute((build.HERE.parent.parent/'GL28-Adaptive-Boost/gl28_settings_locator.lua').read_bytes())
  self.lua,self.memory,self.api=lua,memory,api
  return lua

 def test_fast_startup_and_shutdown_restore_all_data(self):
  lua=self.setup_runtime();before={a:bytes(b)for a,b in self.memory.items()}
  lua.execute((build.HERE/'entry.lua').read_bytes())
  state=lua.globals().TongzP35GasSpeargun
  for frame in range(100):
   self.assertEqual(lua.globals().update(),123)
   if state[b'ready_frame']:break
  self.assertEqual(state[b'startup_path'],b'VERIFIED_FAST')
  self.assertLess(state[b'ready_frame'],65)
  self.assertEqual(state[b'fixed_p35'][b'status'],b'READY')
  self.assertEqual(state[b'magazine'][b'capacity'],3)
  self.assertGreater(len(self.writes),0)
  lua.globals().shutdown()
  self.assertEqual({a:bytes(b)for a,b in self.memory.items()},before)

 def test_changed_fast_table_does_not_write_and_falls_back(self):
  lua=self.setup_runtime();self.memory[0x300000][0]^=1
  lua.execute((build.HERE/'entry.lua').read_bytes())
  for _ in range(300):lua.globals().update()
  state=lua.globals().TongzP35GasSpeargun
  self.assertEqual(state[b'startup_path'],b'SCAN_FALLBACK')
  self.assertEqual(state[b'status'],b'LOCATING_ENTITY_OWNER')
  self.assertEqual(self.writes,[])
