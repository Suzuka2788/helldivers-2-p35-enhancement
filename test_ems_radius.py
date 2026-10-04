import struct
import unittest
from test_lua_runtime import LuaRuntime
import build

ID = b'tongz.p35.ems_size'
HEADER, RECORDS, GAME, RVA = 0x900004, 0x90002c, 0x100000, 0x348EC88
ROW = 7


class EmsRadiusTest(unittest.TestCase):
    def setup(self, radii=(1.0, 10.0, 12.0), menu=True, saved=None, live=False):
        lua = LuaRuntime(encoding=None, unpack_returned_tuples=True)
        module = lua.execute((build.HERE / 'ems_radius.lua').read_bytes())
        rows = bytearray(422 * 152)
        if live:
            rows[ROW * 152:(ROW + 1) * 152] = (build.HERE / 'reference_ems_explosion.bin').read_bytes()
        else:
            struct.pack_into('<II8x3f', rows, ROW * 152, 180, 451, *radii)
        struct.pack_into('<II', rows, 3 * 152, 154, 1)
        header = struct.pack('<IIII8xQQ', 0x444c444c, 1, build.dlhash('ExplosionSettings'), 67800, RECORDS, 422)
        self.memory = {HEADER: bytearray(header + bytes(rows)), GAME + RVA: bytearray(struct.pack('<Q', HEADER - 4))}
        self.writes = []
        def read(a, n):
            for base, b in self.memory.items():
                if base <= a and a + n <= base + len(b): return bytes(b[a - base:a - base + n])
        def write(a, b):
            for base, data in self.memory.items():
                if base <= a and a + len(b) <= base + len(data):
                    data[a - base:a - base + len(b)] = b; self.writes.append(a); return True
            return False
        api = lua.table_from({b'read': read, b'read_module': read, b'write': write,
                              b'pointer': lambda b: struct.unpack('<Q', b)[0] if b and len(b) == 8 else None})
        hit = lua.table_from({b'header': HEADER, b'header_bytes': header, b'records': RECORDS, b'count': 422,
                              b'stride': 152, b'pointer_rva': RVA, b'data': bytes(rows)})
        settings = lua.table_from({b'status': b'COMPLETE', b'hits': lua.table_from({b'explosion': lua.table_from([hit])})})
        g = lua.globals()
        lua.execute(b"""specs,callbacks,saved={},{},{}
         menu={api=1,register_option=function(id,spec)specs[id]=spec;return true end,
          get=function(id)return saved[id] or specs[id].default end,on_change=function(id,fn)callbacks[id]=fn end}""")
        for k, v in (saved or {}).items(): g.saved[k] = v
        if menu: g.ModOptionsMenu = g.menu
        self.lua = lua
        return module.new(api, settings, GAME)

    def radii(self):
        return struct.unpack_from('<3f', self.memory[HEADER], 40 + ROW * 152 + 16)

    def run_frames(self, s, n=60):
        for _ in range(n): s.step(s)

    def test_default_half_and_menu_choices(self):
        s = self.setup(); self.run_frames(s)
        spec = self.lua.globals().specs[ID]
        self.assertEqual(list(spec.choices.values()), [b'50%', b'100%'])
        self.assertEqual(spec.default, 1)
        self.assertIn(b'EMS mortar', spec.description)
        self.assertIn(b'field effect', spec.description)
        self.assertEqual(s.status, b'APPLIED'); self.assertEqual(self.radii(), (0.5, 5.0, 6.0))
        self.assertEqual(self.writes, [RECORDS + ROW * 152 + 16])

    def test_every_choice_scales_only_radii_and_restores(self):
        s = self.setup(); self.run_frames(s)
        before = bytes(self.memory[HEADER])
        for index, percent in [(2, 100), (1, 50), (2, 100), (1, 50)]:
            self.lua.globals().callbacks[ID](index)
            self.run_frames(s)
            f = struct.unpack('<3f', struct.pack('<3f', 1 * (percent / 100), 10 * (percent / 100), 12 * (percent / 100)))
            self.assertEqual(self.radii(), f)
            now = bytes(self.memory[HEADER]); o = 40 + ROW * 152
            self.assertEqual(now[:o + 16] + now[o + 28:], before[:o + 16] + before[o + 28:])
        s.stop(s)
        self.assertEqual(s.status, b'RESTORED'); self.assertEqual(self.radii(), (1.0, 10.0, 12.0))

    def test_saved_full_size_writes_nothing(self):
        s = self.setup(saved={ID: 2}); self.run_frames(s, 120)
        self.assertEqual(s.status, b'READY'); self.assertEqual(self.writes, [])
        s.stop(s); self.assertEqual(self.writes, [])

    def test_without_menu_uses_half(self):
        s = self.setup(menu=False); self.run_frames(s)
        self.assertEqual(self.radii(), (0.5, 5.0, 6.0))

    def test_non_vanilla_radius_refused(self):
        s = self.setup(radii=(10.0, 25.0, 35.0)); self.run_frames(s)
        self.assertEqual(s.status, b'EMS_RADIUS_NOT_VANILLA_NO_WRITE'); self.assertEqual(self.writes, [])

    def test_external_change_stops_and_is_not_restored(self):
        s = self.setup(); self.run_frames(s)
        struct.pack_into('<f', self.memory[HEADER], 40 + ROW * 152 + 16, 7.0)
        count = len(self.writes)
        self.lua.globals().callbacks[ID](2); self.run_frames(s)
        self.assertEqual(s.status, b'EMS_RADIUS_CHANGED_NO_WRITE'); self.assertEqual(len(self.writes), count)
        s.stop(s); self.assertEqual(len(self.writes), count)

    def test_invalid_values_rejected(self):
        s = self.setup(); self.run_frames(s)
        for v in [0, 30, 70, 101, b'50']: self.assertFalse(s.set_percent(s, v)[0])
        self.lua.globals().callbacks[ID](0); self.lua.globals().callbacks[ID](3)
        self.assertEqual(s.percent, 50)

    def test_live_captured_record_is_accepted_and_only_radii_change(self):
        # reference_ems_explosion.bin: type 180 read from the running game (build 2e2c3b7c...).
        live = (build.HERE / 'reference_ems_explosion.bin').read_bytes()
        self.assertEqual(struct.unpack_from('<II', live), (180, 451))
        self.assertEqual(struct.unpack_from('<3f', live, 16), (1.0, 10.0, 12.0))
        s = self.setup(live=True); self.run_frames(s)
        self.assertEqual(s.status, b'APPLIED')
        row = bytes(self.memory[HEADER][40 + ROW * 152:40 + (ROW + 1) * 152])
        self.assertEqual(struct.unpack_from('<3f', row, 16), (0.5, 5.0, 6.0))
        self.assertEqual(row[:16] + row[28:], live[:16] + live[28:])
        s.stop(s)
        self.assertEqual(bytes(self.memory[HEADER][40 + ROW * 152:40 + (ROW + 1) * 152]), live)


if __name__ == '__main__':
    unittest.main()
