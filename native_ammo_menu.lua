local M={}
local ffi,bit=require('ffi'),require('bit')
local function pack(v)
 return string.char(v%256,math.floor(v/256)%256,math.floor(v/65536)%256,math.floor(v/16777216)%256)
end
local function u32(b,o)
 if not b then return nil end
 local a,c,d,e=b:byte(o+1,o+4)
 return e and a+c*256+d*65536+e*16777216 or nil
end
function M.new(api,game,owner,ref,id,hit,policy_spec)
 local s={status='INITIALIZING',leases={}}
 local function ptr(a) return api.pointer(api.read(a,8)) end
 local function global(rva) return api.pointer(api.read_module(game+rva,8)) end
 -- The same bounded native hash lookup used by the MLS launcher observer.
 local function lookup(map,key,limit)
  local b=api.read(map,20)
  local base=b and api.pointer(b:sub(1,8));local cap=u32(b,8)
  local empty,mult=u32(b,12),u32(b,16)
  if not base or not cap or cap==0 or cap>limit or bit.band(cap,cap-1)~=0 or key==empty then return end
  local product=tonumber(ffi.cast('uint32_t',ffi.cast('uint64_t',key)*mult))
  for probe=0,math.min(cap,128)-1 do
   local row=api.read(base+8*bit.band(product+probe,cap-1),8)
   local k=u32(row,0)
   if k==key then local i=u32(row,4);return i~=0xffffffff and i or nil end
   if not k or k==empty then return end
  end
 end
 local function install(address,original,modified,valid)
  if not valid() or api.read(address,#original)~=original then return false end
  local ok=api.write(address,modified)
  if api.read(address,#modified)==modified then
   s.leases[#s.leases+1]={address=address,original=original,modified=modified,valid=valid}
  end
  return ok and api.read(address,#modified)==modified
 end
 function s:stop()
  for i=#self.leases,1,-1 do
   local l=self.leases[i]
   if l.valid() and api.read(l.address,#l.modified)==l.modified then api.write(l.address,l.original) end
  end
  self.leases={};self.status='STOPPED'
 end
 local table_slot=owner+0xF11798
 local data=ptr(table_slot)
 local function data_context()
  return ptr(table_slot)==data and api.read_blob(data,#ref.weapon_map)==ref.weapon_map
 end
 local row=data and data+#ref.weapon_map+ref.weapon_index*1232
 if not row or not data_context() or api.read_blob(row,1232)~=ref.weapon_row then
  s.status='WEAPON_DATA_MISMATCH_NO_WRITE';return s
 end
 local projectile_table=ptr(owner+hit.slot_rva)
 local function projectile_context()
  return ptr(owner+hit.slot_rva)==projectile_table
   and api.read_blob(projectile_table,#ref.map)==ref.map
 end
 local alternate=ref.alternate_type or ref.projectile_type or 343
 if not install(hit.row+576,ref.row:sub(577,580),pack(alternate),projectile_context)
  or not install(row+184,ref.weapon_row:sub(185,188),pack(8),data_context) then
  s:stop();s.status='MENU_INSTALL_FAILED';return s
 end
 policy_spec.jar_component=ref.row:sub(1,576)..pack(alternate)..ref.row:sub(581)
 s.status='WAITING_FOR_P35'
 -- The game itself fires the alternate record once the menu is installed, so
 -- this walk only installs new weapon instances and reports the mode. Callers
 -- may set poll_interval to run the ~25-read walk every N updates.
 s.poll_interval=1
 local skipped=0
 function s:step(policy)
  if self.status=='STOPPED' or self.status:find('FAILED') or self.status:find('NO_WRITE') then return end
  if self.poll_interval>1 then
   skipped=skipped+1
   if skipped<self.poll_interval then return end
   skipped=0
  end
  if global(0x3326B90)~=owner then self.status='OWNER_CHANGED_NO_WRITE';return end
  local player,inventory=global(0x3326468),global(0x3326738)
  local unit=player and u32(api.read(player+0x3A8,4),0)
  local ai=unit and lookup(owner+0xF21A88,unit,1048576)
  local avatar=ai and ai<262144 and api.read(owner+0xF31AD8+ai*24,24)
  local avatar_id=u32(avatar,8)
  local ii=inventory and avatar_id and lookup(inventory+40,avatar_id,4096)
  local owners=ii and ptr(inventory+64);local rows=ii and ptr(inventory+80)
  local avatar_row=owners and ptr(owners+ii*8)
  if not rows or not avatar_row or api.read(avatar_row,24)~=avatar then self.status='WAITING_FOR_P35';return end
  local inventory_row=api.read(rows+ii*48,48)
  local weapon_id=u32(inventory_row,4)
  local wi=weapon_id and lookup(owner+0xF19A70,weapon_id,1048576)
  local weapon=wi and wi<262144 and api.read(owner+0xF31AD8+wi*24,24)
  if not weapon or weapon:sub(1,8)~=id or u32(weapon,8)~=weapon_id then self.status='WAITING_FOR_P35';return end
  local manager=global(0x3326CE0)
  local index=manager and lookup(manager+48,weapon_id,32768)
  local values=index and ptr(manager+88);local flags=index and ptr(manager+96)
  if not values or not flags then self.status='WAITING_FOR_WEAPON_DATA';return end
  local address=values+index*1008+0x350
  local function instance_context()
   return global(0x3326CE0)==manager and ptr(manager+88)==values
    and lookup(manager+48,weapon_id,32768)==index
    and api.read(owner+0xF31AD8+wi*24,24)==weapon
  end
  local current=api.read(address,4)
  if current==ref.weapon_row:sub(185,188) and current~=pack(8) then
   if not install(address,current,pack(8),instance_context) then self.status='INSTANCE_INSTALL_FAILED';return end
  elseif current~=pack(8) then self.status='INSTANCE_MENU_CHANGED_NO_WRITE';return end
  local value=u32(api.read(flags+index*12+4,4),0)
  local mode=value and bit.band(bit.rshift(value,2),3)
  if mode~=0 and mode~=1 then self.status='UNKNOWN_AMMO_MODE_NO_WRITE';return end
  policy:set_ems(mode==1);self.status=mode==1 and 'NATIVE_EMS' or 'NATIVE_GAS'
 end
 return s
end
return M
