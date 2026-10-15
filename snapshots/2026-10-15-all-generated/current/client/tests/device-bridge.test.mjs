import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';

const source=await readFile(new URL('../dist/device-bridge.js',import.meta.url),'utf8');
const context=vm.createContext({AbortController,ArrayBuffer,Uint8Array,DataView,setTimeout,clearTimeout,Date});
vm.runInContext(source,context,{filename:'device-bridge.js'});
const API=context.SVDeviceBridge;
const toPlain=value=>JSON.parse(JSON.stringify(value));
const env=extra=>({isSecureContext:true,AbortController,ArrayBuffer,Uint8Array,DataView,setTimeout,clearTimeout,performance:{now:()=>123.5},navigator:{},...extra});
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function until(predicate,timeout=1500){const end=Date.now()+timeout;while(!predicate()){if(Date.now()>end)throw Error('Timed out waiting for transport state');await wait(5);}}
function deferred(){let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});return {promise,resolve,reject};}
function events(target={}){
  const handlers=new Map();
  target.addEventListener=(name,fn)=>{if(!handlers.has(name))handlers.set(name,new Set());handlers.get(name).add(fn);};
  target.removeEventListener=(name,fn)=>handlers.get(name)?.delete(fn);
  target.emit=(name,payload={})=>{for(const fn of [...(handlers.get(name)||[])])fn({target,...payload});};
  target.count=name=>handlers.get(name)?.size||0;
  return target;
}
function bleFixture(overrides={}){
  const calls=[],characteristic=events({properties:{read:true,notify:true},value:new DataView(new Uint8Array([0x80,0x80,0x90,60,90]).buffer),
    async readValue(){calls.push('read');return this.value;},async startNotifications(){calls.push('notify');return this;},async stopNotifications(){calls.push('stop-notify');return this;}});
  const service={async getCharacteristic(id){assert.equal(id,API.BLE_MIDI_CHARACTERISTIC);calls.push('characteristic');return characteristic;}};
  const server={async getPrimaryService(id){assert.equal(id,API.BLE_MIDI_SERVICE);calls.push('service');return service;}};
  const device=events({id:'violin-1',name:'Test violin',gatt:{connected:false,async connect(){calls.push('connect');this.connected=true;return server;},disconnect(){calls.push('disconnect');if(this.connected){this.connected=false;device.emit('gattserverdisconnected');}}}});
  const navigator={bluetooth:{async requestDevice(query){calls.push('chooser');assert.deepEqual(toPlain(query),{filters:[{services:[API.BLE_MIDI_SERVICE]}]});return device;}}};
  Object.assign(characteristic,overrides.characteristic);Object.assign(device.gatt,overrides.gatt);
  return {calls,characteristic,service,server,device,navigator};
}
function nativeFixture(overrides={}){
  const calls=[],connection={connected:true,deviceId:'real-instrument'},listeners=new Set();
  const provider={kind:'native',verification:'verified',id:'explicit-adapter',
    getConnectionState(){return {...connection};},
    async handshake(request){calls.push({kind:'handshake',request});return {requestId:request.requestId,deviceId:connection.deviceId,connected:true,protocolVersion:'test-1',presetSchemaVersion:1,
      capabilities:{parameterControl:true,presetStore:true},parameterRanges:{volume:{min:0,max:1},reverb:{min:0,max:1}}};},
    async storePreset(request){calls.push({kind:'store',request});return {requestId:request.requestId,deviceId:request.deviceId,ok:true,persisted:true};},
    subscribeConnection(fn){listeners.add(fn);return()=>listeners.delete(fn);},
    disconnect(){connection.connected=false;calls.push({kind:'disconnect'});},...overrides};
  return {calls,connection,provider,drop(){connection.connected=false;for(const fn of listeners)fn({...connection});},listeners};
}
const preset=()=>({schemaVersion:1,name:'My violin',group:'Practice',parameters:{volume:.7,reverb:.2}});

test('capabilities inspect actual APIs and security; codec failures cannot escape',()=>{
  function MediaRecorder(){}MediaRecorder.isTypeSupported=type=>{if(type.includes('ogg'))throw Error('unsupported');return type==='audio/mp4'||type==='video/mp4';};
  const capabilities=API.detectCapabilities(env({AudioContext:function(){},MediaRecorder,navigator:{bluetooth:{requestDevice(){}},requestMIDIAccess(){},mediaDevices:{getUserMedia(){}}}}));
  assert.equal(capabilities.webBluetooth,true);assert.equal(capabilities.webMIDI,true);assert.equal(capabilities.mediaInput,true);
  assert.deepEqual(toPlain(capabilities.audioRecordingTypes),['audio/mp4']);assert.deepEqual(toPlain(capabilities.videoRecordingTypes),['video/mp4']);
  const insecure=API.detectCapabilities(env({isSecureContext:false,navigator:{bluetooth:{requestDevice(){}},requestMIDIAccess(){},mediaDevices:{getUserMedia(){}}}}));
  assert.equal(insecure.webBluetooth,false);assert.equal(insecure.webMIDI,false);assert.equal(insecure.mediaInput,false);
  assert.equal(capabilities.endToEndLatencyMeasured,false);assert.equal(capabilities.endToEndLatencyMs,null);
});

test('actual BLE service/read/notify gates connected status and packet copies',async()=>{
  const f=bleFixture(),packets=[],states=[];
  const bridge=API.createDeviceBridge({environment:env({navigator:f.navigator}),onMidiPacket:packet=>packets.push(packet),onState:s=>states.push(s)});
  await bridge.connectBleMidi();assert.equal(bridge.status().ble.connected,true);
  assert.deepEqual(f.calls.slice(0,5),['chooser','connect','service','characteristic','read']);assert.equal(f.calls[5],'notify');
  assert.equal(states.find(s=>s.ble.status==='connecting').ble.connected,false);
  const backing=new Uint8Array([1,2,0x80,0x81,0x90,65,99,9]);f.characteristic.value=new DataView(backing.buffer,2,5);f.characteristic.emit('characteristicvaluechanged');
  assert.equal(packets.length,1);assert.deepEqual([...packets[0].bytes],[0x80,0x81,0x90,65,99]);backing[2]=4;assert.equal(packets[0].bytes[0],0x80);
  assert.equal(packets[0].transport,'ble-midi');assert.equal(packets[0].receivedAt,123.5);assert.equal(bridge.status().endToEndLatencyMs,null);
  bridge.dispose();assert.equal(f.characteristic.count('characteristicvaluechanged'),0);assert.equal(f.device.count('gattserverdisconnected'),0);
});

test('unsupported browser does not open a chooser or fabricate connectivity',async()=>{
  const f=bleFixture(),bridge=API.createDeviceBridge({environment:env({isSecureContext:false,navigator:f.navigator})});
  await assert.rejects(bridge.connectBleMidi(),error=>error.code==='UNSUPPORTED');assert.equal(f.calls.length,0);assert.equal(bridge.status().ble.connected,false);bridge.dispose();
});

test('a resolved connect promise with gatt.connected false is rejected',async()=>{
  const f=bleFixture();f.device.gatt.connect=async()=>f.server;
  const bridge=API.createDeviceBridge({environment:env({navigator:f.navigator})});await assert.rejects(bridge.connectBleMidi(),error=>error.code==='NOT_CONNECTED');
  assert.equal(bridge.status().ble.connected,false);bridge.dispose();
});

test('missing MIDI service and disabled notifications fail without guessed services',async()=>{
  const f=bleFixture();f.server.getPrimaryService=async id=>{assert.equal(id,API.BLE_MIDI_SERVICE);throw Object.assign(Error('missing'),{name:'NotFoundError'});};
  const bridge=API.createDeviceBridge({environment:env({navigator:f.navigator})});await assert.rejects(bridge.connectBleMidi());assert.equal(bridge.status().ble.connected,false);bridge.dispose();
  const g=bleFixture({characteristic:{properties:{read:true,notify:false}}}),other=API.createDeviceBridge({environment:env({navigator:g.navigator})});
  await assert.rejects(other.connectBleMidi(),error=>error.code==='UNSUPPORTED');assert.equal(g.calls.includes('notify'),false);other.dispose();
});

test('notification subscription must finish before connected is reported',async()=>{
  const f=bleFixture(),pending=deferred();f.characteristic.startNotifications=()=>pending.promise;
  const bridge=API.createDeviceBridge({environment:env({navigator:f.navigator})}),promise=bridge.connectBleMidi();await wait(5);
  assert.equal(bridge.status().ble.connected,false);assert.equal(bridge.status().ble.status,'connecting');pending.resolve(f.characteristic);await promise;assert.equal(bridge.status().ble.connected,true);bridge.dispose();
});

test('chooser cancellation and a late chooser result cannot connect',async()=>{
  const f=bleFixture(),pending=deferred();f.navigator.bluetooth.requestDevice=()=>pending.promise;
  const bridge=API.createDeviceBridge({environment:env({navigator:f.navigator})}),promise=bridge.connectBleMidi();bridge.cancel();
  await assert.rejects(promise,error=>error.code==='ABORTED');pending.resolve(f.device);await wait(5);assert.equal(f.calls.includes('connect'),false);assert.equal(bridge.status().ble.connected,false);bridge.dispose();
});

test('cancelled pending GATT connection is disconnected if it resolves late',async()=>{
  const f=bleFixture(),pending=deferred();f.device.gatt.connect=()=>pending.promise;
  const bridge=API.createDeviceBridge({environment:env({navigator:f.navigator})}),promise=bridge.connectBleMidi();await wait(5);bridge.cancel();
  await assert.rejects(promise,error=>error.code==='ABORTED');f.device.gatt.connected=true;pending.resolve(f.server);await wait(5);assert.equal(f.device.gatt.connected,false);assert.equal(bridge.status().ble.connected,false);bridge.dispose();
});

test('unexpected drop retries an already selected device at most three times',async()=>{
  const f=bleFixture(),bridge=API.createDeviceBridge({environment:env({navigator:f.navigator}),reconnectDelayMs:[0,0,0]});await bridge.connectBleMidi();
  let attempts=0;f.device.gatt.connect=async()=>{attempts++;throw Error('radio absent');};f.device.gatt.disconnect();
  await until(()=>bridge.status().ble.status==='disconnected'&&bridge.status().ble.attempt===3);assert.equal(attempts,3);assert.equal(bridge.status().ble.attempt,3);assert.equal(f.calls.filter(v=>v==='chooser').length,1);
  await wait(20);assert.equal(attempts,3);bridge.dispose();
});

test('cancel clears scheduled reconnect without a new chooser',async()=>{
  const f=bleFixture(),bridge=API.createDeviceBridge({environment:env({navigator:f.navigator}),reconnectDelayMs:[100,100,100]});await bridge.connectBleMidi();f.device.gatt.disconnect();bridge.cancel();
  await wait(130);assert.equal(f.calls.filter(v=>v==='connect').length,1);assert.equal(bridge.status().ble.connected,false);bridge.dispose();
});

test('no explicit control provider means no guessed hardware parameter command',async()=>{
  const bridge=API.createDeviceBridge({environment:env()});await assert.rejects(bridge.connectNative(),error=>error.code==='UNSUPPORTED');await assert.rejects(bridge.storePreset(preset()),error=>error.code==='UNSUPPORTED');assert.equal(bridge.status().lastWrite,null);bridge.dispose();
});

test('demo declarations never become a real connection or persisted preset',async()=>{
  const f=nativeFixture({verification:'demo'}),bridge=API.createDeviceBridge({environment:env(),provider:f.provider});await bridge.connectNative();
  assert.equal(bridge.status().native.status,'demo');assert.equal(bridge.status().native.connected,false);assert.equal(bridge.status().native.providerDeclaration,'demo');
  await assert.rejects(bridge.storePreset(preset()),error=>error.code==='UNVERIFIED_PROVIDER');assert.equal(f.calls.some(c=>c.kind==='store'),false);bridge.dispose();
});

test('native handshake request ID and actual connection state are both required',async()=>{
  const f=nativeFixture({async handshake(){return {requestId:'wrong',connected:true,deviceId:'real-instrument',protocolVersion:'1',capabilities:{}};}}),bridge=API.createDeviceBridge({environment:env(),provider:f.provider});
  await assert.rejects(bridge.connectNative(),error=>error.code==='INVALID_RESPONSE');assert.equal(bridge.status().native.connected,false);bridge.dispose();
  const g=nativeFixture();g.connection.connected=false;const other=API.createDeviceBridge({environment:env(),provider:g.provider});await assert.rejects(other.connectNative(),error=>error.code==='INVALID_RESPONSE');other.dispose();
});

test('actual provider acknowledgement gates preset persistence',async()=>{
  const f=nativeFixture(),bridge=API.createDeviceBridge({environment:env(),provider:f.provider});await bridge.connectNative();const result=await bridge.storePreset(preset());
  assert.equal(result.persisted,true);assert.equal(result.status,'confirmed');assert.equal(result.deviceId,'real-instrument');assert.equal(f.calls.find(c=>c.kind==='store').request.preset.name,'My violin');
  assert.equal(bridge.status().endToEndLatencyMeasured,false);bridge.dispose();
});

test('unsupported capabilities and invalid parameter ranges cannot write',async()=>{
  const f=nativeFixture(),bridge=API.createDeviceBridge({environment:env(),provider:f.provider});await bridge.connectNative();
  await assert.rejects(bridge.storePreset({...preset(),parameters:{volume:1.01}}),error=>error.code==='INVALID_VALUE');
  await assert.rejects(bridge.storePreset({...preset(),parameters:{sensitivity:1}}),error=>error.code==='INVALID_VALUE');
  await assert.rejects(bridge.storePreset({...preset(),schemaVersion:2}),error=>error.code==='INVALID_VALUE');assert.equal(f.calls.filter(c=>c.kind==='store').length,0);bridge.dispose();
  const g=nativeFixture(),original=g.provider.handshake;g.provider.handshake=async request=>({...await original(request),capabilities:{parameterControl:true,presetStore:false}});
  const other=API.createDeviceBridge({environment:env(),provider:g.provider});await other.connectNative();await assert.rejects(other.storePreset(preset()),error=>error.code==='UNSUPPORTED');assert.equal(g.calls.some(c=>c.kind==='store'),false);other.dispose();
});

for(const invalid of ['requestId','persisted','deviceId','demo'])test('invalid '+invalid+' ACK does not confirm writing',async()=>{
  const f=nativeFixture({async storePreset(request){return {requestId:request.requestId,deviceId:request.deviceId,ok:true,persisted:true,[invalid]:invalid==='persisted'?false:invalid==='demo'?true:'mismatch'};}});
  const bridge=API.createDeviceBridge({environment:env(),provider:f.provider});await bridge.connectNative();await assert.rejects(bridge.storePreset(preset()),error=>error.code==='INVALID_ACK');
  assert.equal(bridge.status().lastWrite.persisted,false);assert.equal(bridge.status().lastWrite.status,'failed');bridge.dispose();
});

test('write timeout never interprets late ACK as persisted success',async()=>{
  let writeSignal;const pending=deferred(),f=nativeFixture({storePreset:request=>{writeSignal=request.signal;return pending.promise;}}),bridge=API.createDeviceBridge({environment:env(),provider:f.provider,timeoutMs:100});await bridge.connectNative();
  const promise=bridge.storePreset(preset());const id=bridge.status().lastWrite.requestId;await assert.rejects(promise,error=>error.code==='TIMEOUT');
  assert.equal(writeSignal.aborted,true);pending.resolve({requestId:id,deviceId:'real-instrument',ok:true,persisted:true});await wait(5);assert.equal(bridge.status().lastWrite.persisted,false);assert.equal(bridge.status().lastWrite.status,'failed');bridge.dispose();
});

test('only one parameter store request can be outstanding',async()=>{
  const pending=deferred(),f=nativeFixture({storePreset:()=>pending.promise}),bridge=API.createDeviceBridge({environment:env(),provider:f.provider});await bridge.connectNative();
  const first=bridge.storePreset(preset());await assert.rejects(bridge.storePreset(preset()),error=>error.code==='BUSY');
  pending.resolve({requestId:bridge.status().lastWrite.requestId,deviceId:'real-instrument',ok:true,persisted:true});await first;bridge.dispose();
});

test('disconnect cancels a pending hardware write and stale ACK stays cancelled',async()=>{
  const pending=deferred(),f=nativeFixture({storePreset:()=>pending.promise}),bridge=API.createDeviceBridge({environment:env(),provider:f.provider});await bridge.connectNative();
  const promise=bridge.storePreset(preset()),id=bridge.status().lastWrite.requestId;bridge.disconnect();await assert.rejects(promise,error=>error.code==='ABORTED');
  pending.resolve({requestId:id,deviceId:'real-instrument',ok:true,persisted:true});await wait(5);assert.equal(bridge.status().native.connected,false);assert.equal(bridge.status().lastWrite.status,'cancelled');assert.equal(bridge.status().lastWrite.persisted,false);assert.equal(f.listeners.size,0);bridge.dispose();
});

test('real adapter disconnection clears capabilities and aborts pending write',async()=>{
  const pending=deferred(),f=nativeFixture({storePreset:()=>pending.promise}),bridge=API.createDeviceBridge({environment:env(),provider:f.provider});await bridge.connectNative();
  const promise=bridge.storePreset(preset());f.drop();await assert.rejects(promise,error=>error.code==='ABORTED');assert.equal(bridge.status().native.connected,false);assert.equal(bridge.status().native.capabilities,null);assert.equal(bridge.status().lastWrite.persisted,false);pending.resolve(null);bridge.dispose();
});

test('Web MIDI requests sysex:false, subscribes actual input and detaches on removal',async()=>{
  const input=events({id:'port-1',name:'USB violin',type:'input',state:'connected',async open(){},async close(){this.closed=true;}}),output={id:'port-2',name:'Output',type:'output',state:'connected'};
  const access=events({inputs:new Map([[input.id,input]]),outputs:new Map([[output.id,output]])});
  const bridge=API.createDeviceBridge({environment:env({navigator:{async requestMIDIAccess(query){assert.deepEqual(toPlain(query),{sysex:false});return access;}}})});
  const rows=await bridge.listMIDIPorts();assert.equal(rows.length,2);const received=[];await bridge.subscribeMidiInput(input.id,p=>received.push(p));
  const bytes=new Uint8Array([0x90,60,100]);input.emit('midimessage',{data:bytes,receivedTime:77});assert.deepEqual([...received[0].bytes],[0x90,60,100]);bytes[1]=99;assert.equal(received[0].bytes[1],60);assert.equal(received[0].timestamp,77);
  input.state='disconnected';access.emit('statechange');input.emit('midimessage',{data:bytes});assert.equal(received.length,1);assert.equal(input.count('midimessage'),0);assert.equal(input.closed,true);
  bridge.dispose();assert.equal(access.count('statechange'),0);
});

test('disposal cancels resources, rejects later mutations and preserves honest latency',async()=>{
  const bridge=API.createDeviceBridge({environment:env()});bridge.dispose();bridge.dispose();await assert.rejects(bridge.connectBleMidi(),error=>error.code==='DISPOSED');
  assert.equal(bridge.status().ble.connected,false);assert.equal(bridge.status().endToEndLatencyMs,null);
});

test('status checks actual transport and provider state even before a disconnect event',async()=>{
  const f=bleFixture(),bridge=API.createDeviceBridge({environment:env({navigator:f.navigator})});await bridge.connectBleMidi();f.device.gatt.connected=false;
  assert.equal(bridge.status().ble.connected,false);assert.equal(bridge.status().ble.status,'disconnected');bridge.dispose();
  const g=nativeFixture(),other=API.createDeviceBridge({environment:env(),provider:g.provider});await other.connectNative();g.connection.connected=false;
  assert.equal(other.status().native.connected,false);assert.equal(other.status().native.capabilities,null);await assert.rejects(other.storePreset(preset()),error=>error.code==='NOT_CONNECTED');other.dispose();
});

test('cancel immediately rejects a pending MIDI port open and closes its late result',async()=>{
  const pending=deferred(),input=events({id:'pending',name:'Pending port',type:'input',state:'connected',open:()=>pending.promise,async close(){this.closed=true;}});
  const access=events({inputs:new Map([[input.id,input]]),outputs:new Map()}),bridge=API.createDeviceBridge({environment:env({navigator:{requestMIDIAccess:async()=>access}})});
  await bridge.listMIDIPorts();const promise=bridge.subscribeMidiInput(input.id,()=>{});bridge.cancel();await assert.rejects(promise,error=>error.code==='ABORTED');
  pending.resolve(input);await wait(5);assert.equal(input.closed,true);assert.equal(input.count('midimessage'),0);bridge.dispose();
});

test('a timed-out native handshake cannot leave a late connection owned by the bridge',async()=>{
  const pending=deferred(),f=nativeFixture({handshake:()=>pending.promise}),bridge=API.createDeviceBridge({environment:env(),provider:f.provider,timeoutMs:100});
  const promise=bridge.connectNative();await assert.rejects(promise,error=>error.code==='TIMEOUT');pending.resolve({connected:true});await wait(5);
  assert.equal(bridge.status().native.connected,false);assert.equal(f.connection.connected,false);bridge.dispose();
});
