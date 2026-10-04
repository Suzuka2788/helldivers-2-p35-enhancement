import struct
import unittest
from test_lua_runtime import LuaRuntime
import build

class FixedProjectileTest(unittest.TestCase):
 def test_fixed_record_is_written_once_and_restored(self):
  lua=LuaRuntime(encoding=None,unpack_returned_tuples=True)
  module=lua.execute((build.HERE/'fixed_projectile.lua').read_bytes())
  rows=(build.HERE/'reference_projectile_table.bin').read_bytes()
  original,=[rows[o:o+272]for o in range(0,len(rows),272)if struct.unpack_from('<I',rows,o)[0]==332]
  header=struct.pack('<IIII8xQQ',0x444c444c,1,0,16+len(rows),0x40002c,350)
  memory={0x400004:bytearray(header+rows),0x100100:bytearray(struct.pack('<Q',0x400000))};writes=[]
  def read(a,n):
   for base,b in memory.items():
    if base<=a and a+n<=base+len(b):return bytes(b[a-base:a-base+n])
  def write(a,b):
   for base,data in memory.items():
    if base<=a and a+len(b)<=base+len(data):data[a-base:a-base+len(b)]=b;writes.append(a);return True
   return False
  api=lua.table_from({b'read':read,b'read_blob':read,b'read_module':read,b'write':write,b'pointer':lambda b:struct.unpack('<Q',b)[0]if b and len(b)==8 else None})
  settings=lua.table_from({b'status':b'COMPLETE',b'hits':lua.table_from({b'projectile':lua.table_from([lua.table_from({b'header':0x400004,b'pointer_rva':0x100})])})})
  target=lua.table();state=module[b'new'](api,settings,0x100000,original,target)
  spear=(build.HERE/'reference_projectiles_current.bin').read_bytes()[272:]
  modified=bytearray(spear);struct.pack_into('<I',modified,156,180);modified[16:24]=struct.pack('<Q',0x2D9268907FB9420E)
  state[b'step'](state,bytes(modified));self.assertEqual(state[b'status'],b'READY')
  address=0x40002c+rows.index(original)
  expected=original[:4]+bytes(modified[4:]);self.assertEqual(read(address,272),expected)
  state[b'step'](state,spear);self.assertEqual(len(writes),1);self.assertEqual(read(address,272),expected)
  state[b'stop'](state);self.assertEqual(read(0x40002c,len(rows)),rows)
