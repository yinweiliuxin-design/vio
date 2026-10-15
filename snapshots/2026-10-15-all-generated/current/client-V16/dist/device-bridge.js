/* Original SmartVio transport adapter. BLE MIDI packets are not audio or raw MIDI.
 * Protocol UUIDs checked against AOSP BluetoothMidiDevice.java (f0a41d1) and
 * https://docs.espressif.com/projects/esp-iot-solution/en/latest/bluetooth/ble_midi.html
 * No Apple/GarageBand code, samples, guessed DSP commands or automatic chooser. */
(function(root,factory){
  'use strict';
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  else root.SVDeviceBridge=api;
})(typeof globalThis==='object'?globalThis:this,function(){
  'use strict';
  const BLE_MIDI_SERVICE='03b80e5a-ede8-4b33-a751-6ce34ec4c700';
  const BLE_MIDI_CHARACTERISTIC='7772e5db-3868-4112-a1a9-f2669d106bf3';
  const AUDIO_TYPES=['audio/webm;codecs=opus','audio/webm','audio/mp4','audio/ogg;codecs=opus'];
  const VIDEO_TYPES=['video/webm;codecs=vp8,opus','video/webm;codecs=vp9,opus','video/webm','video/mp4'];
  class DeviceBridgeError extends Error{
    constructor(code,message,cause){super(message);this.name='DeviceBridgeError';this.code=code;this.causeName=cause?.name||null;}
  }
  const fail=(code,message,cause)=>new DeviceBridgeError(code,message,cause);
  /* Receive-only BLE MIDI 1.0 channel-message subset. Original implementation.
   * Public format checks: AOSP BluetoothPacketDecoder.java at 4bbbfaa and
   * https://microsoft.github.io/MIDI/kb/ble-midi-transport-architecture/
   * Sender timestamps are modulo 8192 ms; they are not local performance time.
   * No SysEx, System Common, clock correlation, UMP or cross-packet running status. */
  function decodeBleMidiPacket(packet,previousState=null){
    const invalid=(code,message,offset)=>{const error=fail(code,message);error.offset=offset;throw error;};
    let bytes;
    if(Array.isArray(packet)){
      if(packet.length>512||Array.from(packet).some(v=>!Number.isInteger(v)||v<0||v>255))invalid('BLE_MIDI_INVALID_PACKET','BLE MIDI 数据必须是至多 512 个合法字节',0);
      bytes=Uint8Array.from(packet);
    }else if(ArrayBuffer.isView(packet)){
      if(packet.BYTES_PER_ELEMENT!==1&&Object.prototype.toString.call(packet)!=='[object DataView]')invalid('BLE_MIDI_INVALID_PACKET','BLE MIDI 需要字节数组或 DataView',0);
      if(packet.byteLength>512)invalid('BLE_MIDI_INVALID_PACKET','BLE MIDI 数据超过 512 字节限制',0);
      bytes=new Uint8Array(packet.buffer,packet.byteOffset,packet.byteLength).slice();
    }else if(Object.prototype.toString.call(packet)==='[object ArrayBuffer]'){
      if(packet.byteLength>512)invalid('BLE_MIDI_INVALID_PACKET','BLE MIDI 数据超过 512 字节限制',0);
      bytes=new Uint8Array(packet).slice();
    }else invalid('BLE_MIDI_INVALID_PACKET','BLE MIDI 需要字节数组或 DataView',0);
    if(bytes.length<3)invalid('BLE_MIDI_TRUNCATED_PACKET','BLE MIDI 数据不完整：缺少包头、时间戳或消息',bytes.length);
    if((bytes[0]&0x80)===0)invalid('BLE_MIDI_INVALID_HEADER','BLE MIDI 包头的最高位必须为 1',0);
    let packetsDecoded=0;
    if(previousState!==null&&previousState!==undefined){
      if(typeof previousState!=='object'||Array.isArray(previousState)||!Number.isSafeInteger(previousState.packetsDecoded)||previousState.packetsDecoded<0||previousState.packetsDecoded>=Number.MAX_SAFE_INTEGER||!Number.isInteger(previousState.lastTimestamp13)||previousState.lastTimestamp13<0||previousState.lastTimestamp13>8191)invalid('BLE_MIDI_INVALID_STATE','BLE MIDI 上一次解析状态无效，请在断连后清空状态',0);
      packetsDecoded=previousState.packetsDecoded;
    }
    const events=[];
    let high=(bytes[0]&0x3f)<<7,lastLow=null,timestamp=null,afterTimestamp=false,wraps=0;
    let running=0,pending=null,interruption=false,ignoredRealtime=0;
    for(let index=1;index<bytes.length;index++){
      const byte=bytes[index];
      if((byte&0x80)!==0&&!afterTimestamp){
        const low=byte&0x7f;
        if(lastLow!==null&&low<lastLow){
          if(++wraps>1)invalid('BLE_MIDI_UNSUPPORTED_TIMING','本解析器只支持包内一次时间戳低位回绕',index);
          high=(high+128)&0x1f80;
        }
        timestamp=high|low;lastLow=low;afterTimestamp=true;interruption=!!pending;continue;
      }
      if(timestamp===null)invalid('BLE_MIDI_TIMESTAMP_REQUIRED','BLE MIDI 消息缺少时间戳；本解析器不支持 SysEx 续包',index);
      afterTimestamp=false;
      if(interruption&&byte<0xf8)invalid('BLE_MIDI_TRUNCATED_MESSAGE','未完成的 MIDI 通道消息只能由实时消息打断',index);
      interruption=false;
      if(byte>=0xf8){
        if(byte===0xf9||byte===0xfd)invalid('BLE_MIDI_UNDEFINED_REALTIME','不支持未定义的 MIDI 实时状态',index);
        ignoredRealtime++;continue;
      }
      if(byte>=0xf0){
        if(byte===0xf0||byte===0xf7)invalid('BLE_MIDI_SYSEX_UNSUPPORTED','本解析器不支持 SysEx 或其分包，数据未作为音符接收',index);
        invalid('BLE_MIDI_SYSTEM_COMMON_UNSUPPORTED','本解析器只接收通道消息，不支持 System Common',index);
      }
      if(byte>=0x80){
        if(pending)invalid('BLE_MIDI_TRUNCATED_MESSAGE','MIDI 通道消息尚未完成就出现新的状态字节',index);
        running=byte;pending={status:byte,length:(byte&0xf0)===0xc0||(byte&0xf0)===0xd0?1:2,data:[],timestamp};continue;
      }
      if(!pending){
        if(!running)invalid('BLE_MIDI_RUNNING_STATUS_REQUIRED','每个 BLE MIDI 包的首条通道消息必须包含状态字节',index);
        pending={status:running,length:(running&0xf0)===0xc0||(running&0xf0)===0xd0?1:2,data:[],timestamp};
      }
      pending.data.push(byte);
      if(pending.data.length===pending.length){
        const statusByte=(pending.status&0xf0)===0x90&&pending.data[1]===0?(pending.status&0x0f)|0x80:pending.status;
        events.push({data:Uint8Array.from([statusByte,...pending.data]),timestamp:pending.timestamp});pending=null;
      }
    }
    if(afterTimestamp)invalid('BLE_MIDI_TRUNCATED_TIMESTAMP','BLE MIDI 最后一个时间戳后缺少消息',bytes.length);
    if(pending)invalid('BLE_MIDI_TRUNCATED_MESSAGE','BLE MIDI 最后一条通道消息缺少数据字节',bytes.length);
    return {events,state:{lastTimestamp13:timestamp,packetsDecoded:packetsDecoded+1},ignoredRealtime,sourceClock:'ble-midi-13-bit-ms'};
  }
  const short=value=>typeof value==='string'?value.slice(0,160):'';
  const safeError=error=>({code:error?.code||error?.name||'TRANSPORT_ERROR',message:short(error?.message)||'连接失败'});
  const plain=value=>!!value&&typeof value==='object'&&!Array.isArray(value)&&Object.prototype.toString.call(value)==='[object Object]';
  const cleanName=value=>typeof value==='string'?value.replace(/[\u0000-\u001f\u007f]/g,'').slice(0,160):'';
  function supportedTypes(env,types){return types.filter(type=>{try{return env.MediaRecorder?.isTypeSupported?.(type)===true;}catch{return false;}});}
  function detectCapabilities(env=typeof globalThis==='object'?globalThis:{}){
    const secure=env.isSecureContext===true,nav=env.navigator||{};
    return Object.freeze({secureContext:secure,webBluetooth:secure&&typeof nav.bluetooth?.requestDevice==='function',
      webMIDI:secure&&typeof nav.requestMIDIAccess==='function',webAudio:typeof(env.AudioContext||env.webkitAudioContext)==='function',
      mediaInput:secure&&typeof nav.mediaDevices?.getUserMedia==='function',mediaRecorder:typeof env.MediaRecorder==='function',
      audioRecordingTypes:Object.freeze(supportedTypes(env,AUDIO_TYPES)),videoRecordingTypes:Object.freeze(supportedTypes(env,VIDEO_TYPES)),
      endToEndLatencyMeasured:false,endToEndLatencyMs:null});
  }
  function createDeviceBridge(options={}){
    const env=options.environment||(typeof globalThis==='object'?globalThis:{}),nav=env.navigator||{};
    const timer=options.setTimeout||env.setTimeout?.bind(env),untimer=options.clearTimeout||env.clearTimeout?.bind(env);
    const Controller=env.AbortController||(typeof AbortController==='function'?AbortController:null);
    if(!timer||!untimer||!Controller)throw fail('UNSUPPORTED','当前环境缺少连接计时或取消接口');
    const now=options.now||(()=>env.performance?.now?.()??Date.now());
    const timeoutMs=Math.min(30000,Math.max(100,Number(options.timeoutMs)||5000));
    const retryDelays=(Array.isArray(options.reconnectDelayMs)?options.reconnectDelayMs:[500,1000,2000]).slice(0,4).map(v=>Math.min(30000,Math.max(0,Number(v)||0)));
    const observers=new Set(),packets=new Set();
    if(typeof options.onState==='function')observers.add(options.onState);
    if(typeof options.onMidiPacket==='function')packets.add(options.onMidiPacket);
    const state={ble:{status:'disconnected',connected:false,protocol:'ble-midi',deviceId:null,deviceName:null,attempt:0,error:null},
      midi:{status:'idle',ports:[],error:null},native:{status:'unavailable',connected:false,providerDeclaration:null,deviceId:null,capabilities:null,error:null},
      lastWrite:null,endToEndLatencyMeasured:false,endToEndLatencyMs:null};
    let disposed=false,bleGeneration=0,bleDevice=null,bleHandler=null,bleCharacteristic=null,bleNotify=null,bleToken=null,retryTimer=null,retries=0;
    let midiGeneration=0,midiAccess=null,midiStateHandler=null,midiToken=null;
    const midiSubscriptions=new Map(),midiOpenTokens=new Set();
    let nativeGeneration=0,nativeToken=null,nativeHandshake=null,nativeUnsubscribe=null,writeToken=null,writing=false;
    let requestCounter=0;
    const provider=options.provider||options.controlProfile||null;
    const clone=value=>JSON.parse(JSON.stringify(value));
    const status=()=>{
      const snapshot=clone({...state,capabilities:detectCapabilities(env)});
      if(snapshot.ble.connected&&bleDevice?.gatt?.connected!==true){snapshot.ble.status='disconnected';snapshot.ble.connected=false;}
      if(snapshot.native.connected){let actual;try{actual=provider?.getConnectionState?.();}catch{}
        if(!plain(actual)||actual.connected!==true||actual.deviceId!==snapshot.native.deviceId){snapshot.native.status='disconnected';snapshot.native.connected=false;snapshot.native.capabilities=null;}}
      return snapshot;
    };
    const notify=()=>{const snapshot=status();for(const callback of observers){try{callback(snapshot);}catch{}}};
    const set=(section,update)=>{Object.assign(state[section],update);notify();};
    const live=()=>{if(disposed)throw fail('DISPOSED','设备接口已关闭');};
    const token=(generation,valid)=>({generation,valid,controller:new Controller()});
    const guard=op=>{live();if(op.controller.signal.aborted||!op.valid())throw fail('ABORTED','连接操作已取消');};
    const abort=op=>{try{op?.controller.abort();}catch{}};
    function deadline(work,op,lateCleanup,limit=timeoutMs){
      guard(op);
      return new Promise((resolve,reject)=>{
        let finished=false;
        const finish=(error,result)=>{if(finished)return;finished=true;untimer(id);op.controller.signal.removeEventListener('abort',onAbort);error?reject(error):resolve(result);};
        const onAbort=()=>finish(fail('ABORTED','连接操作已取消'));
        const id=timer(()=>{finish(fail('TIMEOUT','设备没有在规定时间内确认请求'));abort(op);},limit);
        op.controller.signal.addEventListener('abort',onAbort,{once:true});
        let promise;try{promise=work();}catch(error){finish(error);return;}
        Promise.resolve(promise).then(result=>{
          if(finished){try{lateCleanup?.(result);}catch{}return;}
          try{guard(op);finish(null,result);}catch(error){try{lateCleanup?.(result);}catch{}finish(error);}
        },error=>finish(error));
      });
    }
    function emitPacket(value,transport,extra={}){
      if(disposed)return;
      let bytes;
      if(ArrayBuffer.isView(value))bytes=new Uint8Array(value.buffer,value.byteOffset,value.byteLength).slice();
      else if(value instanceof ArrayBuffer)bytes=new Uint8Array(value).slice();
      else return;
      if(!bytes.length||bytes.length>(transport==='ble-midi'?512:4096))return;
      for(const callback of packets){try{callback({...extra,bytes:bytes.slice(),transport,receivedAt:now()});}catch{}}
    }
    function removeCharacteristic(){
      const characteristic=bleCharacteristic;
      if(characteristic&&bleNotify)characteristic.removeEventListener?.('characteristicvaluechanged',bleNotify);
      bleCharacteristic=null;bleNotify=null;
      if(characteristic?.stopNotifications)try{Promise.resolve(characteristic.stopNotifications()).catch(()=>{});}catch{}
    }
    function disconnectGatt(device){try{device?.gatt?.disconnect();}catch{}}
    function resetBle(){
      bleGeneration++;abort(bleToken);bleToken=null;if(retryTimer!==null)untimer(retryTimer);retryTimer=null;
      removeCharacteristic();if(bleDevice&&bleHandler)bleDevice.removeEventListener?.('gattserverdisconnected',bleHandler);
      const old=bleDevice;bleDevice=null;bleHandler=null;disconnectGatt(old);retries=0;
    }
    async function openBle(device,op){
      const server=await deadline(()=>device.gatt.connect(),op,()=>{if(bleDevice!==device||!['connecting','reconnecting','connected'].includes(state.ble.status))disconnectGatt(device);});
      guard(op);if(!server||device.gatt.connected!==true)throw fail('NOT_CONNECTED','蓝牙设备尚未建立 GATT 连接');
      const service=await deadline(()=>server.getPrimaryService(BLE_MIDI_SERVICE),op);guard(op);
      const characteristic=await deadline(()=>service.getCharacteristic(BLE_MIDI_CHARACTERISTIC),op);guard(op);
      if(!characteristic||typeof characteristic.startNotifications!=='function'||typeof characteristic.readValue!=='function'||typeof characteristic.addEventListener!=='function'||typeof characteristic.removeEventListener!=='function')throw fail('UNSUPPORTED','设备缺少标准 BLE MIDI 读或通知能力');
      if(characteristic.properties&&(characteristic.properties.notify===false||characteristic.properties.read===false))throw fail('UNSUPPORTED','设备未声明标准 BLE MIDI 读或通知能力');
      await deadline(()=>characteristic.readValue(),op);guard(op);
      removeCharacteristic();bleCharacteristic=characteristic;
      const generation=bleGeneration;
      bleNotify=event=>{if(generation===bleGeneration&&state.ble.connected&&device.gatt.connected===true)emitPacket(event?.target?.value,'ble-midi',{deviceId:state.ble.deviceId});};
      characteristic.addEventListener?.('characteristicvaluechanged',bleNotify);
      await deadline(()=>characteristic.startNotifications(),op,()=>{if(bleCharacteristic!==characteristic)try{Promise.resolve(characteristic.stopNotifications()).catch(()=>{});}catch{}});
      guard(op);if(device.gatt.connected!==true)throw fail('NOT_CONNECTED','订阅 MIDI 时蓝牙设备已断开');
      set('ble',{status:'connected',connected:true,attempt:retries,error:null});
      return status();
    }
    function retryBle(generation,error){
      if(disposed||generation!==bleGeneration||!bleDevice)return;
      removeCharacteristic();
      if(options.autoReconnect===false||retries>=retryDelays.length){set('ble',{status:'disconnected',connected:false,error:safeError(error)});return;}
      const delay=retryDelays[retries++],device=bleDevice;
      set('ble',{status:'reconnecting',connected:false,attempt:retries,error:safeError(error)});
      retryTimer=timer(async()=>{
        retryTimer=null;if(disposed||generation!==bleGeneration||device!==bleDevice)return;
        abort(bleToken);const op=token(generation,()=>generation===bleGeneration);bleToken=op;
        try{await openBle(device,op);}catch(error){if(generation!==bleGeneration||disposed)return;disconnectGatt(device);retryBle(generation,error);}
      },delay);
    }
    async function connectBleMidi(){
      live();if(!detectCapabilities(env).webBluetooth)throw fail('UNSUPPORTED','当前浏览器不支持安全的 Web Bluetooth，请使用支持的浏览器或原生端');
      resetBle();const generation=bleGeneration,op=token(generation,()=>generation===bleGeneration);bleToken=op;
      set('ble',{status:'choosing',connected:false,deviceId:null,deviceName:null,attempt:0,error:null});
      try{
        const device=await deadline(()=>nav.bluetooth.requestDevice({filters:[{services:[BLE_MIDI_SERVICE]}]}),op,null,30000);
        guard(op);if(!device?.gatt||typeof device.gatt.connect!=='function'||typeof device.addEventListener!=='function'||typeof device.removeEventListener!=='function')throw fail('UNSUPPORTED','选择的设备没有可用 GATT 或断连通知接口');
        bleDevice=device;bleHandler=()=>{
          if(generation!==bleGeneration||device!==bleDevice||disposed||state.ble.status!=='connected')return;
          set('ble',{status:'disconnected',connected:false,error:{code:'DISCONNECTED',message:'真实蓝牙连接已断开'}});
          retryBle(generation,fail('DISCONNECTED','真实蓝牙连接已断开'));
        };
        device.addEventListener?.('gattserverdisconnected',bleHandler);
        set('ble',{status:'connecting',connected:false,deviceId:cleanName(device.id)||null,deviceName:cleanName(device.name)||null});
        return await openBle(device,op);
      }catch(error){
        if(generation===bleGeneration&&!disposed){removeCharacteristic();disconnectGatt(bleDevice);set('ble',{status:'disconnected',connected:false,error:safeError(error)});}
        throw error;
      }
    }
    function portRows(){return midiAccess?[...midiAccess.inputs.values(),...midiAccess.outputs.values()].map(port=>({id:cleanName(port.id),name:cleanName(port.name),type:port.type==='input'?'input':'output',state:port.state==='connected'?'connected':'disconnected'})):[];}
    function closeMidi(){
      midiGeneration++;abort(midiToken);midiToken=null;
      for(const op of midiOpenTokens)abort(op);midiOpenTokens.clear();
      for(const subscription of [...midiSubscriptions.values()])subscription.stop();
      if(midiAccess&&midiStateHandler)midiAccess.removeEventListener?.('statechange',midiStateHandler);
      midiAccess=null;midiStateHandler=null;
    }
    async function listMIDIPorts(){
      live();if(!detectCapabilities(env).webMIDI)throw fail('UNSUPPORTED','当前浏览器不支持安全的 Web MIDI');
      closeMidi();const generation=midiGeneration,op=token(generation,()=>generation===midiGeneration);midiToken=op;
      set('midi',{status:'requesting',ports:[],error:null});
      try{
        const access=await deadline(()=>nav.requestMIDIAccess({sysex:false}),op);
        guard(op);if(!access?.inputs?.values||!access?.outputs?.values)throw fail('INVALID_RESPONSE','系统没有返回有效 MIDI 端口');
        midiAccess=access;midiStateHandler=()=>{if(generation!==midiGeneration||disposed)return;for(const subscription of [...midiSubscriptions.values()])if(subscription.port.state!=='connected')subscription.stop();set('midi',{status:'ready',ports:portRows(),error:null});};
        access.addEventListener?.('statechange',midiStateHandler);set('midi',{status:'ready',ports:portRows(),error:null});return clone(state.midi.ports);
      }catch(error){if(generation===midiGeneration&&!disposed)set('midi',{status:'error',ports:[],error:safeError(error)});throw error;}
    }
    async function subscribeMidiInput(id,callback){
      live();if(typeof callback!=='function')throw fail('INVALID_VALUE','MIDI 输入回调必须是函数');
      const port=midiAccess?.inputs?.get(id);if(!port||port.state!=='connected')throw fail('NOT_CONNECTED','没有找到已连接的 MIDI 输入端口');
      midiSubscriptions.get(id)?.stop();const generation=midiGeneration,op=token(generation,()=>generation===midiGeneration);
      midiOpenTokens.add(op);
      try{await deadline(()=>port.open?.(),op,()=>{if(generation!==midiGeneration)try{Promise.resolve(port.close?.()).catch(()=>{});}catch{}});guard(op);}finally{midiOpenTokens.delete(op);}
      if(port.state!=='connected')throw fail('NOT_CONNECTED','MIDI 输入端口已断开');
      let stopped=false;const previous=port.onmidimessage;
      const handler=event=>{
        if(stopped||disposed||generation!==midiGeneration||port.state!=='connected')return;
        const value=event?.data;if(!ArrayBuffer.isView(value)||!value.byteLength||value.byteLength>4096)return;
        const bytes=new Uint8Array(value.buffer,value.byteOffset,value.byteLength).slice();
        try{callback({bytes,transport:'web-midi',portId:cleanName(port.id),timestamp:Number.isFinite(event.receivedTime)?event.receivedTime:now(),receivedAt:now()});}catch{}
      };
      let wrapper;if(port.addEventListener)port.addEventListener('midimessage',handler);else{wrapper=event=>{try{previous?.call(port,event);}finally{handler(event);}};port.onmidimessage=wrapper;}
      const subscription={port,stop(){if(stopped)return;stopped=true;if(port.removeEventListener)port.removeEventListener('midimessage',handler);else if(port.onmidimessage===wrapper)port.onmidimessage=previous||null;try{Promise.resolve(port.close?.()).catch(()=>{});}catch{}if(midiSubscriptions.get(id)===subscription)midiSubscriptions.delete(id);}};
      midiSubscriptions.set(id,subscription);return subscription.stop;
    }
    function validProvider(){
      if(!plain(provider)||!['native','control-profile'].includes(provider.kind)||!['verified','demo'].includes(provider.verification)||!cleanName(provider.id)||typeof provider.handshake!=='function'||typeof provider.getConnectionState!=='function')throw fail('UNSUPPORTED','尚未配置明确的原生适配器或已核对控制协议');
    }
    const requestId=()=>{const random=env.crypto?.randomUUID?.();return random||'sv-'+Date.now().toString(36)+'-'+(++requestCounter).toString(36);};
    function connectionConfirmed(reply){const actual=provider.getConnectionState();return plain(actual)&&actual.connected===true&&actual.deviceId===reply.deviceId;}
    function ranges(value){
      if(!plain(value))return {};
      const result={};for(const [key,range] of Object.entries(value)){
        if(!/^[A-Za-z][A-Za-z0-9_-]{0,39}$/.test(key)||['constructor','prototype','__proto__'].includes(key)||!plain(range)||!Number.isFinite(range.min)||!Number.isFinite(range.max)||range.min>range.max)throw fail('INVALID_RESPONSE','设备参数范围声明无效');
        result[key]={min:range.min,max:range.max};
      }
      if(Object.keys(result).length>64)throw fail('INVALID_RESPONSE','设备参数声明过长');return result;
    }
    function closeNative(){
      nativeGeneration++;abort(nativeToken);abort(writeToken);nativeToken=null;writeToken=null;nativeHandshake=null;writing=false;
      if(typeof nativeUnsubscribe==='function')try{nativeUnsubscribe();}catch{}nativeUnsubscribe=null;
    }
    async function connectNative(){
      live();validProvider();closeNative();const generation=nativeGeneration,op=token(generation,()=>generation===nativeGeneration);nativeToken=op;
      const id=requestId();set('native',{status:'connecting',connected:false,providerDeclaration:provider.verification,deviceId:null,capabilities:null,error:null});
      try{
        const reply=await deadline(()=>provider.handshake({requestId:id,signal:op.controller.signal}),op,()=>{
          if(!nativeHandshake&&state.native.status!=='connecting')try{Promise.resolve(provider.disconnect?.()).catch(()=>{});}catch{}
        });guard(op);
        if(!plain(reply)||reply.requestId!==id||reply.connected!==true||!cleanName(reply.deviceId)||typeof reply.protocolVersion!=='string'||!reply.protocolVersion||!plain(reply.capabilities)||!connectionConfirmed(reply))throw fail('INVALID_RESPONSE','设备握手或连接状态没有得到有效确认');
        const paramRanges=ranges(reply.parameterRanges);
        nativeHandshake={deviceId:reply.deviceId,protocolVersion:reply.protocolVersion,presetSchemaVersion:Number.isInteger(reply.presetSchemaVersion)?reply.presetSchemaVersion:null,
          capabilities:{parameterControl:reply.capabilities.parameterControl===true,presetStore:reply.capabilities.presetStore===true},parameterRanges:paramRanges};
        if(typeof provider.subscribeConnection==='function')nativeUnsubscribe=provider.subscribeConnection(actual=>{
          if(generation!==nativeGeneration||disposed)return;
          if(!plain(actual)||actual.connected!==true||actual.deviceId!==nativeHandshake?.deviceId){abort(writeToken);nativeHandshake=null;set('native',{status:'disconnected',connected:false,capabilities:null,error:{code:'DISCONNECTED',message:'原生设备连接已断开'}});}
        });
        const demo=provider.verification==='demo';set('native',{status:demo?'demo':'connected',connected:!demo,deviceId:reply.deviceId,capabilities:nativeHandshake.capabilities,error:null});
        return status();
      }catch(error){if(generation===nativeGeneration&&!disposed){nativeHandshake=null;set('native',{status:'disconnected',connected:false,capabilities:null,error:safeError(error)});}throw error;}
    }
    function checkedPreset(value){
      if(!plain(value)||typeof value.name!=='string'||!value.name.trim()||value.name.length>80||!plain(value.parameters)||value.schemaVersion!==nativeHandshake.presetSchemaVersion)throw fail('INVALID_VALUE','预设名称、schema 或参数无效');
      const parameters={};for(const [key,item] of Object.entries(value.parameters)){
        const range=nativeHandshake.parameterRanges[key];if(!Object.prototype.hasOwnProperty.call(nativeHandshake.parameterRanges,key)||!range||!Number.isFinite(item)||item<range.min||item>range.max)throw fail('INVALID_VALUE','参数不在设备声明范围内：'+cleanName(key));parameters[key]=item;
      }
      if(!Object.keys(parameters).length)throw fail('INVALID_VALUE','预设没有设备支持的参数');
      if(value.group!==undefined&&(typeof value.group!=='string'||value.group.length>80))throw fail('INVALID_VALUE','预设分组无效');
      const result={schemaVersion:value.schemaVersion,name:value.name.trim(),group:value.group||'',parameters};
      if(value.slot!==undefined){if(!Number.isInteger(value.slot)||value.slot<0||value.slot>127)throw fail('INVALID_VALUE','预设槽位无效');result.slot=value.slot;}
      return result;
    }
    async function storePreset(value){
      live();validProvider();if(provider.verification!=='verified')throw fail('UNVERIFIED_PROVIDER','演示适配器不能确认写入真实琴端');
      if(!nativeHandshake||!state.native.connected||!connectionConfirmed(nativeHandshake))throw fail('NOT_CONNECTED','需要先确认真实设备连接');
      if(!nativeHandshake.capabilities.parameterControl||!nativeHandshake.capabilities.presetStore||typeof provider.storePreset!=='function'||nativeHandshake.presetSchemaVersion===null)throw fail('UNSUPPORTED','设备未声明参数控制与预设持久化能力');
      if(writing)throw fail('BUSY','上一条写琴请求尚未完成');const preset=checkedPreset(value),generation=nativeGeneration,op=token(generation,()=>generation===nativeGeneration);writeToken=op;writing=true;
      const id=requestId();state.lastWrite={status:'pending',requestId:id,persisted:false};notify();
      try{
        const reply=await deadline(()=>provider.storePreset({requestId:id,deviceId:nativeHandshake.deviceId,preset,signal:op.controller.signal}),op);guard(op);
        if(!nativeHandshake||!connectionConfirmed(nativeHandshake))throw fail('NOT_CONNECTED','写琴期间真实设备已断开');
        if(!plain(reply)||reply.requestId!==id||reply.ok!==true||reply.persisted!==true||reply.deviceId!==nativeHandshake.deviceId||reply.demo===true)throw fail('INVALID_ACK','设备没有返回匹配的持久化确认');
        state.lastWrite={status:'confirmed',requestId:id,persisted:true,deviceId:reply.deviceId};notify();return clone(state.lastWrite);
      }catch(error){if(generation===nativeGeneration&&!disposed){state.lastWrite={status:'failed',requestId:id,persisted:false,error:safeError(error)};notify();}throw error;
      }finally{if(writeToken===op){writeToken=null;writing=false;}}
    }
    function disconnect(){
      resetBle();closeMidi();closeNative();
      if(provider?.disconnect)try{Promise.resolve(provider.disconnect()).catch(()=>{});}catch{}
      state.ble={...state.ble,status:'disconnected',connected:false,error:null};state.midi={status:'idle',ports:[],error:null};
      state.native={...state.native,status:provider?'disconnected':'unavailable',connected:false,deviceId:null,capabilities:null,error:null};
      if(state.lastWrite?.status==='pending')state.lastWrite={...state.lastWrite,status:'cancelled',persisted:false};notify();
    }
    function subscribeState(callback){live();if(typeof callback!=='function')throw fail('INVALID_VALUE','状态回调必须是函数');observers.add(callback);return()=>observers.delete(callback);}
    function onMidiPacket(callback){live();if(typeof callback!=='function')throw fail('INVALID_VALUE','MIDI 回调必须是函数');packets.add(callback);return()=>packets.delete(callback);}
    function dispose(){if(disposed)return;disconnect();disposed=true;observers.clear();packets.clear();}
    return {detectCapabilities:()=>detectCapabilities(env),status,subscribeState,onMidiPacket,connectBleMidi,listMIDIPorts,subscribeMidiInput,connectNative,storePreset,disconnect,cancel:disconnect,dispose};
  }
  return {BLE_MIDI_SERVICE,BLE_MIDI_CHARACTERISTIC,DeviceBridgeError,detectCapabilities,createDeviceBridge,decodeBleMidiPacket};
});
