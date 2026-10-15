(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.SVMediaStore = api.createMediaStore({environment: root});
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const SCHEMA_VERSION = 1;
  const STORE = 'media';
  const KINDS = ['recording', 'video', 'loop', 'backing'];
  const LIMITS = [
    '仅当前浏览器与同源地址保存；协议、主机或端口改变后不会读取到原录音。',
    '容量由浏览器配额决定，隐私模式、清理网站数据或浏览器回收可能删除录音。重要录音请另行下载。',
    '这是本机浏览器存储，不是云备份；未停止且未完成的录音不会恢复。'
  ];

  class MediaStorageError extends Error {
    constructor(code, message, cause) {
      super(message);
      this.name = 'MediaStorageError';
      this.code = code;
      this.causeName = cause && cause.name || null;
      this.committed = false;
      this.persisted = false;
    }
  }

  function storageError(code, cause) {
    const name = cause && cause.name;
    if (name === 'QuotaExceededError') return new MediaStorageError('QUOTA_EXCEEDED',
      code === 'DELETE_FAILED' || code === 'CLEAR_FAILED' ? '浏览器存储提交失败；删除未确认，请重试。' : '浏览器存储空间不足；录音仅保留在本页内存，请立即下载。', cause);
    if (name === 'SecurityError' || name === 'NotAllowedError') return new MediaStorageError('STORAGE_DENIED', '浏览器未允许本机存储；录音仅保留在本页内存，刷新后会丢失。', cause);
    const messages = {
      UNAVAILABLE: '当前浏览器不支持 IndexedDB；录音仅保留在本页内存，刷新后会丢失。',
      OPEN_FAILED: '无法打开本机录音库；本页录音可下载，但未确认持久保存。',
      BLOCKED: '录音库被其他页面占用，请关闭旧页面后刷新；本页录音尚未持久保存。',
      WRITE_FAILED: '录音未提交到本机录音库；仅保留在本页内存，请下载备份。',
      READ_FAILED: '无法读取本机录音库；当前列表可能不完整，请保留本页并重试。',
      DELETE_FAILED: '删除未提交；本机录音仍需确认删除，请重试。',
      CLEAR_FAILED: '清空未提交；本机录音仍需确认删除，请重试。',
      VERSION_CHANGED: '录音库版本已被其他页面更新；请刷新后再保存。',
      CLOSED: '录音库已关闭；本页新增录音尚未持久保存。'
    };
    return new MediaStorageError(code, messages[code] || messages.WRITE_FAILED, cause);
  }

  function errorInfo(error) {
    return error ? {code: error.code, message: error.message, name: error.causeName || error.name} : null;
  }

  function createMediaStore(options) {
    options = options || {};
    const env = options.environment || (typeof globalThis !== 'undefined' ? globalThis : {});
    const BlobType = options.Blob || env.Blob;
    const now = options.now || (() => new Date().toISOString());
    const dbName = options.dbName || 'smartvio-v11-media';
    const memory = new Map();
    let db = null, openPromise = null, lastError = null, writeQueue = Promise.resolve(), closed = false;
    const isBlob = value => typeof BlobType === 'function' && value instanceof BlobType;
    const remember = error => { lastError = error; return error; };

    function status() {
      const warning = lastError || (memory.size ? new MediaStorageError('VOLATILE_RECORDS', '部分录音仅保留在本页内存；刷新后会丢失，请下载备份。') : null);
      return {
        schemaVersion: SCHEMA_VERSION, database: dbName,
        mode: db ? warning ? 'degraded' : 'indexeddb' : 'memory',
        persistentAvailable: !!db, error: errorInfo(warning),
        memoryRecords: memory.size,
        memoryBytes: [...memory.values()].reduce((sum, row) => sum + row.blob.size, 0),
        limitations: LIMITS.slice()
      };
    }

    async function ensureDB() {
      if (closed) { remember(storageError('CLOSED')); return null; }
      if (!openPromise) {
        openPromise = new Promise(resolve => {
          let factory;
          try { factory = Object.prototype.hasOwnProperty.call(options, 'indexedDB') ? options.indexedDB : env.indexedDB; }
          catch (error) { remember(storageError('OPEN_FAILED', error)); resolve(null); return; }
          if (!factory || typeof factory.open !== 'function') { remember(storageError('UNAVAILABLE')); resolve(null); return; }
          let request, settled = false, timer;
          const finish = (connection, error) => {
            if (settled) { if (connection) connection.close(); return; }
            settled = true;
            clearTimeout(timer);
            if (error) remember(error);
            if (connection && !closed) { db = connection; lastError = null; }
            else if (connection) connection.close();
            resolve(db);
          };
          try {
            request = factory.open(dbName, SCHEMA_VERSION);
            request.onupgradeneeded = () => {
              const connection = request.result;
              const store = connection.objectStoreNames.contains(STORE)
                ? request.transaction.objectStore(STORE)
                : connection.createObjectStore(STORE, {keyPath: 'id'});
              if (!store.indexNames.contains('byKind')) store.createIndex('byKind', 'kind', {unique: false});
              if (!store.indexNames.contains('byLoopSlot')) store.createIndex('byLoopSlot', ['kind', 'trackIndex'], {unique: true});
            };
            request.onerror = () => finish(null, storageError('OPEN_FAILED', request.error));
            request.onblocked = () => finish(null, storageError('BLOCKED'));
            request.onsuccess = () => {
              const connection = request.result;
              connection.onversionchange = () => { connection.close(); if (db === connection) db = null; remember(storageError('VERSION_CHANGED')); };
              connection.onclose = () => { if (db === connection) { db = null; remember(storageError('CLOSED')); } };
              finish(connection);
            };
            timer = setTimeout(() => finish(null, storageError('BLOCKED')), options.openTimeoutMs || 2500);
          } catch (error) { finish(null, storageError('OPEN_FAILED', error)); }
        });
      }
      await openPromise;
      return db;
    }

    // Only transaction.complete confirms a commit; request.success is insufficient.
    // https://www.w3.org/TR/IndexedDB-3/#transaction-finished
    function transaction(connection, mode, operation) {
      return new Promise((resolve, reject) => {
        let tx, result, failure;
        try {
          if (mode === 'readwrite') {
            try { tx = connection.transaction(STORE, mode, {durability: 'strict'}); }
            catch (error) { if (error.name !== 'TypeError') throw error; tx = connection.transaction(STORE, mode); }
          } else tx = connection.transaction(STORE, mode);
          tx.oncomplete = () => resolve(result);
          tx.onabort = () => reject(tx.error || failure || new Error('Transaction aborted'));
          tx.onerror = () => { failure = tx.error || failure; };
          const watch = (request, success) => {
            request.onerror = () => { failure = request.error || failure; };
            request.onsuccess = () => {
              try { if (success) success(request.result); }
              catch (error) { failure = error; tx.abort(); }
            };
            return request;
          };
          operation(tx.objectStore(STORE), watch, value => { result = value; });
        } catch (error) {
          if (tx) { failure = error; try { tx.abort(); } catch (_) { reject(error); } }
          else reject(error);
        }
      });
    }

    function validateKind(kind) {
      if (kind !== undefined && !KINDS.includes(kind)) throw new MediaStorageError('INVALID_RECORD', '录音类别无效。');
    }

    function normalize(input) {
      validateKind(input && input.kind);
      if (!input || !KINDS.includes(input.kind) || typeof input.id !== 'string' || !input.id || input.id.length > 160 ||
          input.completed !== true || !isBlob(input.blob) || !input.blob.size || typeof input.name !== 'string' || input.name.length > 200) {
        throw new MediaStorageError('INVALID_RECORD', '仅能保存已停止且完成的非空录音；需要有效编号、名称、Blob和completed:true。');
      }
      if (input.kind === 'loop' && (!Number.isInteger(input.trackIndex) || input.trackIndex < 0 || input.trackIndex > 3)) {
        throw new MediaStorageError('INVALID_RECORD', 'Looper轨号必须为0至3。');
      }
      const row = {
        schemaVersion: SCHEMA_VERSION, id: input.id, kind: input.kind,
        completed: true, name: input.name, blob: input.blob,
        type: input.blob.type || (typeof input.type === 'string' ? input.type.slice(0, 180) : 'application/octet-stream'),
        createdAt: typeof input.createdAt === 'string' && Number.isFinite(Date.parse(input.createdAt)) ? input.createdAt : now(), updatedAt: now()
      };
      if (input.kind === 'loop') row.trackIndex = input.trackIndex;
      for (const key of ['duration', 'bpm', 'meter', 'loopBars', 'volume', 'sampleRate', 'channels']) {
        if (input[key] !== undefined) {
          if (!Number.isFinite(input[key]) || input[key] < 0) throw new MediaStorageError('INVALID_RECORD', '录音元数据中的数值无效。');
          row[key] = input[key];
        }
      }
      if (typeof input.muted === 'boolean') row.muted = input.muted;
      if (typeof input.source === 'string') row.source = input.source.slice(0, 80);
      return row;
    }

    function keepMemory(row) {
      if (row.kind === 'loop') for (const [id, old] of memory) if (old.kind === 'loop' && old.trackIndex === row.trackIndex) memory.delete(id);
      memory.set(row.id, row);
    }

    function serialWrite(operation) {
      const result = writeQueue.then(operation);
      writeQueue = result.catch(() => {});
      return result;
    }

    function restorable(row) {
      return row && row.schemaVersion === SCHEMA_VERSION && row.completed === true && KINDS.includes(row.kind) &&
        typeof row.id === 'string' && isBlob(row.blob) && row.blob.size > 0 &&
        (row.kind !== 'loop' || Number.isInteger(row.trackIndex) && row.trackIndex >= 0 && row.trackIndex < 4);
    }

    async function list(kind, listOptions) {
      validateKind(kind);
      await writeQueue;
      const connection = await ensureDB();
      let stored = [];
      if (connection) {
        try {
          stored = await transaction(connection, 'readonly', (store, watch, set) => {
            watch(kind ? store.index('byKind').getAll(kind) : store.getAll(), set);
          });
          lastError = null;
        } catch (error) { remember(storageError('READ_FAILED', error)); }
      }
      const merged = new Map(stored.filter(restorable).map(row => [row.id, {...row, persisted: true}]));
      for (const row of memory.values()) if (restorable(row) && (!kind || row.kind === kind)) merged.set(row.id, {...row, persisted: false});
      const rows = [...merged.values()].sort((a, b) => String(b.updatedAt).localeCompare(String(a.updatedAt)) || Number(a.persisted) - Number(b.persisted));
      // Destructive UI actions need all IDs, including a durable slot hidden by
      // a newer volatile recording after a failed replacement transaction.
      if (listOptions && listOptions.includeShadowed === true) return rows;
      const occupied = new Set();
      return rows.filter(row => {
        if (row.kind !== 'loop') return true;
        if (occupied.has(row.trackIndex)) return false;
        occupied.add(row.trackIndex); return true;
      });
    }

    async function put(input) {
      const row = normalize(input);
      return serialWrite(async () => {
        const connection = await ensureDB();
        if (connection) {
          try {
            await transaction(connection, 'readwrite', (store, watch) => {
              const save = () => watch(store.put(row));
              if (row.kind === 'loop') watch(store.index('byLoopSlot').getKey(['loop', row.trackIndex]), oldId => {
                if (oldId !== undefined && oldId !== row.id) watch(store.delete(oldId));
                save();
              });
              else save();
            });
            memory.delete(row.id);
            if (row.kind === 'loop') for (const [id, old] of memory) if (old.kind === 'loop' && old.trackIndex === row.trackIndex) memory.delete(id);
            lastError = null;
            return {record: {...row, persisted: true}, persisted: true, committed: true, mode: 'indexeddb', error: null};
          } catch (error) { remember(storageError('WRITE_FAILED', error)); }
        }
        keepMemory(row);
        return {record: {...row, persisted: false}, persisted: false, committed: false, mode: 'memory', error: errorInfo(lastError)};
      });
    }

    function deleteRecord(id) {
      if (typeof id !== 'string' || !id || id.length > 160) return Promise.reject(new MediaStorageError('INVALID_RECORD', '录音编号无效。'));
      return serialWrite(async () => {
        const connection = await ensureDB();
        if (connection) {
          try { await transaction(connection, 'readwrite', (store, watch) => watch(store.delete(id))); }
          catch (error) { throw remember(storageError('DELETE_FAILED', error)); }
          memory.delete(id); lastError = null;
          return {id, deleted: true, committed: true, persisted: true, mode: 'indexeddb', error: null};
        }
        memory.delete(id);
        return {id, deleted: true, committed: false, persisted: false, mode: 'memory', error: errorInfo(lastError)};
      });
    }

    function clear() {
      return serialWrite(async () => {
        const connection = await ensureDB();
        if (connection) {
          try { await transaction(connection, 'readwrite', (store, watch) => watch(store.clear())); }
          catch (error) { throw remember(storageError('CLEAR_FAILED', error)); }
          memory.clear(); lastError = null;
          return {cleared: true, committed: true, persisted: true, mode: 'indexeddb', error: null};
        }
        memory.clear();
        return {cleared: true, committed: false, persisted: false, mode: 'memory', error: errorInfo(lastError)};
      });
    }

    async function estimate() {
      const result = {usage: null, quota: null, persistentPermission: null, ...status()};
      try {
        const storage = options.storage || env.navigator && env.navigator.storage;
        if (storage && typeof storage.estimate === 'function') {
          const size = await storage.estimate();
          result.usage = Number.isFinite(size.usage) ? size.usage : null;
          result.quota = Number.isFinite(size.quota) ? size.quota : null;
        }
        if (storage && typeof storage.persisted === 'function') result.persistentPermission = await storage.persisted();
      } catch (error) { result.estimateError = {name: error.name, message: '无法取得浏览器容量估算；可用容量未知。'}; }
      return result;
    }

    function close() { closed = true; if (db) db.close(); db = null; }
    return {list, put, delete: deleteRecord, clear, status, estimate, close};
  }
  return {createMediaStore, MediaStorageError, SCHEMA_VERSION};
});
