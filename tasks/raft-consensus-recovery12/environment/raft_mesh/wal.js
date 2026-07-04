export const MAX_FRAME_SIZE = 65536;

export function readFrames(buffer, { littleEndian = true } = {}) {
  const frames = [];
  let offset = 0;
  let line = 1;
  while (offset + 4 <= buffer.length) {
    const len = littleEndian
      ? buffer.readUInt32LE(offset)
      : buffer.readUInt32BE(offset);
    offset += 4;
    if (len === 0 || len > MAX_FRAME_SIZE) {
      return { ok: false, code: 'wal_frame_oversize', message: `frame size ${len}`, line };
    }
    if (offset + len > buffer.length) {
      return { ok: false, code: 'bad_binary_frame', message: 'truncated frame', line };
    }
    const body = buffer.subarray(offset, offset + len).toString('utf8');
    offset += len;
    let parsed;
    try {
      parsed = JSON.parse(body);
    } catch {
      return { ok: false, code: 'bad_binary_frame', message: 'invalid json frame', line };
    }
    frames.push(parsed);
    line += 1;
  }
  if (offset !== buffer.length) {
    return { ok: false, code: 'bad_binary_frame', message: 'trailing bytes', line };
  }
  return { ok: true, frames };
}

export function validateFrameOrder(frames) {
  let prevTick = -1;
  for (let i = 0; i < frames.length; i += 1) {
    const tick = Number(frames[i].tick ?? -1);
    if (tick < prevTick) {
      return { ok: false, code: 'wal_order_violation', message: 'frame tick regression', line: i + 1 };
    }
    prevTick = tick;
  }
  return { ok: true };
}
