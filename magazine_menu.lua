-- P-35 magazine capacity / spare magazines and ModOptionsMenu integration.
-- Row +136..+159: capacity, magazines, magazines_refill, magazines_max,
-- reload_threshold, chambered (WeaponMagazineComponentData, 160-byte rows).
local M={}
local CAPACITY_ID='tongz.p35.magazine_capacity_1_6'
local SPARES_ID='tongz.p35.spare_magazines'
local MOD='Suzuka‘s P35 enhancement'
local function pack(v)
 return string.char(v%256,math.floor(v/256)%256,math.floor(v/65536)%256,math.floor(v/16777216)%256)
end
local function whole(value,low,high)
 return type(value)=='number' and value%1==0 and value>=low and value<=high
end
function M.new(api,owner,ref,fast_slot)
 local s={status='SCANNING',menu_status='WAITING',capacity=1,spares=5,slot=0,seen={},hits={},frames=0,writes=0}
 local original=ref.mag_row:sub(137,160)
 local function context(hit)
  return api.pointer(api.read(hit.slot,8))==hit.table
   and api.read_blob(hit.table,#ref.mag_map)==ref.mag_map
 end
 local function expected(hit)
  return ref.mag_row:sub(1,136)..hit.settings
 end
 -- Spares set start, refill and maximum alike (vanilla P-35 is 2/2/2). A
 -- one-round magazine uses the S-11 speargun's reload threshold of 0; 2-6
 -- rounds keep the vanilla threshold.
 local function desired(self)
  local n=pack(self.spares)
  local threshold=self.capacity==1 and pack(0) or original:sub(17,20)
  return pack(self.capacity)..n..n..n..threshold..original:sub(21,24)
 end
 local function probe(slot)
  local at=api.pointer(api.read(slot,8))
  if not at or s.seen[at] then return end
  s.seen[at]=true
  local offset=#ref.mag_map+ref.mag_index*160
  if api.read_blob(at,#ref.mag_map)==ref.mag_map and api.read(at+offset,160)==ref.mag_row then
   s.hits[#s.hits+1]={slot=slot,table=at,address=at+offset,settings=original}
  end
 end
 if fast_slot then
  probe(owner+fast_slot)
  if #s.hits==1 then s.status='READY';s.path='VERIFIED_FAST' end
 end
 function s:set_capacity(value)
  if not whole(value,1,6) then return false,'invalid_capacity' end
  self.capacity=value
  return true
 end
 function s:set_spares(value)
  if not whole(value,1,6) then return false,'invalid_spares' end
  self.spares=value
  return true
 end
 local function menu(self)
  local m=rawget(_G,'ModOptionsMenu')
  if m==nil then return end
  if type(m)~='table' or m.api~=1 or type(m.register_option)~='function'
   or type(m.get)~='function' or type(m.on_change)~='function' then
   self.menu_status='INCOMPATIBLE';return
  end
  local options={
   {CAPACITY_ID,{type='choice',mod=MOD,label='Magazine capacity',choices={'1','2','3','4','5','6'},default=1,
    description='Rounds per P-35 magazine. Apply, then reload to use the new capacity.'},
    function(i) if whole(i,1,6) then self:set_capacity(i) end end},
   {SPARES_ID,{type='choice',mod=MOD,label='Spare magazines',choices={'1','2','3','4','5','6'},default=5,
    description='Spare P-35 magazines carried, maximum and resupply amount. Full effect on the next weapon spawn or resupply.'},
    function(i) if whole(i,1,6) then self:set_spares(i) end end},
  }
  for _,o in ipairs(options) do
   local ok,why=m.register_option(o[1],o[2])
   if not ok then self.menu_status='REGISTER_FAILED';self.error=tostring(why);return end
  end
  for _,o in ipairs(options) do m.on_change(o[1],o[3]);o[3](m.get(o[1])) end
  self.menu_status='REGISTERED'
 end
 function s:step()
  self.frames=self.frames+1
  if self.menu_status=='WAITING' and self.frames%60==1 then menu(self) end
  if self.status=='SCANNING' then
   for _=1,4 do
    if self.slot>=1536 then
     self.status=#self.hits==1 and 'READY' or 'NO_UNIQUE_MAGAZINE_NO_WRITE';break
    end
    local slot=owner+0xF10000+self.slot*8;self.slot=self.slot+1
    probe(slot)
    if #self.hits>1 then self.status='AMBIGUOUS_MAGAZINES_NO_WRITE';return end
   end
  end
  if self.status~='READY' and self.status~='APPLIED_MAGAZINE_CAPACITY' then return end
  local hit=self.hits[1]
  local want=desired(self)
  if hit.settings==want and self.frames%60~=0 then return end
  if not context(hit) or api.read(hit.address,160)~=expected(hit) then
   self.status='MAGAZINE_CONTEXT_CHANGED_NO_WRITE';return
  end
  if hit.settings==want then return end
  local ok,why=api.write(hit.address+136,want)
  local after=api.read(hit.address+136,24)
  if after==want then hit.settings=want;self.writes=self.writes+1 end
  if not ok or after~=want then
   self.status='MAGAZINE_WRITE_FAILED';self.error=tostring(why);return
  end
  self.status='APPLIED_MAGAZINE_CAPACITY'
 end
 function s:stop()
  local hit=self.hits[1]
  if not hit or hit.settings==original then return end
  if not context(hit) or api.read(hit.address,160)~=expected(hit) then
   self.status='MAGAZINE_RESTORE_CONTEXT_CHANGED';return
  end
  local ok=api.write(hit.address+136,original)
  self.status=ok and api.read(hit.address,160)==ref.mag_row and 'MAGAZINE_RESTORED' or 'MAGAZINE_RESTORE_FAILED'
 end
 return s
end
return M
