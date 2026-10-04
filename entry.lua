if rawget(_G,'TongzP35GasSpeargun') then return end
local state={version='1.2.0',status='INITIALIZING',frames=0}
rawset(_G,'TongzP35GasSpeargun',state)
local loader=rawget(_G,'CowboyBingusModLoader')
local function report()
 pcall(function()
  local f=loader and loader.open_log and loader.open_log('TongzP35GasSpeargun.log')
  if not f then return end
  f:write('Suzuka‘s P35 enhancement '..state.version..'\nSTATUS='..state.status..'\n')
  if state.game_sha256 then f:write('GAME_SHA256='..state.game_sha256..'\n') end
  f:write('STARTUP_PATH='..tostring(state.startup_path)..' READY_FRAME='..tostring(state.ready_frame)..'\n')
  if state.resolver then f:write('RESOLVER='..state.resolver.status..' candidates='..#state.resolver.candidates..'\n') end
  if state.locator then
   local d=state.locator
   f:write('LOCATOR='..d.status..' slots='..d.slot..' tables='..d.tables..' weapon='..#d.weapon..'\n')
  end
  if state.policy then
   if state.fixed_p35 then f:write('FIXED_P35='..state.fixed_p35.status..'\n') end
   f:write('EMS_ENABLED='..tostring(state.p35_mode_ems)..'\n')
   if state.projectile_menu then f:write('PROJECTILE_MENU='..state.projectile_menu.status..'\n') end
   f:write('POLICY='..state.policy.status..' writes='..state.policy.writes
    ..' reads='..state.policy.reads..' failures='..state.policy.failures
    ..' cache_hits='..state.policy.cache_hits..' aliases='..state.policy.aliases..' candidates='..#state.policy.candidates..'\n')
   if state.policy.error then f:write('POLICY_ERROR='..state.policy.error..'\n') end
   if state.policy.regions then
    f:write('PROGRESS=region '..state.policy.region_index..'/'..#state.policy.regions
     ..' offset='..state.policy.region_offset..' frames='..state.policy.frames..'\n')
   end
  end
  if state.magazine then
   local m=state.magazine
   f:write('MAGAZINE='..m.status..' capacity='..m.capacity..' spares='..m.spares..' writes='..m.writes..' MENU='..m.menu_status..'\n')
   if m.error then f:write('MAGAZINE_ERROR='..m.error..'\n') end
  end
  if state.ems_radius then
   local e=state.ems_radius
   f:write('EMS_RADIUS='..e.status..' percent='..e.percent..' writes='..e.writes..' MENU='..e.menu_status..'\n')
   if e.error then f:write('EMS_RADIUS_ERROR='..e.error..'\n') end
  end
  if state.ems_visual then
   local v=state.ems_visual
   f:write('EMS_VISUAL='..v.status..' percent='..tostring(v.percent)..' writes='..v.writes..' found='..v.found..' passes='..v.passes..'\n')
   if v.error then f:write('EMS_VISUAL_ERROR='..v.error..'\n') end
  end
  if state.perf then
   local p=state.perf
   f:write(string.format('PERF updates=%d work_ms=%.1f avg_us=%.2f max_ms=%.3f max_status=%s\n',
    p.updates,p.work_ms,p.updates>0 and p.work_ms*1000/p.updates or 0,p.max_ms,p.max_status))
   f:write('PERF_HIST_MS <=0.05='..p.hist[1]..' <=0.25='..p.hist[2]..' <=1='..p.hist[3]
    ..' <=4='..p.hist[4]..' >4='..p.hist[5]..'\n')
   local c=state.cost
   if c then
    f:write(string.format('PERF_NATIVE vq_calls=%d vq_ms=%.2f rpm_calls=%d rpm_ms=%.2f\n',
     c.vq,c.vq_ticks*state.ms_per_tick,c.rpm,c.rpm_ticks*state.ms_per_tick))
   end
  end
  if state.error then f:write('ERROR='..state.error..'\n') end
  f:close()
 end)
end
local ok,err=pcall(function()
 assert(loader and loader.api==1,'Bingus Shared Loader API 1 required')
 local api=create_api()
 local ticks=api.ticks
 if ticks then
  state.cost=api.cost;state.ms_per_tick=api.ms_per_tick
  state.perf={updates=0,work_ms=0,max_ms=0,max_status='NONE',hist={0,0,0,0,0}}
 end
 local game=assert(api.module('game.dll'),'game.dll unavailable')
 state.game_sha256=api.module_hash(game)
 local resolver=layout_resolver.new(api,game)
 state.resolver=resolver;state.status='LOCATING_ENTITY_OWNER';state.startup_path='SCAN_FALLBACK'
 if state.game_sha256=='2e2c3b7c2500646dadd5f2b4c6e0504dbb7e7896139f64cddc0d1813c718f51e' then
  state.status='FAST_LOCATING';state.startup_path='VERIFIED_FAST'
 end
 local previous=assert(rawget(_G,'update'),'update unavailable')
 local old_shutdown=rawget(_G,'shutdown')
 local function next_owner()
  state.owner_checked=state.owner_checked+1
  local candidate=state.owner_candidates[state.owner_checked]
  if candidate then
   state.locator=bolt_locator.new(api,candidate.address,ref,jar_id)
   state.status='LOCATING_COMPONENT'
  elseif #state.owner_matches==1 then
   local found=state.owner_matches[1]
   state.owner_rva=found.candidate.rva;state.locator=found.locator
   state.status='COMPONENT_VERIFIED'
  else
   state.status=#state.owner_matches==0 and 'NO_VERIFIED_OWNER_NO_WRITE' or 'AMBIGUOUS_OWNERS_NO_WRITE'
  end
 end
 local function start_policy()
  state.settings=settings_locator.new(api,game,state.game_sha256)
  state.settings:start()
  local hit=state.locator.weapon[1]
  local spec={game=game,owner_rva=state.owner_rva,scan_begin=hit.slot_rva,
   scan_end=hit.slot_rva+8,component_probe_offset=0,
   component_map=hit.map,jar_component=ref.row,bolt_component=ref.bolt,
   jar_projectile=ref.jar_projectile,bolt_projectile=ref.bolt_projectile,damage_original=ref.damage_original,
   damage_source=ref.damage_source,damage_target=ref.damage_target,ems_projectile=ref.ems_projectile,
   gas_icon=ref.gas_icon,ems_icon=ref.ems_icon,settings=state.settings}
  local owner=api.pointer(api.read(game+state.owner_rva,8))
  if owner then state.magazine=magazine_menu.new(api,owner,ref,state.startup_path=='VERIFIED_FAST' and 0xF11060 or nil) end
  state.policy=projectile_sync.new(api,spec)
  assert(state.game_sha256=='2e2c3b7c2500646dadd5f2b4c6e0504dbb7e7896139f64cddc0d1813c718f51e','UNSUPPORTED_NATIVE_MENU_GAME_BUILD')
  state.projectile_menu=native_ammo_menu.new(api,game,owner,ref,jar_id,hit,spec)
  assert(state.projectile_menu.status=='WAITING_FOR_P35',state.projectile_menu.status)
  state.projectile_menu.poll_interval=10
  state.fixed_p35=fixed_projectile.new(api,state.settings,game,ref.alternate_original,{})
  state.ems_radius=ems_radius.new(api,state.settings,game)
  state.ems_visual=ems_visual.new(api,ems_visual_spec,state.ems_radius)
  state.policy:start();state.status='APPLYING'
 end
 local function work()
  if state.status=='FAST_LOCATING' then
   if state.frames==1 or state.frames%15==0 then
    local owner=api.pointer(api.read_module(game+0x3326B90,8))
    local found=owner and bolt_locator.fast(api,owner,ref,jar_id)
    if found then
     state.owner_rva=0x3326B90;state.locator=found;state.status='COMPONENT_VERIFIED'
    elseif state.frames>=300 then
     state.status='LOCATING_ENTITY_OWNER';state.startup_path='SCAN_FALLBACK'
    end
   end
  elseif state.status=='LOCATING_ENTITY_OWNER' then
   resolver:step()
   if resolver.status:find('^COMPLETE') then
    local owners={}
    for _,c in ipairs(resolver.candidates) do if c.kind=='ENTITY_OWNER' then owners[#owners+1]=c end end
    if #owners==0 then state.status='NO_ENTITY_OWNER_NO_WRITE'
    else state.owner_candidates=owners;state.owner_checked=0;state.owner_matches={};next_owner() end
   elseif resolver.status=='ERROR' then state.status='ENTITY_OWNER_ERROR_NO_WRITE' end
  elseif state.status=='LOCATING_COMPONENT' then
   state.locator:step()
   if state.locator.status~='SCANNING' then
    if state.locator.status=='COMPLETE' then
     local candidate=state.owner_candidates[state.owner_checked]
     state.owner_matches[#state.owner_matches+1]={candidate=candidate,locator=state.locator}
    end
    next_owner()
   end
  elseif state.status=='COMPONENT_VERIFIED' then start_policy()
  else
   state.projectile_menu:step(state.policy)
   state.p35_mode_ems=state.policy.ems_enabled
   state.policy:set_ems(false);state.policy:step()
   if state.policy.lease then state.fixed_p35:step(state.policy.lease.electromagnetic) end
  end
  if state.magazine then state.magazine:step() end
  if state.ems_radius then state.ems_radius:step() end
  if state.ems_visual then state.ems_visual:step() end
  if not state.ready_frame and state.fixed_p35 and state.fixed_p35.status=='READY'
   and state.magazine.status=='APPLIED_MAGAZINE_CAPACITY' then
   state.ready_frame=state.frames
  end
 end
 local active={FAST_LOCATING=true,LOCATING_ENTITY_OWNER=true,LOCATING_COMPONENT=true,
  COMPONENT_VERIFIED=true,APPLYING=true}
 -- Field-wise change detection keeps string building out of every update.
 local last,dirty={},false
 local function track(i,v) if last[i]~=v then last[i]=v;dirty=true end end
 local function changed()
  dirty=false
  local m,l,p,f=state.magazine,state.locator,state.policy,state.fixed_p35
  track(1,state.status);track(2,resolver.status)
  track(3,m and m.status);track(4,m and m.menu_status);track(5,m and m.capacity)
  track(6,l and l.status);track(7,p and p.status);track(8,state.p35_mode_ems)
  track(9,f and f.status);track(10,state.ready_frame)
  local e=state.ems_radius
  track(13,e and e.status);track(14,e and e.percent);track(15,e and e.menu_status)
  track(18,m and m.spares)
  local v=state.ems_visual
  track(16,v and v.status);track(17,v and v.percent)
  return dirty
 end
 local function finish(...)
  state.frames=state.frames+1
  if active[state.status] then
   local began=ticks and ticks()
   local good,problem=pcall(work)
   if not good then state.status='DISABLED_RUNTIME_ERROR';state.error=tostring(problem) end
   if began then
    local p=state.perf
    local ms=(ticks()-began)*state.ms_per_tick
    p.updates=p.updates+1;p.work_ms=p.work_ms+ms
    if ms>p.max_ms then p.max_ms=ms;p.max_status=state.status end
    local h=p.hist
    if ms<=0.05 then h[1]=h[1]+1 elseif ms<=0.25 then h[2]=h[2]+1 elseif ms<=1 then h[3]=h[3]+1
    elseif ms<=4 then h[4]=h[4]+1 else h[5]=h[5]+1 end
   end
  end
  -- Write the log on a status change, plus a heartbeat every 36000 updates.
  if changed() or state.frames%36000==0 then report() end
  return ...
 end
 _G.update=function(...)
  return finish(previous(...))
 end
 _G.shutdown=function(...)
  if state.fixed_p35 then pcall(function()state.fixed_p35:stop()end) end
  if state.magazine then pcall(function()state.magazine:stop()end) end
  if state.ems_radius then pcall(function()state.ems_radius:stop()end) end
  if state.ems_visual then pcall(function()state.ems_visual:stop()end) end
  if state.policy then pcall(function()state.policy:stop()end) end
  if state.projectile_menu then pcall(function()state.projectile_menu:stop()end) end
  report();if old_shutdown then return old_shutdown(...) end
 end
end)
if not ok then state.status='DISABLED_NO_WRITE';state.error=tostring(err) end
report()
