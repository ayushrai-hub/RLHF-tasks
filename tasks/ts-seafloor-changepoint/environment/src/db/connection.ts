import Database from 'better-sqlite3';

let _db: Database.Database | null = null;

export function openDatabase(dbPath: string): Database.Database {
  if (_db) {
    _db.close();
  }
  _db = new Database(dbPath, { readonly: true });
  return _db;
}

export function closeDatabase(): void {
  if (_db) {
    _db.close();
    _db = null;
  }
}
