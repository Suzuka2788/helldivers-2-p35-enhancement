-- Preserve P-35 type 343 and copy native S-11 type 125 settings.
local M={}
local function hash(name)
    local h=5381
    for i=1,#name do h=(h*33+name:byte(i))%4294967296 end
    return (h-5381)%4294967296
end
local function pack(v)
    return string.char(v%256,math.floor(v/256)%256,
        math.floor(v/65536)%256,math.floor(v/16777216)%256)
end
local function u32(s,o)
    local a,b,c,d=s:byte(o+1,o+4);if not d then return nil end
    return a+b*256+c*65536+d*16777216
end
local function u64(s,o)
    local lo,hi=u32(s,o),u32(s,o+4)
    if not lo or not hi or hi>=32768 then return nil end
    return lo+hi*4294967296
end
local function similar(a,b)
    local same=0
    for i=1,#b do if a:byte(i)==b:byte(i) then same=same+1 end end
    return same/#b
end
local DAMAGE_SIGNATURE=pack(0x444C444C)..pack(1)..pack(hash('DamageSettings'))
local SIGNATURE=pack(0x444C444C)..pack(1)..pack(hash('ProjectileSettings'))
function M.new(api,spec)
    assert(#spec.component_map==8672 and #spec.jar_component==616
        and #spec.bolt_component==616,'reference_component_layout_invalid')
    assert(u32(spec.jar_component,0)==343 and u32(spec.bolt_component,0)==125,
        'reference_component_projectile_ids_invalid')
    assert(#spec.damage_original==76 and #spec.damage_source==76 and #spec.damage_target==76)
    local applied_status='APPLIED_P35_ONLY_DAMAGE_163_69_AP3'
    local s={status='IDLE',writes=0,reads=0,failures=0,ems_enabled=false}
    function s:set_ems(enabled)
        assert(type(enabled)=='boolean','invalid_ems_option')
        self.ems_enabled=enabled
    end
    local function pointer(address) return api.pointer(api.read(address,8)) end
    local function owner() return pointer(spec.game+spec.owner_rva) end
    local function component_map_matches(address)
        if not address then return false end
        local p=spec.component_probe_offset
        if api.read(address+p,32)~=spec.component_map:sub(p+1,p+32) then return false end
        for i=0,#spec.component_map-1,2048 do
            local chunk=spec.component_map:sub(i+1,i+2048)
            if api.read(address+i,#chunk)~=chunk then return false end
        end
        return true
    end
    local function component_context(lease)
        local bolt=api.read(lease.table+#spec.component_map+251*616,616)
        return owner()==lease.owner and pointer(lease.slot)==lease.table
            and component_map_matches(lease.table)
            and api.read(lease.table+#spec.component_map+229*616,616)==spec.jar_component
            and bolt==spec.bolt_component
    end
    local function find_component_context()
        local who=owner();if not who then return nil,'WAITING_FOR_ENTITY_MANAGER' end
        local found
        for index=0,(spec.scan_end-spec.scan_begin)/8-1 do
            local slot=who+spec.scan_begin+index*8
            local table_at=pointer(slot)
            if table_at and component_map_matches(table_at) then
                if found and found.table~=table_at then return nil,'AMBIGUOUS_COMPONENT_TABLES_NO_WRITE' end
                found={owner=who,slot=slot,table=table_at}
            end
        end
        if not found then return nil,'COMPONENT_TABLE_NOT_FOUND_NO_WRITE' end
        if not component_context(found) then return nil,'COMPONENT_RECORD_MISMATCH_NO_WRITE' end
        return found
    end
    local function read_blob(self,address,size)
        self.reads=self.reads+1
        local data=api.read_blob(address,size)
        if not data then self.failures=self.failures+1 end
        return data
    end
    local function table_blob(self,records,count,stride)
        local key=records..':'..count..':'..stride
        local cached=self.table_cache[key]
        if cached then self.cache_hits=self.cache_hits+1;return cached end
        local data=read_blob(self,records,count*stride)
        if data then self.table_cache[key]=data end
        return data
    end
    local function inspect_damage(self,base,window)
        local from=1
        while true do
            local i=window:find(DAMAGE_SIGNATURE,from,true);if not i then return end
            from=i+1
            local o=i-1
            local size,records,count=u32(window,o+12),u64(window,o+24),u64(window,o+32)
            if records and count and size and count>=600 and count<=900
                and size>=16+count*76 and size<=262144 and not api.excluded(records,count*76) then
                local blob=table_blob(self,records,count,76)
                if blob then
                    local target,source
                    for n=0,count-1 do
                        local row=blob:sub(n*76+1,(n+1)*76)
                        if u32(row,0)==67 then
                            if target then self.status='DUPLICATE_DAMAGE_ID_NO_WRITE';return end
                            target={address=records+n*76,bytes=row}
                        elseif u32(row,0)==65 then
                            if source then self.status='DUPLICATE_DAMAGE_ID_NO_WRITE';return end
                            source={address=records+n*76,bytes=row}
                        end
                    end
                    if target and source and target.bytes==spec.damage_original and source.bytes==spec.damage_source then
                        local alias=false
                        for _,prior in ipairs(self.damage_candidates) do
                            if prior.records==records then alias=true;break end
                        end
                        if not alias then
                            self.damage_candidates[#self.damage_candidates+1]={header=base+o,
                                header_bytes=window:sub(i,i+39),records=records,target=target,source=source}
                            if #self.damage_candidates>1 then self.status='AMBIGUOUS_DAMAGE_TABLES_NO_WRITE';return end
                        end
                    end
                end
            end
        end
    end
    local function inspect(self,base,window)
        local from=1
        while true do
            local i=window:find(SIGNATURE,from,true);if not i then return end
            from=i+1
            local off=i-1
            local size,records,count=u32(window,off+12),u64(window,off+24),u64(window,off+32)
            if size and records and count and count>=250 and count<=600
                and size>=16+count*272 and size<=262144
                and not api.excluded(records,count*272) then
                local data=table_blob(self,records,count,272)
                if data then
                    local target,source,ems
                    local damage_users=0
                    for n=0,count-1 do
                        local row=data:sub(n*272+1,(n+1)*272)
                        local kind=u32(row,0)
                        if u32(row,60)==67 and kind~=343 then damage_users=damage_users+1 end
                        if kind==343 then
                            if target then target=false;break end
                            target={address=records+n*272,bytes=row}
                        elseif kind==125 then
                            if source then source=false;break end
                            source={address=records+n*272,bytes=row}
                        elseif kind==154 and spec.ems_projectile then
                            if ems then ems=false;break end
                            ems={address=records+n*272,bytes=row}
                        end
                    end
                    if target and source and damage_users==0
                        and similar(target.bytes,spec.jar_projectile)>=0.97
                        and similar(source.bytes,spec.bolt_projectile)>=0.97
                        and u32(target.bytes,32)==u32(spec.jar_projectile,32)
                        and u32(source.bytes,32)==u32(spec.bolt_projectile,32)
                        and (not spec.ems_projectile or (ems
                            and similar(ems.bytes,spec.ems_projectile)>=0.97
                            and u32(ems.bytes,32)==u32(spec.ems_projectile,32))) then
                        local candidate={header=base+off,header_bytes=window:sub(i,i+39),
                            records=records,count=count,target=target,source=source,ems=ems}
                        local alias=false
                        for _,prior in ipairs(self.candidates) do
                            if prior.records==candidate.records and prior.count==candidate.count then
                                alias=true;self.aliases=self.aliases+1;break
                            end
                        end
                        if not alias then
                            self.candidates[#self.candidates+1]=candidate
                            if #self.candidates>1 then
                                self.status='AMBIGUOUS_PROJECTILE_TABLES_NO_WRITE';return
                            end
                        end
                    end
                end
            end
        end
    end
    local function runtime_context(self,lease)
        if spec.settings then
            local hits=spec.settings.hits
            local p,d=hits.projectile[1],hits.damage[1]
            if not p or not d
                or api.pointer(api.read_module(spec.game+p.pointer_rva,8))~=p.header-4
                or api.pointer(api.read_module(spec.game+d.pointer_rva,8))~=d.header-60 then return false end
        end
        return component_context(self.component_lease)
            and api.read(lease.header,40)==lease.header_bytes
            and api.read(lease.source.address,272)==lease.source.bytes
            and (not spec.ems_projectile or api.read(lease.ems.address,272)==lease.ems.bytes)
            and api.read(lease.damage.header,40)==lease.damage.header_bytes
            and api.read(lease.damage.source.address,76)==lease.damage.source.bytes
    end
    local function apply(self)
        if #self.candidates~=1 then self.status='PROJECTILE_TABLE_NOT_FOUND_NO_WRITE';return end
        if #self.damage_candidates~=1 then self.status='DAMAGE_TABLE_NOT_UNIQUE_NO_WRITE';return end
        local lease=self.candidates[1]
        lease.damage=self.damage_candidates[1]
        local current=api.read(lease.target.address,272)
        if current~=lease.target.bytes or not runtime_context(self,lease) then
            self.status='PROJECTILE_CONTEXT_CHANGED_NO_WRITE';return
        end
        if api.read(lease.damage.target.address,76)~=spec.damage_original then
            self.status='DAMAGE_CONTEXT_CHANGED_NO_WRITE';return
        end
        lease.gas=pack(343)..lease.source.bytes:sub(5,60)..pack(67)..lease.source.bytes:sub(65)
        if spec.ems_projectile then
            -- Preserve spear impact and delay behavior; change its delayed explosion.
            lease.electromagnetic=lease.gas:sub(1,156)
                ..lease.ems.bytes:sub(157,160)..lease.gas:sub(161)
        end
        if spec.gas_icon then
            assert(#spec.gas_icon==8 and #spec.ems_icon==8,'INVALID_AMMO_ICON')
            lease.gas=lease.gas:sub(1,16)..spec.gas_icon..lease.gas:sub(25)
            if lease.electromagnetic then
                lease.electromagnetic=lease.electromagnetic:sub(1,16)..spec.ems_icon..lease.electromagnetic:sub(25)
            end
        end
        local target=self.ems_enabled and lease.electromagnetic or lease.gas
        lease.modified=target
        self.lease=lease
        local damage_ok,damage_error=api.write(lease.damage.target.address+4,spec.damage_target:sub(5))
        if not damage_ok or api.read(lease.damage.target.address,76)~=spec.damage_target then
            self.status='DAMAGE_WRITE_FAILED';self.error=tostring(damage_error)
            if api.read(lease.damage.target.address,76)==spec.damage_target then
                api.write(lease.damage.target.address+4,spec.damage_original:sub(5))
            end
            return
        end
        lease.damage_written=true
        local write_address=lease.target.address+4
        local write_bytes=target:sub(5)
        local restore_bytes=lease.target.bytes:sub(5)
        lease.write_address=write_address;lease.restore_bytes=restore_bytes
        local ok,detail=api.write(write_address,write_bytes)
        local after=api.read(lease.target.address,272)
        if not ok or after~=target then
            self.status='WRITE_FAILED_OR_READBACK_MISMATCH';self.error=tostring(detail)
            if after==target and runtime_context(self,lease) then
                api.write(write_address,restore_bytes)
            end
            if api.read(lease.target.address,272)==lease.target.bytes then
                if runtime_context(self,lease) and api.read(lease.damage.target.address,76)==spec.damage_target then
                    api.write(lease.damage.target.address+4,spec.damage_original:sub(5))
                end
                self.status=api.read(lease.damage.target.address,76)==spec.damage_original and 'WRITE_FAILED_ROLLED_BACK' or 'ROLLBACK_NOT_CONFIRMED'
            end
            return
        end
        self.writes=2
        self.status=applied_status
    end
    function s:start()
        self.status='WAITING_TO_SCAN';self.frames=0;self.writes=0
        self.reads=0;self.failures=0;self.table_cache={};self.cache_hits=0;self.candidates={};self.damage_candidates={};self.aliases=0;self.lease=nil
    end
    function s:step()
        self.frames=self.frames+1
        if self.status==applied_status then
            do
                local lease=self.lease
                local desired=self.ems_enabled and lease.electromagnetic or lease.gas
                if not desired then self.status='EMS_REFERENCE_UNAVAILABLE_NO_WRITE';return end
                if desired~=lease.modified then
                    if not runtime_context(self,lease)
                        or api.read(lease.target.address,272)~=lease.modified
                        or api.read(lease.damage.target.address,76)~=spec.damage_target then
                        self.status='MODE_CONTEXT_CHANGED_RESTART_REQUIRED';return
                    end
                    local ok,why=api.write(lease.target.address+4,desired:sub(5))
                    local after=api.read(lease.target.address,272)
                    if after==desired then lease.modified=desired;self.writes=self.writes+1 end
                    if not ok or after~=desired then
                        self.status='MODE_WRITE_FAILED';self.error=tostring(why);return
                    end
                end
            end
            if self.frames%300==0 and (not runtime_context(self,self.lease)
                or api.read(self.lease.target.address,272)~=self.lease.modified
                or api.read(self.lease.damage.target.address,76)~=spec.damage_target) then
                self.status='APPLIED_RECORD_CHANGED_RESTART_REQUIRED'
            end
            return
        end
        if self.status=='WAITING_TO_SCAN' then
            if not spec.settings and self.frames<120 then return end
            local lease,reason=find_component_context()
            if not lease then self.status=reason;return end
            if spec.settings then
                self.component_lease=lease;self.status='LOADING_DIRECT_SETTINGS';return
            end
            self.component_lease=lease;self.cursor=65536;self.regions={}
            self.region_index=1;self.region_offset=0;self.previous='';self.status='MAPPING'
        end
        if self.status=='LOADING_DIRECT_SETTINGS' then
            spec.settings:step()
            if spec.settings.status=='COMPLETE' then
                local p,d=spec.settings.hits.projectile[1],spec.settings.hits.damage[1]
                self.status='SCANNING'
                inspect_damage(self,d.header,d.header_bytes)
                if self.status~='SCANNING' then return end
                inspect(self,p.header,p.header_bytes)
                if self.status~='SCANNING' then return end
                apply(self)
            elseif spec.settings.status~='LOADING' then
                self.status='DIRECT_SETTINGS_'..spec.settings.status
            end
            return
        end
        if self.frames%2~=0 then return end
        if self.status=='MAPPING' then
            for _=1,32 do
                local region,reason=api.query(self.cursor)
                if not region then
                    if reason~='end' then self.status='QUERY_FAILED';return end
                    table.sort(self.regions,function(a,b)
                        local ap=a.kind==0x20000 and a.size==131072 and 0 or 1
                        local bp=b.kind==0x20000 and b.size==131072 and 0 or 1
                        if ap~=bp then return ap<bp end
                        return a.size<b.size
                    end)
                    self.status='SCANNING';return
                end
                local next_cursor=region.base+region.size
                if next_cursor<=self.cursor then self.status='INVALID_REGION';return end
                self.cursor=next_cursor
                if region.readable and region.size>=65536 and region.size<=64*1024*1024 then
                    self.regions[#self.regions+1]={base=region.base,size=region.size,kind=region.kind}
                end
            end
            return
        end
        if self.status~='SCANNING' then return end
        for _=1,4 do
            local region=self.regions[self.region_index]
            if not region then apply(self);return end
            local remain=region.size-self.region_offset
            if remain<=0 then
                self.region_index=self.region_index+1;self.region_offset=0;self.previous=''
            else
                local size=math.min(65536,remain)
                local at=region.base+self.region_offset
                local blob=read_blob(self,at,size)
                if blob then
                    local window=self.previous..blob
                    inspect_damage(self,at-#self.previous,window)
                    if self.status~='SCANNING' then return end
                    inspect(self,at-#self.previous,window)
                    if self.status=='AMBIGUOUS_PROJECTILE_TABLES_NO_WRITE' then return end
                    self.previous=window:sub(-39)
                else self.previous='' end
                self.region_offset=self.region_offset+size
            end
        end
    end
    function s:stop()
        local lease=self.lease;if not lease or not lease.damage_written then return end
        if runtime_context(self,lease) and api.read(lease.target.address,272)==lease.modified then
            local ok,detail=api.write(lease.write_address,lease.restore_bytes)
            if ok and api.read(lease.target.address,272)==lease.target.bytes then
                if api.read(lease.damage.target.address,76)==spec.damage_target then
                    local restored=api.write(lease.damage.target.address+4,spec.damage_original:sub(5))
                    if restored and api.read(lease.damage.target.address,76)==spec.damage_original then
                        self.status='RESTORED_ON_SHUTDOWN';self.lease=nil;return
                    end
                end
            end
            self.error='restore_failed_'..tostring(detail)
        else self.error='restore_context_changed_no_write' end
        self.status='RESTORE_NOT_CONFIRMED'
    end
    return s
end
return M

