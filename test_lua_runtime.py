"""Run the projectile policy against bounded simulated game memory."""
import gzip
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent.parent / 'test-deps'))
from lupa.luajit21 import LuaRuntime

import build


def ems_spear(spear, ems):
    row=bytearray(spear)
    struct.pack_into('<II',row,0,343,struct.unpack_from('<I',spear,4)[0])
    struct.pack_into('<I',row,60,67)
    row[156:160]=ems[156:160]
    return bytes(row)


def pointer(value):
    return struct.pack('<Q', value)


class ProjectilePolicyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = gzip.decompress(build.SAMPLE.read_bytes())
        cls.mapping, cls.jar_index, cls.jar = build.component(
            data, 'ProjectileWeaponComponentData', 8672, 616, build.DOMINATOR)
        _, cls.bolt_index, cls.bolt = build.component(
            data, 'ProjectileWeaponComponentData', 8672, 616, build.BOLT_CANDIDATE)
        cls.file = build.PROJECTILES.read_bytes()
        current = build.LIVE_PROJECTILES.read_bytes()
        cls.references = {343: current[:272], 125: current[272:]}
        rows = bytearray((Path(__file__).parent / 'reference_projectile_table.bin').read_bytes())
        damage = (Path(__file__).parent / 'reference_damage_current.bin').read_bytes()
        cls.damage_original, cls.damage_source = damage[:76], damage[76:]
        modified = bytearray(cls.damage_source)
        struct.pack_into('<7I', modified, 0, 67,163,69,3,3,3,3)
        cls.damage_target = bytes(modified)
        cls.damages = (Path(__file__).parent / 'reference_damage_table.bin').read_bytes()
        for offset in range(0, len(rows), 272):
            kind = struct.unpack_from('<I', rows, offset)[0]
            if kind in cls.references:
                rows[offset:offset + 272] = cls.references[kind]
        cls.records = bytes(rows)

    def run_policy(self, tables, fail_write=False, alias=False, shared=False, fail_projectile=False, duplicate_damage=False, ems=False, enabled=False, direct=False, wrong_build=False, icons=False):
        lua = LuaRuntime(unpack_returned_tuples=True, encoding=None)
        module = lua.execute((Path(__file__).parent / 'projectile_sync.lua').read_bytes())
        memory = lua.table()
        def add(base, data):
            memory[len(memory) + 1] = lua.table_from({b'base': base, b'data': data})
        owner, component_table = 0x200000, 0x300000
        add(0x100100, pointer(owner))
        add(owner + 0xF10000, pointer(component_table))
        components = bytearray(self.mapping + bytes(252 * 616))
        components[len(self.mapping) + self.jar_index * 616:len(self.mapping) + (self.jar_index + 1) * 616] = self.jar
        components[len(self.mapping) + self.bolt_index * 616:len(self.mapping) + (self.bolt_index + 1) * 616] = self.bolt
        add(component_table, bytes(components))
        for index in range(tables):
            header_address = 0x400000 + index * 0x100000
            records_address = 0x420000 if alias else header_address + 0x20000
            header = bytearray(self.file[4:44])
            struct.pack_into('<I',header,12,16+len(self.records))
            struct.pack_into('<Q', header, 24, records_address)
            struct.pack_into('<Q', header, 32, len(self.records) // 272)
            if direct:
                add(records_address-40,bytes(header)+self.records)
                add(0x100000+0x348E2F8,pointer(records_address-44))
            else:
                region = bytearray(131072)
                region[1000:1040] = header
                add(header_address, bytes(region))
                if not alias or index == 0:
                    add(records_address, self.records)
        if shared:
            for index in range(0, len(self.records), 272):
                if struct.unpack_from('<I', self.records, index)[0] == 300:
                    row = bytearray(self.records[index:index+272])
                    struct.pack_into('<I', row, 60, 67)
                    memory[len(memory)].data = self.records[:index] + bytes(row) + self.records[index+272:]
                    break
        import build
        for n in range(2 if duplicate_damage else 1):
            base = 0x800000 + n*0x100000
            header = struct.pack('<IIII8xQQ',0x444c444c,1,build.dlhash('DamageSettings'),16+len(self.damages),base+0x20000,len(self.damages)//76)
            if direct:
                add(base+0x20000-40,header+self.damages)
                add(0x100000+0x348E1F8,pointer(base+0x20000-100))
            else:
                region = bytearray(65536);region[100:140]=header
                add(base,bytes(region));add(base+0x20000,self.damages)
        if direct:
            header=struct.pack('<IIII8xQQ',0x444c444c,1,build.dlhash('ExplosionSettings'),67800,0xA0002C,422)
            add(0xA00004,header+bytes(422*152))
            add(0x100000+0x348EC88,pointer(0xA00000))
        lua.globals().segments = memory
        lua.execute(b'''
            local function read(at,n)
                for _,part in ipairs(segments) do
                    local offset=at-part.base
                    if offset>=0 and offset+n<=#part.data then
                        return part.data:sub(offset+1,offset+n)
                    end
                end
            end
            local function pointer(bytes)
                if not bytes or #bytes~=8 then return nil end
                local value=0
                for i=8,1,-1 do value=value*256+bytes:byte(i) end
                return value~=0 and value or nil
            end
            api={read=read,read_blob=read,pointer=pointer,excluded=function()return false end,
                query=function(cursor)
                    local first
                    for _,part in ipairs(segments) do
                        if part.base+#part.data>cursor and (not first or part.base<first.base) then first=part end
                    end
                    if not first then return nil,'end' end
                    return {base=first.base,size=#first.data,readable=true,kind=0x20000}
                end,
                write=function(at,bytes)
                    if #bytes~=72 and #bytes~=268 then return false,'invalid_size' end
                    for _,part in ipairs(segments) do
                        local offset=at-part.base
                        if offset>=0 and offset+#bytes<=#part.data then
                            part.data=part.data:sub(1,offset)..bytes..part.data:sub(offset+#bytes+1)
                            return true
                        end
                    end
                    return false,'missing_address'
                end}
        ''')
        if fail_write:
            lua.execute(b"api.write=function()return false,'synthetic_failure' end")
        if fail_projectile:
            lua.execute(b"local previous=api.write;api.write=function(at,bytes)if #bytes==268 then return false,'projectile_failure' end return previous(at,bytes)end")
        spec = lua.table_from({
            b'game': 0x100000, b'owner_rva': 0x100,
            b'scan_begin': 0xF10000, b'scan_end': 0xF10008,
            b'component_probe_offset': 0, b'component_map': self.mapping,
            b'jar_component': self.jar, b'bolt_component': self.bolt,
            b'jar_projectile': self.references[343],
            b'bolt_projectile': self.references[125],
            b'damage_original': self.damage_original,b'damage_source':self.damage_source,b'damage_target':self.damage_target,
        })
        policy = module.new(lua.globals().api, spec)
        if ems:
            spec.ems_projectile=(Path(__file__).parent/'reference_ems_projectile.bin').read_bytes()
        if direct:
            lua.execute(b'api.read_module=api.read')
            locator=lua.execute((Path(__file__).parent.parent.parent/'GL28-Adaptive-Boost/gl28_settings_locator.lua').read_bytes())
            settings=locator.new(lua.globals().api,0x100000,b'unknown' if wrong_build else b'2e2c3b7c2500646dadd5f2b4c6e0504dbb7e7896139f64cddc0d1813c718f51e')
            settings.start(settings);spec.settings=settings
        if icons:
            spec.gas_icon=struct.pack('<Q',0x3B975896BC689499)
            spec.ems_icon=struct.pack('<Q',0x2D9268907FB9420E)
        policy.set_ems(policy,enabled)
        policy.start(policy)
        self.peak_reads=0
        for _ in range(2000):
            before=policy.reads
            policy.step(policy)
            self.peak_reads=max(self.peak_reads,policy.reads-before)
            if policy.status in (b'APPLIED_P35_ONLY_DAMAGE_163_69_AP3',
                                 b'AMBIGUOUS_PROJECTILE_TABLES_NO_WRITE',
                                 b'PROJECTILE_TABLE_NOT_FOUND_NO_WRITE',
                                 b'WRITE_FAILED_ROLLED_BACK'):
                break
        self.runtime = lua
        return policy

    def test_direct_settings_apply_without_process_scan(self):
        policy=self.run_policy(1,ems=True,enabled=True,direct=True)
        self.assertEqual(policy.status,b'APPLIED_P35_ONLY_DAMAGE_163_69_AP3')
        self.assertLess(policy.frames,220)
        self.assertIsNone(policy.regions)
        self.assertEqual(policy.reads,2)
        policy.set_ems(policy,False)
        for _ in range(60):policy.step(policy)
        self.assertEqual(policy.lease.modified,policy.lease.gas)
        policy.stop(policy)
        self.assertEqual(policy.status,b'RESTORED_ON_SHUTDOWN')

    def test_direct_settings_unknown_build_refuses_writes(self):
        policy=self.run_policy(1,ems=True,direct=True,wrong_build=True)
        self.assertEqual(policy.status,b'DIRECT_SETTINGS_UNVERIFIED_GAME_BUILD_NO_WRITE')
        self.assertEqual(policy.writes,0)

    def test_ems_toggle_preserves_sources_and_restores_p35(self):
        policy=self.run_policy(1,ems=True)
        read=self.runtime.globals().api.read
        offset=next(i for i in range(0,len(self.records),272) if struct.unpack_from('<I',self.records,i)[0]==343)
        address=0x420000+offset
        gas=read(address,272)
        ems=(Path(__file__).parent/'reference_ems_projectile.bin').read_bytes()
        for enabled in (True,False,True):
            policy.set_ems(policy,enabled)
            for _ in range(60):policy.step(policy)
            self.assertEqual(policy.status,b'APPLIED_P35_ONLY_DAMAGE_163_69_AP3')
            self.assertEqual(read(address,272),ems_spear(self.references[125],ems) if enabled else gas)
            expected=bytearray(self.records);expected[offset:offset+272]=read(address,272)
            self.assertEqual(read(0x420000,len(expected)),bytes(expected))
        policy.stop(policy)
        self.assertEqual(read(0x420000,len(self.records)),self.records)
        self.assertEqual(read(0x820000,len(self.damages)),self.damages)

    def test_halt_icons_follow_p35_mode_without_changing_donors(self):
        policy=self.run_policy(1,ems=True,direct=True,icons=True)
        self.assertEqual(policy.lease.modified[16:24],struct.pack('<Q',0x3B975896BC689499))
        policy.set_ems(policy,True)
        policy.step(policy)
        self.assertEqual(policy.lease.modified[16:24],struct.pack('<Q',0x2D9268907FB9420E))
        read=self.runtime.globals().api.read
        self.assertEqual(read(policy.lease.source.address,272),self.references[125])
        self.assertEqual(read(policy.lease.ems.address,272),(Path(__file__).parent/'reference_ems_projectile.bin').read_bytes())
        address=policy.lease.target.address
        policy.stop(policy)
        self.assertEqual(read(address,272),self.references[343])

    def test_ems_keeps_complete_spear_behavior_except_delayed_explosion(self):
        policy=self.run_policy(1,ems=True,direct=True)
        gas=policy.lease.modified
        policy.set_ems(policy,True)
        policy.step(policy)
        row=policy.lease.modified
        self.assertEqual(row[:156],gas[:156])
        self.assertEqual(row[160:],gas[160:])
        self.assertEqual(struct.unpack_from('<I',row,156)[0],180)
        self.assertEqual(struct.unpack_from('<I',row,144)[0],0)
        self.assertEqual(struct.unpack_from('<f',row,152)[0],0.5)
        self.assertEqual(struct.unpack_from('<I',row,60)[0],67)

    def test_saved_ems_applies_at_start(self):
        policy=self.run_policy(1,ems=True,enabled=True)
        offset=next(i for i in range(0,len(self.records),272) if struct.unpack_from('<I',self.records,i)[0]==343)
        ems=(Path(__file__).parent/'reference_ems_projectile.bin').read_bytes()
        actual=self.runtime.globals().api.read(0x420000+offset,272)
        self.assertEqual(actual,ems_spear(self.references[125],ems))
        self.assertEqual(struct.unpack_from('<4f',actual,32),(300.0,100.0,4.0,1.0))

    def test_ems_switch_refuses_changed_p35(self):
        policy=self.run_policy(1,ems=True)
        offset=next(i for i in range(0,len(self.records),272) if struct.unpack_from('<I',self.records,i)[0]==343)
        api=self.runtime.globals().api
        row=api.read(0x420000+offset,272)
        api.write(0x420000+offset+4,row[4:32]+b'xxxx'+row[36:])
        before=api.read(0x420000,len(self.records))
        policy.set_ems(policy,True)
        for _ in range(60):policy.step(policy)
        self.assertEqual(policy.status,b'MODE_CONTEXT_CHANGED_RESTART_REQUIRED')
        self.assertEqual(api.read(0x420000,len(self.records)),before)

    def test_menu_default_saved_choice_and_apply_switch(self):
        policy=self.run_policy(1,ems=True)
        lua=self.runtime
        lua.execute(b"ModOptionsMenu={api=1,register_option=function(id,spec) menu_spec=spec;return true end,get=function()return saved_ems or menu_spec.default end,on_change=function(id,fn)ems_change=fn end}")
        module=lua.execute((Path(__file__).parent/'projectile_menu.lua').read_bytes())
        menu=module.new(policy);menu.step(menu)
        self.assertFalse(policy.ems_enabled)
        self.assertEqual(menu.status,b'REGISTERED')
        lua.globals().ems_change(2)
        for _ in range(60):policy.step(policy)
        self.assertTrue(policy.ems_enabled)
        ems=(Path(__file__).parent/'reference_ems_projectile.bin').read_bytes()
        self.assertEqual(policy.lease.modified[4:],ems_spear(self.references[125],ems)[4:])
        lua.globals().ems_change(1)
        for _ in range(60):policy.step(policy)
        self.assertEqual(policy.lease.modified,policy.lease.gas)
        lua.globals().saved_ems=2
        menu=module.new(policy);menu.step(menu)
        self.assertTrue(policy.ems_enabled)

    def test_unique_table_applies(self):
        policy = self.run_policy(1)
        self.assertEqual(policy.status, b'APPLIED_P35_ONLY_DAMAGE_163_69_AP3')
        self.assertEqual(policy.writes, 2)
        self.assertLessEqual(self.peak_reads,6)
        read = self.runtime.globals().api.read
        target_offset = next(i for i in range(0, len(self.records), 272)
                             if struct.unpack_from('<I', self.records, i)[0] == 343)
        source_offset = next(i for i in range(0, len(self.records), 272)
                             if struct.unpack_from('<I', self.records, i)[0] == 125)
        self.assertEqual(read(0x420000 + target_offset, 272),
                         struct.pack('<I', 343) + self.references[125][4:60] + struct.pack('<I',67) + self.references[125][64:])
        self.assertEqual(read(0x420000 + source_offset, 272), self.references[125])
        self.assertEqual(struct.unpack_from('<fI', read(0x420000 + target_offset, 272), 152), (0.5, 97))
        damage_offset=next(i for i in range(0,len(self.damages),76) if struct.unpack_from('<I',self.damages,i)[0]==67)
        expected=bytearray(self.damages);expected[damage_offset:damage_offset+76]=self.damage_target
        self.assertEqual(read(0x820000,len(self.damages)),bytes(expected))
        policy.stop(policy)
        self.assertEqual(read(0x820000,len(self.damages)),self.damages)
        self.assertEqual(read(0x420000 + target_offset, 272), self.references[343])
        self.assertEqual(policy.status, b'RESTORED_ON_SHUTDOWN')

    def test_write_failure_does_not_apply(self):
        policy = self.run_policy(1, fail_write=True)
        self.assertEqual(policy.status, b'DAMAGE_WRITE_FAILED')
        self.assertEqual(policy.writes, 0)

    def test_duplicate_table_refuses_write(self):
        policy = self.run_policy(2)
        self.assertEqual(policy.status, b'AMBIGUOUS_PROJECTILE_TABLES_NO_WRITE')
        self.assertEqual(policy.writes, 0)

    def test_alias_headers_share_one_table(self):
        policy = self.run_policy(2, alias=True)
        self.assertEqual(policy.status, b'APPLIED_P35_ONLY_DAMAGE_163_69_AP3')
        self.assertEqual(policy.aliases, 1)
        self.assertGreaterEqual(policy.cache_hits,1)
        self.assertEqual(policy.writes, 2)

    def test_shared_damage_id_refuses_write(self):
        policy=self.run_policy(1,shared=True)
        self.assertEqual(policy.status,b'PROJECTILE_TABLE_NOT_FOUND_NO_WRITE')
        self.assertEqual(policy.writes,0)

    def test_damage_table_ambiguity_refuses_write(self):
        policy=self.run_policy(1,duplicate_damage=True)
        self.assertEqual(policy.status,b'AMBIGUOUS_DAMAGE_TABLES_NO_WRITE')
        self.assertEqual(policy.writes,0)

    def test_projectile_failure_restores_damage(self):
        policy=self.run_policy(1,fail_projectile=True)
        self.assertEqual(policy.status,b'WRITE_FAILED_ROLLED_BACK')
        self.assertEqual(self.runtime.globals().api.read(0x820000,len(self.damages)),self.damages)

    def test_production_api_accepts_damage_write_length(self):
        lua=LuaRuntime(unpack_returned_tuples=True,encoding=None)
        # Reach the real size gate without executing Windows calls: region rejects
        # this intentionally invalid address only after length acceptance.
        source=(Path(__file__).parent / 'windows_api.lua').read_bytes()
        factory=lua.execute(source)
        api=factory()
        ok,reason=api.write(0,b'x'*72)
        self.assertFalse(ok)
        self.assertEqual(reason,b'not_plain_data_page')
        ok,reason=api.write(0,b'x'*73)
        self.assertFalse(ok)
        self.assertEqual(reason,b'invalid_size')

    def test_missing_table_refuses_write(self):
        policy = self.run_policy(0)
        self.assertEqual(policy.status, b'PROJECTILE_TABLE_NOT_FOUND_NO_WRITE')
        self.assertEqual(policy.writes, 0)


if __name__ == '__main__':
    unittest.main()
