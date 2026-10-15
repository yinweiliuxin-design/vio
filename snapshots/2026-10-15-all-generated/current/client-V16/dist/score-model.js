'use strict';
/* Pure score timing and reference scoring. No browser, device or network calls. */
(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  if(root)root.SVScoreModel=api;
})(typeof globalThis==='object'?globalThis:this,function(){
  const PPQ=960;
  const NAMES=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
  const STEPS={C:0,D:1,E:2,F:3,G:4,A:5,B:6};
  const CHROMATIC={C:0,D:2,E:4,F:5,G:7,A:9,B:11};
  function pitchParts(pitch){
    if(pitch==='R')return null;
    const m=/^([A-G])([#b]?)(-?\d)$/.exec(String(pitch));
    if(!m)throw new Error('Invalid pitch: '+pitch);
    return {letter:m[1],accidental:m[2],octave:Number(m[3])};
  }
  function midi(pitch){const p=pitchParts(pitch);return p?CHROMATIC[p.letter]+(p.accidental==='#'?1:p.accidental==='b'?-1:0)+(p.octave+1)*12:null;}
  function frequency(pitch,a4=440,semitone=0){
    const n=midi(pitch);if(n===null)return 0;
    if(!Number.isFinite(a4)||a4<=0||!Number.isFinite(semitone))throw new Error('Invalid tuning');
    return a4*Math.pow(2,(n-69+semitone)/12);
  }
  function transposeName(pitch,semitone=0){const n=midi(pitch);if(n===null)return 'R';const shifted=n+semitone;return NAMES[((shifted%12)+12)%12]+(Math.floor(shifted/12)-1);}
  function createScore(song,options={}){
    const ppq=options.ppq||PPQ,numerator=options.numerator||options.meter||4,denominator=options.denominator||4;
    if(!Number.isInteger(ppq)||ppq<=0||!Number.isInteger(numerator)||numerator<=0||![1,2,4,8,16].includes(denominator))throw new Error('Invalid score timebase');
    const ticksPerBar=ppq*4*numerator/denominator;
    const text=typeof song==='string'?song:song&&song.melody;
    if(typeof text!=='string'||!text.trim())throw new Error('Empty melody');
    let cursor=0;
    const events=text.trim().split(/\s+/).map((token,sourceIndex)=>{
      const parts=token.split(':');if(parts.length!==2)throw new Error('Invalid melody token: '+token);
      const pitch=parts[0],beats=Number(parts[1]);pitchParts(pitch);
      const durationTicks=Math.round(beats*ppq);
      if(!Number.isFinite(beats)||beats<=0||durationTicks<=0)throw new Error('Invalid note duration: '+token);
      const startTick=cursor;cursor+=durationTicks;
      return {id:String((song&&song.id)||'score')+':'+sourceIndex,sourceIndex,pitch,beats,durationTicks,startTick,endTick:cursor,originalStartTick:startTick,originalEndTick:cursor,bar:Math.floor(startTick/ticksPerBar)+1};
    });
    return {ppq,timeSignature:{numerator,denominator},ticksPerBar,events,totalTicks:cursor};
  }
  function selectTicks(score,startTick=0,endTick=score.totalTicks){
    const start=Math.min(score.totalTicks,Math.max(0,Number(startTick)||0));
    const end=Math.min(score.totalTicks,Math.max(start,Number.isFinite(endTick)?endTick:score.totalTicks));
    const events=score.events.filter(n=>n.endTick>start&&n.startTick<end).map(n=>{
      const a=Math.max(n.startTick,start),b=Math.min(n.endTick,end);
      return {...n,startTick:a,endTick:b,durationTicks:b-a,beats:(b-a)/score.ppq,bar:Math.floor(a/score.ticksPerBar)+1,clippedStart:a>n.originalStartTick,clippedEnd:b<n.originalEndTick};
    });
    return {score,events,startTick:start,endTick:end};
  }
  function selectBars(score,startBar=1,endBar=0){
    const start=Math.max(1,Math.floor(Number(startBar)||1));
    const end=Math.floor(Number(endBar)||0);
    return selectTicks(score,(start-1)*score.ticksPerBar,end>0?end*score.ticksPerBar:score.totalTicks);
  }
  function plan(range,bpm=80,a4=440,semitone=0){
    if(!Number.isFinite(bpm)||bpm<=0)throw new Error('Invalid BPM');
    const secondsPerTick=60/(bpm*range.score.ppq);
    return range.events.map(n=>({...n,i:n.sourceIndex,freq:frequency(n.pitch,a4,semitone),start:(n.startTick-range.startTick)*secondsPerTick,end:(n.endTick-range.startTick)*secondsPerTick}));
  }
  function staffPosition(pitch,topY=16,gap=5){
    const p=pitchParts(pitch);if(!p)return null;
    const step=p.octave*7+STEPS[p.letter];
    const y=topY+8*gap-(step-30)*gap; // E4 (step 30) is the bottom treble line.
    const ledgerYs=[];
    if(step<=28)for(let st=28;st>=step;st-=2)ledgerYs.push(topY+8*gap-(st-30)*gap);
    if(step>=40)for(let st=40;st<=step;st+=2)ledgerYs.push(topY+8*gap-(st-30)*gap);
    return {step,y,ledgerYs,accidental:p.accidental};
  }
  function createCoverage(planItems,options={}){
    const eligible=planItems.map(n=>n.pitch!=='R'&&Number.isFinite(n.freq)&&n.freq>=80&&n.freq<=3000);
    const activeDuration=planItems.reduce((s,n,i)=>s+(eligible[i]?n.end-n.start:0),0);
    return {plan:planItems,eligible,covered:planItems.map(()=>0),valid:planItems.map(()=>0),activeDuration,lastEnd:0,centsTolerance:options.centsTolerance??35,minConfidence:options.minConfidence??0.85,maxSampleGap:options.maxSampleGap??0.12};
  }
  function observeCoverage(state,sample,from,to){
    if(!Number.isFinite(from)||!Number.isFinite(to)||to<=from)return;
    const a=Math.max(0,from,state.lastEnd,to-state.maxSampleGap),b=Math.max(0,to);
    state.lastEnd=Math.max(state.lastEnd,b);if(b<=a)return;
    const reliable=sample&&sample.valid===true&&Number.isFinite(sample.frequency)&&sample.frequency>=80&&sample.frequency<=3000&&Number.isFinite(sample.confidence)&&sample.confidence>=state.minConfidence;
    if(!reliable)return;
    state.plan.forEach((n,i)=>{
      if(!state.eligible[i])return;
      const overlap=Math.max(0,Math.min(b,n.end)-Math.max(a,n.start));if(!overlap)return;
      state.valid[i]=Math.min(n.end-n.start,state.valid[i]+overlap);
      if(Math.abs(1200*Math.log2(sample.frequency/n.freq))<=state.centsTolerance)state.covered[i]=Math.min(n.end-n.start,state.covered[i]+overlap);
    });
  }
  function coverageResult(state){
    const covered=state.covered.reduce((a,b)=>a+b,0),valid=state.valid.reduce((a,b)=>a+b,0);
    const pitchCoverage=state.activeDuration?Math.min(1,covered/state.activeDuration):null;
    const validInputFraction=state.activeDuration?Math.min(1,valid/state.activeDuration):null;
    return {score:pitchCoverage===null?null:Math.round(pitchCoverage*100),pitchCoverage,validInputFraction,coveredSeconds:covered,activeSeconds:state.activeDuration,noteCoverage:state.plan.map((n,i)=>!state.eligible[i]?null:state.covered[i]/(n.end-n.start))};
  }
  return {PPQ,pitchParts,midi,frequency,transposeName,createScore,selectTicks,selectBars,plan,staffPosition,createCoverage,observeCoverage,coverageResult};
});
