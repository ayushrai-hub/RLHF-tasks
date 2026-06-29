'use strict';

const fs = require('fs');
const path = require('path');

const KERNELS = '/app/workbook/kernels';

function parseModule(content) {
  const mod = { requires: [], replace: [] };
  let section = null;
  for (const raw of content.split('\n')) {
    const line = raw.trim();
    if (!line || line.startsWith('//')) {
      continue;
    }
    if (line.startsWith('module ')) {
      mod.path = line.slice('module '.length).trim();
      continue;
    }
    if (line === 'require (') {
      section = 'require';
      continue;
    }
    if (line === 'replace (') {
      section = 'replace';
      continue;
    }
    if (line === ')') {
      section = null;
      continue;
    }
    if (line.startsWith('require ') && !line.startsWith('require (')) {
      const parts = line.slice('require '.length).trim().split(/\s+/);
      mod.requires.push({ path: parts[0], version: parts[1] || '' });
      continue;
    }
    if (line.includes('=>') && line.startsWith('replace ')) {
      const arrow = line.slice('replace '.length).split('=>');
      if (arrow.length === 2) {
        const left = arrow[0].trim().split(/\s+/);
        const right = arrow[1].trim().split(/\s+/);
        mod.replace.push({
          oldPath: left[0],
          oldVersion: left[1] || '',
          newPath: right[0],
          newVersion: right[1] || '',
        });
      }
    }
  }
  return mod;
}

function moduleDir(wrapperModule) {
  const name = wrapperModule.split('/').pop();
  return path.join(KERNELS, name);
}

function resolveKernelRevision(wrapperModule) {
  const dir = moduleDir(wrapperModule);
  const mod = parseModule(fs.readFileSync(path.join(dir, 'go.mod'), 'utf8'));
  const kernelReq = mod.requires.find((row) => row.path === 'example.com/rd-kernel');
  if (!kernelReq) {
    throw new Error(`missing rd-kernel require in ${wrapperModule}`);
  }
  const direct = mod.replace.find((row) => row.oldPath === kernelReq.path);
  if (!direct) {
    return `${wrapperModule}@${kernelReq.version}`;
  }
  return `${direct.newPath}@${direct.newVersion}`;
}

module.exports = { resolveKernelRevision, parseModule };
