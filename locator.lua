-- Find the P-35 row by resource identity and verify its complete live table.
local M={}
local function u32(s,o)
 local a,b,c,d=s:byte(o+1,o+4)
 return d and a+b*256+c*65536+d*16777216 or nil
end
local function inspect(blob,ref,id)
 local hits={};local from=1
 local source_at=ref.map:find(ref.bolt_id,1,true)
 if not source_at or (source_at-1)%16~=0 then return hits end
 local source_index=u32(ref.map,source_at-1+8)
 if not source_index or blob:sub(#ref.map+source_index*616+1,#ref.map+(source_index+1)*616)~=ref.bolt then
  return hits
 end
 while true do
  local at=blob:find(id,from,true)
  if not at or at>16384 then break end
  from=at+1
  local off=at-1
  if off%16==0 and u32(blob,off+12)==0 then
   local index=u32(blob,off+8)
   if index and index<2048 then
    local map_size=#ref.map
    local row=blob:sub(map_size+index*616+1,map_size+(index+1)*616)
    if blob:sub(1,map_size)==ref.map and row==ref.row then
     hits[#hits+1]={map=ref.map,original=row,map_size=map_size,index=index}
    end
   end
  end
 end
 return hits
end
function M.fast(api,owner,ref,id)
 local rva=0xF11A40
 local at=api.pointer(api.read(owner+rva,8))
 if not at then return nil end
 local blob=api.read_blob(at,#ref.map+252*616)
 if not blob then return nil end
 local hits=inspect(blob,ref,id)
 if #hits~=1 then return nil end
 local hit=hits[1]
 hit.slot_rva=rva;hit.row=at+hit.map_size+hit.index*616
 return {status='COMPLETE',slot=0,tables=1,weapon=hits,path='VERIFIED_FAST'}
end
function M.new(api,owner,ref,id)
 local s={status='SCANNING',slot=0,seen={},weapon={},tables=0}
 local function pointer(at)return api.pointer(api.read(at,8))end
 function s:step()
  if self.status~='SCANNING' then return end
  for _=1,4 do
   if self.slot>=1536 then
    self.status=#self.weapon==1 and 'COMPLETE' or 'NO_UNIQUE_COMPONENT_NO_WRITE';return
   end
   local rva=0xF10000+self.slot*8;self.slot=self.slot+1
   local at=pointer(owner+rva)
   if at and not self.seen[at] then
    self.seen[at]=true
    local region=api.query(at)
    if region and region.readable then
     local size=math.min(262144,region.base+region.size-at)
     if size>=#ref.map+616 then
      local blob=api.read_blob(at,size)
      if blob then
       self.tables=self.tables+1
       for _,hit in ipairs(inspect(blob,ref,id)) do
        hit.slot_rva=rva
        hit.row=at+hit.map_size+hit.index*616
        self.weapon[#self.weapon+1]=hit
        if #self.weapon>1 then self.status='AMBIGUOUS_COMPONENTS_NO_WRITE';return end
       end
      end
     end
    end
   end
  end
 end
 return s
end
return M

