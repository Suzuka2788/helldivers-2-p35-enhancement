"""Build the guarded P-35 native gas speargun settings preview."""
from pathlib import Path
import gzip
import importlib.util
import json
import struct
import sys
import zipfile

HERE = Path(__file__).resolve().parent
DEV = Path(r'C:\Users\tongz\OneDrive\Desktop\26.9 Helldiver2 Mod开发')
SAMPLE = DEV / '.research/generated_entities.current.dl_bin.gz'
PROJECTILES = DEV / '.research/filediver-current/datalibrary/generated_projectile_settings.dl_bin'
LIVE_PROJECTILES = HERE / 'reference_projectiles_current.bin'
HELPER = DEV / '.research/BingusSharedLoader/scripts/build_addon.py'
ROOT = DEV / 'mod'
OUT = HERE / 'Suzukas-P35-enhancement-v1.1.0.zip'
RESOURCE = 'mods/tongz/p35_gas_speargun'
GUID = 'b5212072-a28e-463b-bad8-f426012a6135'
DOMINATOR = 0x0B882808C6F498E8
BOLT_CANDIDATE = 0x3828E2051AA9E897
sys.path.insert(0, str(ROOT / 'scripts'))
from build_capacity import dlhash


def component(data, name, map_size, stride, identity):
    signature = struct.pack('<III', 0x444C444C, 1, dlhash(name))
    assert data.count(signature) == 1, name
    at = data.index(signature)
    size = struct.unpack_from('<I', data, at + 12)[0]
    body = data[at + 24:at + 24 + size]
    assert len(body) == size and (size - map_size) % stride == 0
    mapping = body[:map_size]
    key = struct.pack('<Q', identity)
    assert mapping.count(key) == 1, (name, hex(identity))
    entry = mapping.index(key)
    assert entry % 16 == 0
    index, zero = struct.unpack_from('<II', mapping, entry + 8)
    assert zero == 0 and index < (size - map_size) // stride
    row = body[map_size + index * stride:map_size + (index + 1) * stride]
    return mapping, index, row


def projectile(data, type_id):
    assert data[4:8] == b'LDLD'
    assert (len(data) - 44) % 272 == 0
    matches = [data[44 + i * 272:44 + (i + 1) * 272]
               for i in range((len(data) - 44) // 272)
               if struct.unpack_from('<I', data, 44 + i * 272)[0] == type_id]
    assert len(matches) == 1, type_id
    return matches[0]


def wrap(path, var):
    return f'local {var}=(function()\n' + path.read_text(encoding='utf-8') + '\nend)()\n'


def build():
    entities = gzip.decompress(SAMPLE.read_bytes())
    mapping, index, jar = component(entities, 'ProjectileWeaponComponentData', 8672, 616, DOMINATOR)
    _, bolt_index, bolt = component(entities, 'ProjectileWeaponComponentData', 8672, 616, BOLT_CANDIDATE)
    assert (index, *struct.unpack_from('<Ifff', jar)) == (229, 343, 0.0, 110.0, 0.0)
    assert (bolt_index, *struct.unpack_from('<Ifff', bolt)) == (251, 125, 0.0, 60.0, 0.0)
    mag_map, mag_index, mag_row = component(entities, 'WeaponMagazineComponentData', 8640,160,DOMINATOR)
    # capacity, magazines, refill, max, reload threshold, chambered
    assert struct.unpack_from('<6I',mag_row,136)==(6,2,2,2,6,0)
    weapon_map, weapon_index, weapon_row = component(entities, 'WeaponDataComponentData', 11680, 1232, DOMINATOR)
    assert struct.unpack_from('<2I',weapon_row,184)==(0,0)
    projectile_data = PROJECTILES.read_bytes()
    assert struct.unpack_from('<I', projectile(projectile_data, 343))[0] == 343
    assert struct.unpack_from('<I', projectile(projectile_data, 125))[0] == 125
    live = LIVE_PROJECTILES.read_bytes()
    assert len(live) == 544
    jar_round, bolt_round = live[:272], live[272:]
    assert struct.unpack_from("<I", jar_round)[0] == 343
    assert struct.unpack_from("<I", bolt_round)[0] == 125
    assert struct.unpack_from('<fI', bolt_round, 152) == (0.5, 97)
    damage_live = (HERE / 'reference_damage_current.bin').read_bytes()
    assert len(damage_live) == 152
    original_damage, spear_damage = damage_live[:76], damage_live[76:]
    assert struct.unpack_from('<I', original_damage)[0] == 67
    assert struct.unpack_from('<7I', spear_damage) == (65,650,275,5,5,5,5)
    target_damage = bytearray(spear_damage)
    struct.pack_into('<7I', target_damage, 0, 67,163,69,3,3,3,3)
    source = '-- HD2-Addon: ' + RESOURCE + '\n'
    for path, var in [
        (ROOT / 'src/layout_resolver.lua', 'layout_resolver'),
        (HERE.parent.parent/'GL28-Adaptive-Boost/gl28_settings_locator.lua','settings_locator'),
        (HERE / 'locator.lua', 'bolt_locator'),
        (HERE / 'magazine_menu.lua', 'magazine_menu'),
        (HERE / 'native_ammo_menu.lua', 'native_ammo_menu'),
        (HERE / 'fixed_projectile.lua', 'fixed_projectile'),
        (HERE / 'projectile_sync.lua', 'projectile_sync'),
        (HERE / 'windows_api.lua', 'create_api'),
    ]:
        source += wrap(path, var)
    source += 'local function unhex(s)return(s:gsub("..",function(x)return string.char(tonumber(x,16))end))end\n'
    source += f'local ref={{map=unhex("{mapping.hex()}"),row=unhex("{jar.hex()}"),bolt=unhex("{bolt.hex()}"),bolt_id=unhex("{struct.pack("<Q", BOLT_CANDIDATE).hex()}"),jar_projectile=unhex("{jar_round.hex()}"),bolt_projectile=unhex("{bolt_round.hex()}")}}\n'
    source += f'ref.damage_original=unhex("{original_damage.hex()}");ref.damage_source=unhex("{spear_damage.hex()}");ref.damage_target=unhex("{target_damage.hex()}")\n'
    source += f'ref.mag_map=unhex("{mag_map.hex()}");ref.mag_row=unhex("{mag_row.hex()}");ref.mag_index={mag_index}\n'
    source += f'ref.weapon_map=unhex("{weapon_map.hex()}");ref.weapon_row=unhex("{weapon_row.hex()}");ref.weapon_index={weapon_index}\n'
    ems_round=(HERE/'reference_ems_projectile.bin').read_bytes()
    assert len(ems_round)==272 and struct.unpack_from('<I',ems_round)[0]==154
    source += f'ref.ems_projectile=unhex("{ems_round.hex()}")\n'
    # Copy only the HUD material IDs from Halt's two actual projectile records.
    _, _, halt = component(entities, 'WeaponRoundsComponentData', 800, 136, 0x4E310B1FE4C52B52)
    gas_type, ems_type = struct.unpack_from('<2I', halt, 64)
    assert (gas_type, ems_type) == (183, 191)
    current = (HERE / 'reference_projectile_table.bin').read_bytes()
    def icon(kind):
        row, = [current[i:i+272] for i in range(0,len(current),272)
                if struct.unpack_from('<I',current,i)[0] == kind]
        return row[16:24]
    gas_icon, ems_icon = icon(gas_type), icon(ems_type)
    assert struct.unpack('<Q',gas_icon)[0] == 0x3B975896BC689499
    assert struct.unpack('<Q',ems_icon)[0] == 0x2D9268907FB9420E
    source += f'ref.gas_icon=unhex("{gas_icon.hex()}");ref.ems_icon=unhex("{ems_icon.hex()}")\n'
    # Reserve rows not referenced by any current weapon's primary/alternate ammo.
    used=set()
    for name, map_size, stride, offsets in [('ProjectileWeaponComponentData',8672,616,(0,576)),('WeaponRoundsComponentData',800,136,(64,68))]:
        at=entities.index(struct.pack('<III',0x444c444c,1,dlhash(name)))
        size=struct.unpack_from('<I',entities,at+12)[0]
        body=entities[at+24+map_size:at+24+size]
        used.update(struct.unpack_from('<I',body,i*stride+o)[0] for i in range(len(body)//stride) for o in offsets)
    assert 332 not in used
    reserved={}
    for kind in (332,):
        row,=[current[o:o+272]for o in range(0,len(current),272)if struct.unpack_from('<I',current,o)[0]==kind]
        reserved[kind]=row
    source += f'ref.alternate_type=332;ref.alternate_original=unhex("{reserved[332].hex()}")\n'
    source += f'local jar_id=unhex("{struct.pack("<Q", DOMINATOR).hex()}")\n'
    source += (HERE / 'entry.lua').read_text(encoding='utf-8')
    payload = source.encode('utf-8')
    spec = importlib.util.spec_from_file_location('bsl_builder', HELPER)
    sys.path.insert(0, str(HELPER.parent))
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.build_addon(RESOURCE, payload, GUID, OUT, "Suzuka‘s P35 enhancement")
    from asset_pack import include_assets
    include_assets(OUT,RESOURCE,payload)
    with zipfile.ZipFile(OUT) as z:
        assert json.loads(z.read('manifest.json'))['Guid'] == GUID
        assert payload in z.read('Addon/9ba626afa44a3aa3.patch_0')
    with zipfile.ZipFile(OUT, 'a', compression=zipfile.ZIP_DEFLATED) as z:
        z.write(HERE / 'README-ems-preview.md', 'README.md')
        z.write(HERE / 'CODE_HUMANIZER_REVIEW.md', 'CODE_HUMANIZER_REVIEW.md')
        z.write(HERE / 'performance.json', 'performance.json')
    print(OUT)


if __name__ == '__main__':
    build()

