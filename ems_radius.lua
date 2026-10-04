-- Scale the shared EMS explosion (ExplosionSettings type 180). The P-35 EMS
-- dart and the EMS mortar sentry both use it, so both change. Only the
-- inner/outer/stagger radii (+16..+27) are written; this is local data, the
-- particle effect keeps its size and other players keep their own values.
local M={}
local ffi=require('ffi')
-- New ID in preview21: the old 30-100% option's saved index means something else.
local ID='tongz.p35.ems_size'
local MOD='Suzuka‘s P35 enhancement'
local TYPE,STRIDE,OFFSET=180,152,16
local PERCENTS={50,100}
local function u32(s,o)
 local a,b,c,d=s:byte(o+1,o+4)
 return d and a+b*256+c*65536+d*16777216 or nil
end
local function floats(a,b,c) return ffi.string(ffi.new('float[3]',a,b,c),12) end
-- Live vanilla radii on game build 2e2c3b7c… (inner, outer, stagger). The
-- explosion also starts status volume template 15 (7 s field); that radius is
-- not part of this record and is left unchanged.
local VANILLA=floats(1,10,12)
function M.new(api,settings,game)
 local s={status='WAITING_FOR_SETTINGS',menu_status='WAITING',percent=PERCENTS[1],writes=0,frames=0}
 local address,applied
 local function context()
  local e=settings.hits.explosion[1]
  return e and api.pointer(api.read_module(game+e.pointer_rva,8))==e.header-4
   and api.read(e.header,40)==e.header_bytes
 end
 local function desired(percent)
  if percent==100 then return VANILLA end
  local f=percent/100
  return floats(1*f,10*f,12*f)
 end
 function s:set_percent(value)
  for _,p in ipairs(PERCENTS) do
   if p==value then self.percent=value;return true end
  end
  return false,'invalid_percent'
 end
 local function menu(self)
  local m=rawget(_G,'ModOptionsMenu')
  if m==nil then return end
  if type(m)~='table' or m.api~=1 or type(m.register_option)~='function'
   or type(m.get)~='function' or type(m.on_change)~='function' then
   self.menu_status='INCOMPATIBLE';return
  end
  local choices={}
  for i,p in ipairs(PERCENTS) do choices[i]=p..'%' end
  local ok,why=m.register_option(ID,{type='choice',mod=MOD,label='EMS field size',choices=choices,default=1,
   description='50%: half EMS explosion range and half lingering field effect. 100%: vanilla. '
    ..'Also applies to the EMS mortar sentry, which uses the same explosion. Only your game is changed.'})
  if not ok then self.menu_status='REGISTER_FAILED';self.error=tostring(why);return end
  local function change(i) if type(i)=='number' and PERCENTS[i] then self:set_percent(PERCENTS[i]) end end
  m.on_change(ID,change);change(m.get(ID));self.menu_status='REGISTERED'
 end
 function s:step()
  self.frames=self.frames+1
  if self.menu_status=='WAITING' and self.frames%60==1 then menu(self) end
  if self.status=='WAITING_FOR_SETTINGS' then
   if settings.status~='COMPLETE' then return end
   local e=settings.hits.explosion[1]
   if not e or e.stride~=STRIDE or not context() then self.status='EXPLOSION_TABLE_CHANGED_NO_WRITE';return end
   local row
   for i=0,e.count-1 do
    if u32(e.data,i*STRIDE)==TYPE then
     if row then self.status='DUPLICATE_EMS_EXPLOSION_NO_WRITE';return end
     row=i
    end
   end
   if not row then self.status='EMS_EXPLOSION_NOT_FOUND_NO_WRITE';return end
   address=e.records+row*STRIDE+OFFSET
   if api.read(address,12)~=VANILLA then self.status='EMS_RADIUS_NOT_VANILLA_NO_WRITE';return end
   applied=VANILLA;self.status='READY'
  end
  if self.status~='READY' and self.status~='APPLIED' then return end
  local want=desired(self.percent)
  if want==applied and self.frames%60~=0 then return end
  if not context() or api.read(address,12)~=applied then self.status='EMS_RADIUS_CHANGED_NO_WRITE';return end
  if want==applied then return end
  local ok,why=api.write(address,want)
  local after=api.read(address,12)
  if after==want then applied=want;self.writes=self.writes+1 end
  if not ok or after~=want then self.status='EMS_RADIUS_WRITE_FAILED';self.error=tostring(why);return end
  self.status='APPLIED'
 end
 function s:stop()
  if not applied or applied==VANILLA then return end
  if not context() or api.read(address,12)~=applied then self.status='EMS_RADIUS_RESTORE_CONTEXT_CHANGED';return end
  local ok=api.write(address,VANILLA)
  self.status=ok and api.read(address,12)==VANILLA and 'RESTORED' or 'EMS_RADIUS_RESTORE_FAILED'
  if self.status=='RESTORED' then applied=VANILLA end
 end
 return s
end
return M
