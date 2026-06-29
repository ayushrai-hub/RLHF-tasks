'use strict';

const { execFileSync } = require('child_process');

const DB = '/app/workbook/data/workbook.sqlite';

function query(sql) {
  const out = execFileSync('sqlite3', ['-separator', '|', DB, sql], {
    encoding: 'utf8',
  });
  return out.trim();
}

function queryRows(sql) {
  const raw = query(sql);
  if (!raw) {
    return [];
  }
  return raw.split('\n').map((line) => line.split('|'));
}

function round6(value) {
  return Number(Number(value).toFixed(6));
}

module.exports = { query, queryRows, round6, DB };
