import json
import struct
import unittest
from test_lua_runtime import LuaRuntime
import asset_pack
import build

PARTICLE_AT = 0x4000080   # inside the second readable region, after unrelated data


def particle_spec():
    base = asset_pack.HERE / 'assets/ems_effect'
    name = json.loads((base / 'provenance.json').read_text())['source_archive']
    data = (base / name).read_bytes()
    row, = [r for r in asset_pack.resource_rows(data) if r[:2] == asset_pack.EMS_PARTICLE]
    original = data[row[2]:row[2] + row[7]]
    return original, asset_pack.shrink_ems_field(original)


def lua_spec(lua, baked):
    fields = lua.table_from([lua.table_from([o, lua.table_from(list(v))])
                             for o, v in sorted(asset_pack.EMS_FIELD_VALUES)])
    return lua.table_from({b'baked': baked, b'baked_percent': 50, b'fields': fields})


def install_memory(test, regions):
    """regions: {base: bytearray}. Gaps are reported as unreadable regions."""
    test.memory = regions
    test.writes = []
    def read(a, n):
        for base, b in test.memory.items():
            if base <= a and a + n <= base + len(b): return bytes(b[a - base:a - base + n])
    def write(a, b):
        for base, data in test.memory.items():
            if base <= a and a + len(b) <= base + len(data):
                data[a - base:a - base + len(b)] = b; test.writes.append((a, len(b))); return True
        return False
    def query(a):
        bases = sorted(test.memory)
        for base in bases:
            if base <= a < base + len(test.memory[base]):
                return test.lua.table_from({b'base': base, b'size': len(test.memory[base]), b'readable': True})
        nxt = [b for b in bases if b > a]
        if not nxt: return None, b'end'
        return test.lua.table_from({b'base': a, b'size': nxt[0] - a, b'readable': False})
    return test.lua.table_from({b'read': read, b'read_blob': read, b'write': write, b'query': query})


class EmsVisualTest(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(encoding=None, unpack_returned_tuples=True)
        self.original, self.baked = particle_spec()
        self.module = self.lua.execute((build.HERE / 'ems_visual.lua').read_bytes())
        self.radius = self.lua.table_from({b'percent': 50})

    def make(self, payload_at=PARTICLE_AT, payload=None):
        regions = {0x10000: bytearray(b'\x07' * 300000),
                   0x4000000: bytearray(0x200000)}
        payload = self.baked if payload is None else payload
        regions[0x4000000][payload_at - 0x4000000:payload_at - 0x4000000 + len(payload)] = payload
        api = install_memory(self, regions)
        return self.module.new(api, lua_spec(self.lua, self.baked), self.radius)

    def particle(self):
        return bytes(self.memory[0x4000000][PARTICLE_AT - 0x4000000:PARTICLE_AT - 0x4000000 + len(self.baked)])

    def expected(self, percent):
        out = bytearray(self.original)
        for o, values in asset_pack.EMS_FIELD_VALUES:
            struct.pack_into('<%df' % len(values), out, o, *(v * percent / 100 for v in values))
        return bytes(out)

    def run_frames(self, v, n):
        for _ in range(n): v.step(v)

    def test_finds_shipped_copy_and_follows_menu_percent(self):
        v = self.make(); self.run_frames(v, 10)
        self.assertEqual(v.status, b'SYNCED'); self.assertEqual(v.found, 1)
        self.assertEqual(self.writes, [])            # 50% is already shipped
        for percent in [30, 40, 60, 70, 80, 90, 100, 50]:
            self.radius.percent = percent; self.run_frames(v, 1)
            self.assertEqual(v.status, b'SYNCED'); self.assertEqual(self.particle(), self.expected(percent))
        self.assertEqual(self.expected(50), self.baked)
        self.assertEqual(self.expected(100), self.original)
        changed = {a - PARTICLE_AT for a, _ in self.writes}
        self.assertTrue(changed <= {o + 4 * k for o, vals in asset_pack.EMS_FIELD_VALUES for k in range(len(vals))})

    def test_restores_shipped_values_on_stop(self):
        v = self.make(); self.run_frames(v, 10)
        self.radius.percent = 30; self.run_frames(v, 1)
        v.stop(v)
        self.assertEqual(v.status, b'RESTORED'); self.assertEqual(self.particle(), self.baked)

    def test_unrelated_or_modified_copy_never_written(self):
        tampered = bytearray(self.baked); tampered[5000] ^= 1
        v = self.make(payload=bytes(tampered)); self.run_frames(v, 50)
        self.assertEqual(v.status, b'SCANNING'); self.assertEqual(self.writes, [])
        self.assertGreaterEqual(v.passes, 1)

    def test_rescans_when_resource_replaced(self):
        v = self.make(); self.run_frames(v, 10)
        self.radius.percent = 30; self.run_frames(v, 1)
        # The game reloads the package: same place, shipped bytes again.
        self.memory[0x4000000][PARTICLE_AT - 0x4000000:PARTICLE_AT - 0x4000000 + len(self.baked)] = self.baked
        self.run_frames(v, 300)
        self.assertEqual(v.status, b'SYNCED'); self.assertEqual(v.found, 2)
        self.assertEqual(self.particle(), self.expected(30))

    def test_external_change_is_not_overwritten(self):
        v = self.make(); self.run_frames(v, 10)
        self.memory[0x4000000][PARTICLE_AT - 0x4000000 + 10] ^= 1
        count = len(self.writes)
        self.radius.percent = 40; self.run_frames(v, 1)
        self.assertEqual(v.status, b'SCANNING'); self.assertEqual(len(self.writes), count)

    def test_match_across_scan_window_boundary(self):
        at = 0x4000000 + 262144 - 30          # needle straddles two 256 KiB windows
        regions = {0x4000000: bytearray(0x200000)}
        regions[0x4000000][at - 0x4000000:at - 0x4000000 + len(self.baked)] = self.baked
        api = install_memory(self, regions)
        v = self.module.new(api, lua_spec(self.lua, self.baked), self.radius)
        self.run_frames(v, 10)
        self.assertEqual(v.status, b'SYNCED')


if __name__ == '__main__':
    unittest.main()
