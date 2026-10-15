/* Local preview/test adapter only. Production uses the native env.DB D1 binding. */
import { DatabaseSync } from 'node:sqlite';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { createHash } from 'node:crypto';

export function createD1(file=':memory:'){
  const sqlite=new DatabaseSync(file,{timeout:5000});sqlite.exec('PRAGMA foreign_keys=ON');
  function prepared(sql,values=[]){
    function execute(){
      const statement=sqlite.prepare(sql),results=statement.all(...values);
      const write=!/^\s*(?:SELECT|PRAGMA|EXPLAIN)\b/i.test(sql),changes=write?Number(sqlite.prepare('SELECT changes() AS n').get().n):0;
      return {success:true,results:results.map(row=>({...row})),meta:{changes,last_row_id:Number(sqlite.prepare('SELECT last_insert_rowid() AS n').get().n)}};
    }
    return {sql,values,execute,bind(...input){return prepared(sql,input.map(value=>typeof value==='boolean'?Number(value):value));},async all(){return execute();},async first(column){const row=execute().results[0]||null;return column===undefined?row:row?.[column]??null;},async run(){return execute();}};
  }
  return {
    sqlite,prepare:prepared,
    async batch(statements){
      sqlite.exec('BEGIN IMMEDIATE');
      try{const results=statements.map(statement=>statement.execute());sqlite.exec('COMMIT');return results;}
      catch(error){sqlite.exec('ROLLBACK');throw error;}
    },
    exec(sql){sqlite.exec(sql);},close(){sqlite.close();},
  };
}

export function applyMigrations(db,dir){
  const journal=JSON.parse(readFileSync(join(dir,'meta','_journal.json'),'utf8'));
  if(!Array.isArray(journal.entries))throw Error('Drizzle migration journal is invalid');
  db.sqlite.exec('CREATE TABLE IF NOT EXISTS __local_d1_migrations (tag TEXT PRIMARY KEY, hash TEXT NOT NULL, applied_at TEXT NOT NULL)');
  const applied=[];let last=-1;
  for(const entry of journal.entries){
    if(!Number.isInteger(entry.idx)||entry.idx<=last||typeof entry.tag!=='string'||!/^[A-Za-z0-9_-]+$/.test(entry.tag))throw Error('Drizzle migration order is invalid');last=entry.idx;
    const sql=readFileSync(join(dir,entry.tag+'.sql'),'utf8'),hash=createHash('sha256').update(sql).digest('hex');
    const existing=db.sqlite.prepare('SELECT hash FROM __local_d1_migrations WHERE tag=?').get(entry.tag);
    if(existing){if(existing.hash!==hash)throw Error('Applied migration changed: '+entry.tag);continue;}
    db.sqlite.exec('BEGIN IMMEDIATE');
    try{db.sqlite.exec(sql);db.sqlite.prepare('INSERT INTO __local_d1_migrations (tag,hash,applied_at) VALUES (?,?,?)').run(entry.tag,hash,new Date().toISOString());db.sqlite.exec('COMMIT');applied.push(entry.tag);}
    catch(error){db.sqlite.exec('ROLLBACK');throw error;}
  }
  return applied;
}
