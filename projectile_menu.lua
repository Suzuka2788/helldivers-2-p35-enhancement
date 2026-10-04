local M={}
local ID='suzuka.p35.ems_darts'
function M.new(policy)
 local s={status='WAITING',frames=0}
 function s:step()
  self.frames=self.frames+1
  if self.status~='WAITING' or self.frames%60~=1 then return end
  local menu=rawget(_G,'ModOptionsMenu')
  if menu==nil then return end
  if type(menu)~='table' or menu.api~=1 or type(menu.register_option)~='function'
   or type(menu.get)~='function' or type(menu.on_change)~='function' then
   self.status='INCOMPATIBLE';return
  end
  local ok,why=menu.register_option(ID,{type='choice',mod='Suzuka‘s P35 enhancement',
   label='Electromagnetic darts',choices={'Off (gas speargun)','On (EMS mortar)'},default=1,
   description='Replace P-35 darts with native EMS mortar rounds. Apply between shots to switch projectile modes.'})
  if not ok then self.status='REGISTER_FAILED';self.error=tostring(why);return end
  local function change(value)
   if value==1 or value==2 then policy:set_ems(value==2) end
  end
  menu.on_change(ID,change);change(menu.get(ID));self.status='REGISTERED'
 end
 return s
end
return M
