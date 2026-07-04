#!/usr/bin/env node
'use strict';

const fs = require('fs');
const { execFileSync } = require('child_process');
const importMigration = require('../migrations/001_import');
const summaryMigration = require('../migrations/002_summary');
const { writeChecksum } = require('../lib/export-checksum');

const DB = '/app/workbook/data/workbook.sqlite';
const SCHEMA = '/app/workbook/sql/schema.sql';

function resetDb() {
  fs.mkdirSync('/app/workbook/data', { recursive: true });
  if (fs.existsSync(DB)) {
    fs.unlinkSync(DB);
  }
  execFileSync('sqlite3', [DB], { input: fs.readFileSync(SCHEMA, 'utf8'), encoding: 'utf8' });
}

function up() {
  resetDb();
  importMigration.up();
  summaryMigration.up();
  writeChecksum();
}

if (require.main === module) {
  up();
}

module.exports = { up, resetDb };
