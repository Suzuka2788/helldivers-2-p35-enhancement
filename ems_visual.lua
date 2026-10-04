-- Keep the lingering EMS field visual (particle 0xBFE8E0D13DAFBE5E, systems
-- 15-19) at the same percentage as the EMS explosion radius. The package ships
-- the particle at 50%; once the loaded copy is found in memory its spatial
-- values are rewritten to original*percent. Only a byte-identical copy of the
-- shipped or currently applied particle is ever written.
local M={}
local ffi=require('ffi')
local WINDOW=262144
local SCAN_BYTES=1048576   -- per update while searching
local QUERIES=64           -- VirtualQuery calls per update while searching
local IDLE_FRAMES=600      -- pause after a full pass without a match
local CHECK_FRAMES=300
local function f32(values)
 return ffi.string(ffi.new('float[?]',#values,values),4*#values)
end
-- spec: {baked=<shipped particle bytes>, fields={{offset,{original floats}},...}}
function M.new(api,spec,radius)
 local s={status='SCANNING',percent=nil,writes=0,passes=0,found=0}
 local needle=spec.baked:sub(1,64)
 local size=#spec.baked
 local cursor,region,offset,idle=65536,nil,0,0
 local address,current
 local function bytes_for(percent)
  local parts,at={},1
  for _,f in ipairs(spec.fields) do
   local o,orig=f[1],f[2]
   local scaled={}
   for i,v in ipairs(orig) do scaled[i]=v*percent/100 end
   parts[#parts+1]=spec.baked:sub(at,o)
   parts[#parts+1]=f32(scaled)
   at=o+4*#orig+1
  end
  parts[#parts+1]=spec.baked:sub(at)
  return table.concat(parts)
 end
 local baked_percent=spec.baked_percent
 local function restart()
  address,current,cursor,region,offset=nil,nil,65536,nil,0
  s.status='SCANNING'
 end
 local function candidate(at)
  local blob=api.read_blob(at,size)
  if blob==spec.baked then return baked_percent end
  if blob and current and blob==current.bytes then return current.percent end
 end
 local function scan()
  local budget,queries=SCAN_BYTES,QUERIES
  while budget>0 do
   if not region then
    if queries==0 then return end
    queries=queries-1
    local r,why=api.query(cursor)
    if not r then
     if why~='end' then s.status='QUERY_FAILED';return end
     s.passes=s.passes+1;cursor=65536;idle=IDLE_FRAMES;return
    end
    cursor=r.base+r.size
    if r.readable and r.size>=size then region=r;offset=0 end
   else
    local at=region.base+offset
    local n=math.min(WINDOW,region.base+region.size-at)
    local blob=n>=64 and api.read_blob(at,n)
    if blob then
     local from=1
     while true do
      local i=blob:find(needle,from,true)
      if not i then break end
      local percent=candidate(at+i-1)
      if percent then
       address=at+i-1;current={percent=percent,bytes=percent==baked_percent and spec.baked or current.bytes}
       s.found=s.found+1;s.status='FOUND';return
      end
      from=i+1
     end
    end
    budget=budget-n
    if at+n>=region.base+region.size then region=nil
    else offset=offset+n-63 end
   end
  end
 end
 local function apply(percent)
  local live=api.read_blob(address,size)
  if live~=current.bytes then restart();return end
  local target=bytes_for(percent)
  for _,f in ipairs(spec.fields) do
   local o,n=f[1],4*#f[2]
   local want=target:sub(o+1,o+n)
   if live:sub(o+1,o+n)~=want then
    local ok,why=api.write(address+o,want)
    if not ok then s.status='WRITE_FAILED';s.error=tostring(why);return end
   end
  end
  if api.read_blob(address,size)~=target then s.status='READBACK_MISMATCH';return end
  current={percent=percent,bytes=target};s.percent=percent;s.writes=s.writes+1;s.status='SYNCED'
 end
 local frames=0
 function s:step()
  frames=frames+1
  if self.status=='SCANNING' then
   if idle>0 then idle=idle-1;return end
   scan()
  end
  if self.status=='FOUND' then apply(radius.percent);return end
  if self.status=='SYNCED' then
   if radius.percent~=current.percent then apply(radius.percent)
   elseif frames%CHECK_FRAMES==0 and api.read_blob(address,size)~=current.bytes then restart() end
  end
 end
 function s:stop()
  if address and current and current.percent~=baked_percent and api.read_blob(address,size)==current.bytes then
   apply(baked_percent)
   if self.status=='SYNCED' then self.status='RESTORED' end
  end
 end
 return s
end
return M
