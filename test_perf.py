"""Steady-state cost of the complete entry with the P-35 held (simulated memory)."""
import json
from pathlib import Path
import struct
import unittest
import test_startup
import build

HERE = Path(__file__).resolve().parent
MODULES = [(b'bolt_locator', 'locator.lua'), (b'magazine_menu', 'magazine_menu.lua'),
           (b'projectile_sync', 'projectile_sync.lua'), (b'native_ammo_menu', 'native_ammo_menu.lua'),
           (b'grenade_pistol', 'grenade_pistol.lua'), (b'fixed_projectile', 'fixed_projectile.lua'),
           (b'ems_radius', 'ems_radius.lua'), (b'ems_visual', 'ems_visual.lua')]
BASELINE = Path(__file__).resolve().parent.parent  # preview10, which still drives GP-31
STEADY = 3600


def measure(source):
    t = test_startup.StartupTest()
    lua = t.setup_runtime()
    g = lua.globals()
    for name, file in MODULES:
        if (source / file).exists():
            g[name] = lua.execute((source / file).read_bytes())
    memory = t.memory

    def add(a, b): memory[a] = bytearray(b)
    def pointer(a, v): add(a, struct.pack('<Q', v))
    def mapping(a, key, index, base):
        add(a, struct.pack('<QIII', base, 1, 0xffffffff, 1)); add(base, struct.pack('<II', key, index))
    game, owner = 0x100000, 0x200000
    player, inventory, manager = 0xA00000, 0xA10000, 0xA20000
    pointer(game + 0x3326468, player); pointer(game + 0x3326738, inventory); pointer(game + 0x3326CE0, manager)
    add(player + 0x3A8, struct.pack('<I', 101))
    avatar = struct.pack('<QIIII', 99, 102, 101, 0, 0)
    weapon = struct.pack('<QIIII', build.DOMINATOR, 103, 104, 0, 0)
    mapping(owner + 0xF21A88, 101, 0, 0xA30000); add(owner + 0xF31AD8, avatar)
    mapping(owner + 0xF19A70, 103, 1, 0xA30100); add(owner + 0xF31AD8 + 24, weapon)
    mapping(inventory + 40, 102, 0, 0xA30200); pointer(inventory + 64, 0xA30300); pointer(0xA30300, owner + 0xF31AD8)
    pointer(inventory + 80, 0xA30400); add(0xA30400, struct.pack('<12I', 0, 103, 0, 0, 3, 6, 2, 2, 0, 0, 0, 0))
    mapping(manager + 48, 103, 0, 0xA30500); pointer(manager + 88, 0xA30600); pointer(manager + 96, 0xA30A00)
    add(0xA30600, bytes(1008)); add(0xA30A00, bytes(12))
    opens = [0]
    def open_log(name):
        opens[0] += 1
        return None
    g.CowboyBingusModLoader.open_log = open_log
    lua.execute((source / 'entry.lua').read_bytes())
    state = g.TongzP35GasSpeargun
    for _ in range(200):
        g.update()
    ready = state[b'ready_frame']
    t.reads = 0; opens[0] = 0
    for _ in range(STEADY):
        assert g.update() == 123
    menu = state[b'projectile_menu'][b'status']
    result = {'ready_frame': ready, 'steady_reads': t.reads, 'reads_per_update': t.reads / STEADY,
              'log_opens': opens[0], 'menu': menu.decode(), 'status': state[b'status'].decode(),
              'instance_menu_installed': bytes(memory[0xA30600][0x350:0x354]) == struct.pack('<I', 8)}
    g.shutdown()
    return result


class SteadyStateTest(unittest.TestCase):
    def test_steady_state_is_cheaper_than_preview10(self):
        before, after = measure(BASELINE), measure(HERE)
        for r in (before, after):
            self.assertEqual(r['status'], 'APPLYING')
            self.assertEqual(r['menu'], 'NATIVE_GAS')
            self.assertTrue(r['instance_menu_installed'])
        self.assertLess(after['ready_frame'], 65)
        self.assertLess(after['reads_per_update'], before['reads_per_update'] / 5)
        self.assertEqual(after['log_opens'], 0)
        (HERE / 'steady-state-evidence.json').write_text(
            json.dumps({'updates': STEADY, 'preview10': before, 'preview12': after}, indent=1))


if __name__ == '__main__':
    unittest.main()
