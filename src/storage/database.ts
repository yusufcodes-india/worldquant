/**
 * IndexedDB wrapper for the extension.
 * Provides a simple typed API for storing research runs and imported Alpha JSON data.
 */

interface DBRecord<T> {
  id: string; // primary key
  data: T;
}

/**
 * Open (or create) the IndexedDB database.
 * Returns a promise that resolves to the IDBDatabase instance.
 */
export function openDatabase(name: string = 'brain-alpha-db', version: number = 1): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(name, version);
    request.onupgradeneeded = () => {
      const db = request.result;
      // Store research runs
      if (!db.objectStoreNames.contains('researchRuns')) {
        db.createObjectStore('researchRuns', { keyPath: 'id' });
      }
      // Store imported Alpha JSON files
      if (!db.objectStoreNames.contains('alphaImports')) {
        db.createObjectStore('alphaImports', { keyPath: 'id' });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

/** Generic CRUD helpers */
export async function addRecord<T>(storeName: string, record: DBRecord<T>): Promise<void> {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readwrite');
    const store = tx.objectStore(storeName);
    const req = store.add(record);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

export async function getAllRecords<T>(storeName: string): Promise<DBRecord<T>[]> {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readonly');
    const store = tx.objectStore(storeName);
    const req = store.getAll();
    req.onsuccess = () => resolve(req.result as DBRecord<T>[]);
    req.onerror = () => reject(req.error);
  });
}

export async function getRecord<T>(storeName: string, id: string): Promise<DBRecord<T> | undefined> {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readonly');
    const store = tx.objectStore(storeName);
    const req = store.get(id);
    req.onsuccess = () => resolve(req.result as DBRecord<T>);
    req.onerror = () => reject(req.error);
  });
}

export async function updateRecord<T>(storeName: string, record: DBRecord<T>): Promise<void> {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readwrite');
    const store = tx.objectStore(storeName);
    const req = store.put(record);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

export async function deleteRecord(storeName: string, id: string): Promise<void> {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readwrite');
    const store = tx.objectStore(storeName);
    const req = store.delete(id);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}
