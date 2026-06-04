CREATE TABLE ledger(seq INTEGER PRIMARY KEY, entry_hash TEXT);
CREATE TABLE modules(id TEXT PRIMARY KEY, version TEXT);
CREATE TABLE release_state(id TEXT PRIMARY KEY, status TEXT);
