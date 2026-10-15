/* Mock protocol conformance fixtures only: no Bluetooth or physical devices. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
const source=await readFile(new URL('../dist/device-bridge.js',import.meta.url),'utf8');
const context=vm.createContext({ArrayBuffer,Uint8Array,DataView});vm.runInContext(source,context);
const decode=context.SVDeviceBridge.decodeBleMidiPacket;
const plain=result=>({events:Array.from(result.events,e=>({data:[...e.data],timestamp:e.timestamp})),state:JSON.parse(JSON.stringify(result.state)),ignoredRealtime:result.ignoredRealtime});
const reject=(packet,code,state)=>assert.throws(()=>decode(packet,state),error=>error.code===code&&Number.isInteger(error.offset));

test('complete note-on and note-off preserve channels and 13-bit sender timestamps',()=>{
  const result=plain(decode([0x98,0x87,0x9f,69,110,0x89,0x8f,69,52]));
  assert.deepEqual(result.events,[{data:[0x9f,69,110],timestamp:3079},{data:[0x8f,69,52],timestamp:3081}]);
  assert.equal(result.state.lastTimestamp13,3081);assert.equal(result.state.packetsDecoded,1);
});

test('running-status data may share a timestamp or use a new timestamp',()=>{
  const result=plain(decode([0x80,0x81,0x92,69,40,70,41,0x82,69,0,71,99]));
  assert.deepEqual(result.events,[{data:[0x92,69,40],timestamp:1},{data:[0x92,70,41],timestamp:1},{data:[0x82,69,0],timestamp:2},{data:[0x92,71,99],timestamp:2}]);
});

test('NoteOn velocity zero is semantically normalized to NoteOff without altering wire running status',()=>{
  const result=decode([0x80,0x80,0x94,64,0,65,127]);
  assert.deepEqual([...result.events[0].data],[0x84,64,0]);assert.deepEqual([...result.events[1].data],[0x94,65,127]);
});

test('program change and channel pressure consume one data byte, other channels consume two',()=>{
  const result=plain(decode([0x80,0x80,0xc1,12,13,0x81,0xd1,51,52,0x82,0xb1,74,88,0x83,0xe1,0,64,0x84,0xa1,69,44]));
  assert.deepEqual(result.events.map(e=>e.data),[[0xc1,12],[0xc1,13],[0xd1,51],[0xd1,52],[0xb1,74,88],[0xe1,0,64],[0xa1,69,44]]);
});

test('low timestamp rollover increments the header high bits inside one packet',()=>{
  const result=decode([0x81,0xfe,0x90,60,99,0x81,0x80,60,0]);assert.equal(result.events[0].timestamp,254);assert.equal(result.events[1].timestamp,257);
});

test('timestamp rollover from 8191 to 0 remains a raw 13-bit source value',()=>{
  const first=decode([0xbf,0xff,0x90,60,99,0x80,0x80,60,0]);assert.equal(first.events[0].timestamp,8191);assert.equal(first.events[1].timestamp,0);
  const second=decode([0x80,0x85,0x90,61,90],first.state);assert.equal(second.events[0].timestamp,5);assert.equal(second.state.packetsDecoded,2);
});

test('reserved header bit is ignored but high timestamp bits are kept',()=>{
  const result=decode([0xff,0xff,0x90,60,99]);assert.equal(result.events[0].timestamp,8191);
});

test('high-bit timestamp bytes cannot be mistaken for System Common or real-time statuses',()=>{
  for(const timestamp of [0x80,0x90,0xf0,0xf7,0xf8,0xff]){
    const result=decode([0x80,timestamp,0x90,60,99]);assert.equal(result.events[0].timestamp,timestamp&0x7f);assert.equal(result.ignoredRealtime,0);
  }
});

test('timestamped realtime can interrupt a pending channel message without destroying it',()=>{
  const result=plain(decode([0x80,0x81,0x90,60,0x82,0xf8,100,61,90]));
  assert.deepEqual(result.events,[{data:[0x90,60,100],timestamp:1},{data:[0x90,61,90],timestamp:2}]);assert.equal(result.ignoredRealtime,1);
});

test('defined realtime statuses are counted and do not clear channel running status',()=>{
  for(const realtime of [0xf8,0xfa,0xfb,0xfc,0xfe,0xff]){
    const result=decode([0x80,0x81,0x91,60,80,0x82,realtime,60,0]);assert.equal(result.ignoredRealtime,1);assert.equal(result.events.length,2);assert.deepEqual([...result.events[1].data],[0x81,60,0]);
  }
});

test('realtime-only packets generate no artificial channel notes',()=>{
  const result=decode([0x80,0x80,0xf8,0x81,0xfe]);assert.equal(result.events.length,0);assert.equal(result.ignoredRealtime,2);assert.equal(result.state.lastTimestamp13,1);
});

test('running status is not carried across packet boundaries',()=>{
  const first=decode([0x80,0x81,0x90,60,100]);reject([0x80,0x82,60,0],'BLE_MIDI_RUNNING_STATUS_REQUIRED',first.state);
  assert.equal(decode([0x80,0x82,0x90,60,0],first.state).events[0].data[0],0x80);
});

for(const status of [0xf0,0xf7])test('SysEx status '+status.toString(16)+' rejects the whole packet',()=>reject([0x80,0x81,status,1,2],'BLE_MIDI_SYSEX_UNSUPPORTED'));
for(const status of [0xf1,0xf2,0xf3,0xf4,0xf5,0xf6])test('System Common '+status.toString(16)+' is explicitly unsupported',()=>reject([0x80,0x81,status,1,2],'BLE_MIDI_SYSTEM_COMMON_UNSUPPORTED'));
for(const status of [0xf9,0xfd])test('undefined realtime '+status.toString(16)+' is rejected',()=>reject([0x80,0x81,status],'BLE_MIDI_UNDEFINED_REALTIME'));

test('a SysEx continuation cannot be interpreted with an old channel running status',()=>{
  const first=decode([0x80,0x81,0x90,60,100]);reject([0x80,60,0],'BLE_MIDI_TIMESTAMP_REQUIRED',first.state);
});

test('truncated note data cannot escape as a partial event list',()=>{
  reject([0x80,0x81,0x90,60],'BLE_MIDI_TRUNCATED_MESSAGE');
  reject([0x80,0x81,0x90,60,100,61],'BLE_MIDI_TRUNCATED_MESSAGE');
  reject([0x80,0x81,0x90,60,100,0x82],'BLE_MIDI_TRUNCATED_TIMESTAMP');
  reject([0x80,0x81,0x90,60,0x82,0x80,60,0],'BLE_MIDI_TRUNCATED_MESSAGE');
});

test('timestamps inside an incomplete channel message require an immediately following realtime status',()=>{
  reject([0x80,0x81,0x90,60,0x82,100],'BLE_MIDI_TRUNCATED_MESSAGE');
  reject([0x80,0x81,0x90,60,0xf8,100],'BLE_MIDI_TRUNCATED_MESSAGE');
});

test('more than one low-byte rollover is rejected instead of guessing a long packet timeline',()=>{
  reject([0x80,0xff,0x90,60,100,0x80,60,101,0xff,60,102,0x80,60,103],'BLE_MIDI_UNSUPPORTED_TIMING');
});

test('input size, byte ranges, missing headers and corrupt previous states are bounded',()=>{
  for(const input of [null,{},'8080903c64',[256,128,144],[-1,128,144],[128,128,NaN],[128,128,.5],new Uint16Array([128,128,144]),new Uint8Array(513),Array(3)])reject(input,'BLE_MIDI_INVALID_PACKET');
  for(const input of [[],[128],[128,128]])reject(input,'BLE_MIDI_TRUNCATED_PACKET');
  reject([0,128,144,60,100],'BLE_MIDI_INVALID_HEADER');
  for(const state of [{},{packetsDecoded:-1,lastTimestamp13:0},{packetsDecoded:1,lastTimestamp13:8192},{packetsDecoded:1,lastTimestamp13:null}])reject([128,128,144,60,100],'BLE_MIDI_INVALID_STATE',state);
});

test('DataView byte offsets and ArrayBuffer input are decoded without mutating data or prior state',()=>{
  const original=new Uint8Array([9,9,0x80,0x81,0x90,60,100,9]);const state=Object.freeze({packetsDecoded:2,lastTimestamp13:8191});
  const result=decode(new DataView(original.buffer,2,5),state);assert.deepEqual([...result.events[0].data],[0x90,60,100]);assert.equal(result.state.packetsDecoded,3);assert.equal(state.packetsDecoded,2);
  result.events[0].data[1]=99;assert.equal(original[5],60);assert.equal(decode(new Uint8Array([0x80,0x81,0x90,60,100]).buffer).events[0].data[1],60);
});

test('generated channel fixtures cover all 16 channels with explicit and running statuses',()=>{
  for(let channel=0;channel<16;channel++)for(const kind of [0x80,0x90,0xa0,0xb0,0xc0,0xd0,0xe0]){
    const status=kind|channel,data=kind===0xc0||kind===0xd0?[55]:[55,99];
    const result=decode([0x80,0x87,status,...data,...data,0x88,...data]);assert.equal(result.events.length,3);
    for(const event of result.events)assert.deepEqual([...event.data],[status,...data]);assert.equal(result.events[2].timestamp,8);
  }
});

test('bounded malformed packet corpus only returns valid complete channel messages or clear errors',()=>{
  let seed=1254;const random=()=>{seed^=seed<<13;seed^=seed>>>17;seed^=seed<<5;return seed>>>0;};
  for(let sample=0;sample<300;sample++){
    const bytes=Uint8Array.from({length:random()%65},()=>random()%256);
    try{const result=decode(bytes);for(const event of result.events){assert.ok(event.data[0]>=0x80&&event.data[0]<0xf0);assert.ok(event.timestamp>=0&&event.timestamp<=8191);assert.equal(event.data.length,[0xc0,0xd0].includes(event.data[0]&0xf0)?2:3);assert.ok([...event.data].slice(1).every(v=>v<128));}}
    catch(error){assert.match(error.code,/^BLE_MIDI_/);assert.ok(Number.isInteger(error.offset));}
  }
});
