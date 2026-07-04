"use strict";

function ts() {
  return new Date().toISOString();
}

function info(msg, fields) {
  if (fields !== undefined) {
    process.stderr.write(`${ts()} [info] ${msg} ${JSON.stringify(fields)}\n`);
  } else {
    process.stderr.write(`${ts()} [info] ${msg}\n`);
  }
}

function warn(msg, fields) {
  if (fields !== undefined) {
    process.stderr.write(`${ts()} [warn] ${msg} ${JSON.stringify(fields)}\n`);
  } else {
    process.stderr.write(`${ts()} [warn] ${msg}\n`);
  }
}

function error(msg, fields) {
  if (fields !== undefined) {
    process.stderr.write(`${ts()} [error] ${msg} ${JSON.stringify(fields)}\n`);
  } else {
    process.stderr.write(`${ts()} [error] ${msg}\n`);
  }
}

module.exports = { info, warn, error };
