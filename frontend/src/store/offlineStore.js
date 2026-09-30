import { openDB } from 'idb';

const DB_NAME = 'acuvera-offline-db';
const STORE_NAME = 'triage-drafts';

// Initialize the database
export const initDB = async () => {
    return openDB(DB_NAME, 1, {
        upgrade(db) {
            if (!db.objectStoreNames.contains(STORE_NAME)) {
                db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true });
            }
        },
    });
};

// Save a draft triage request to IndexedDB when offline
export const saveDraft = async (encounterId, triageData) => {
    const db = await initDB();
    const draft = {
        encounterId,
        triageData,
        timestamp: new Date().toISOString()
    };
    return db.add(STORE_NAME, draft);
};

// Retrieve all offline drafts
export const getAllDrafts = async () => {
    const db = await initDB();
    return db.getAll(STORE_NAME);
};

// Delete a draft after it is successfully synced
export const deleteDraft = async (id) => {
    const db = await initDB();
    return db.delete(STORE_NAME, id);
};
