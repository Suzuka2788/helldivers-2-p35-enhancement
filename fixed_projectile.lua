local M={}
local function u32(b,o)
 if not b then return end
 local a,c,d,e=b:byte(o+1,o+4)
 return e and a+c*256+d*65536+e*16777216 or nil
end
function M.new(api,settings,game,original,target)
 local s={status='WAITING'}
 local address,header
 local function context()
  local p=settings.hits.projectile[1]
  return p and api.pointer(api.read_module(game+p.pointer_rva,8))==p.header-4
   and api.read(p.header,40)==header
 end
 function s:step(bytes)
  if self.status~='WAITING' or not bytes or settings.status~='COMPLETE' then return end
  local p=settings.hits.projectile[1]
  header=api.read(p.header,40)
  local records=header and api.pointer(header:sub(25,32));local count=u32(header,32)
  local blob=records and count==350 and api.read_blob(records,count*272)
  if not blob then self.status='TABLE_MISMATCH_NO_WRITE';return end
  local wanted=u32(original,0)
  for i=0,count-1 do
   if u32(blob,i*272)==wanted then
    if address or blob:sub(i*272+1,(i+1)*272)~=original then self.status='RESERVED_RECORD_CHANGED_NO_WRITE';return end
    address=records+i*272
   end
  end
  if not address or not context() then self.status='RECORD_NOT_FOUND_NO_WRITE';return end
  local desired=original:sub(1,4)..bytes:sub(5)
  local ok=api.write(address+4,desired:sub(5))
  if api.read(address,272)==desired then target.bytes=desired;self.status='READY' end
  if not ok or self.status~='READY' then self.status='WRITE_FAILED' end
 end
 function s:stop()
  if address and target.bytes and context() and api.read(address,272)==target.bytes then
   api.write(address+4,original:sub(5))
  end
  self.status='STOPPED'
 end
 return s
end
return M
