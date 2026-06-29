'use strict';

const fs = require('fs');
const pgp = require('pg-promise')();
const batcher = require('./lib/stream-batcher');

const db = pgp({
    host: '127.0.0.1',
    port: 5433,
    database: 'app',
    user: 'app',
    password: 'apppass',
});

const cs = new pgp.helpers.ColumnSet(
    ['id', 'sku', 'name', 'qty', 'price'],
    { table: 'products' }
);

async function* decodeCatalog(file) {
    throw new Error('decodeCatalog not implemented');
    // eslint-disable-next-line no-unreachable
    yield;
}

async function* decodeChangelog(file) {
    throw new Error('decodeChangelog not implemented');
    // eslint-disable-next-line no-unreachable
    yield;
}

async function reconcileChangelog() {
    throw new Error('changelog reconciliation not implemented');
}

async function main() {
    const args = process.argv.slice(2);
    const dryRun = args.includes('--dry-run');
    const file = args.find(a => !a.startsWith('--'));
    if (!file) {
        console.error('usage: import.js [--dry-run] [--resume-from auto|id:<n>] <feed>');
        process.exit(1);
    }

    const sink = dryRun
        ? async () => {}
        : async batch => { await db.none(pgp.helpers.insert(batch, cs)); };
    const total = await batcher.consume(decodeCatalog(file), sink);

    console.log(`processed ${total} rows`);
    pgp.end();
}

const entry = process.argv.includes('--changelog') ? reconcileChangelog : main;
entry().catch(err => {
    console.error('import failed:', err.message);
    process.exit(1);
});
