"""Deterministic product/changelog record generators plus binary feed writer.

Shared by the build-time fixture stage and the per-run verifier (Pattern H): a
seed shifts every value so held-out runs cannot be hardcoded; the nonce is random.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import codec  # noqa: E402

NAMES = ['Widget', 'Gadget', 'Sprocket', 'Cog', 'Gear',
         'Bolt', 'Nut', 'Bracket', 'Flange', 'Hinge']


def gen_products(n, seed=0):
    recs = []
    for i in range(1, n + 1):
        sku = 'SKU-%07d' % i
        name = NAMES[(i + seed) % len(NAMES)] + '-' + str(i)
        qty = ((i + seed) % 50) + 1
        price_ct = ((i * 13 + seed * 7) % 9999)
        recs.append({'id': i, 'sku': sku, 'name': name, 'qty': qty, 'price_ct': price_ct})
    return recs


def _rng(seed):
    state = (seed * 2654435761 + 12345) & 0xFFFFFFFF

    def nxt():
        nonlocal state
        state = (state * 1103515245 + 12345) & 0xFFFFFFFF
        return state / 0x100000000
    return nxt


def gen_changelog(nids, seed=0):
    rnd = _rng(seed + 1)

    def ri(m):
        return int(rnd() * m)

    recs = []
    for cid in range(1, nids + 1):
        ver = 0
        alive = False
        nchg = 1 + ri(7)
        for _ in range(nchg):
            ver += 1
            if alive and rnd() < 0.3:
                recs.append({'id': cid, 'version': ver, 'op': 'del'})
                alive = False
            else:
                full = not alive
                sku = ('SKU-%d-%d' % (cid, ver)) if (full or rnd() < 0.5) else None
                name = ('Item %d v%d' % (cid, ver)) if (full or rnd() < 0.5) else None
                qty = (1 + ri(99)) if (full or rnd() < 0.5) else None
                price_ct = (1 + ri(9999)) if (full or rnd() < 0.5) else None
                recs.append({'id': cid, 'version': ver, 'op': 'put',
                             'sku': sku, 'name': name, 'qty': qty, 'price_ct': price_ct})
                alive = True
    for i in range(len(recs) - 1, 0, -1):
        j = ri(i + 1)
        recs[i], recs[j] = recs[j], recs[i]
    return recs


def write_feed(path, records, version, nonce=None):
    if nonce is None:
        nonce = os.urandom(8)
    blob = codec.encode(records, version, nonce)
    with open(path, 'wb') as f:
        f.write(blob)
    return len(blob)


if __name__ == '__main__':
    import pathlib
    data = sys.argv[1] if len(sys.argv) > 1 else '/app/data'
    pathlib.Path(data).mkdir(parents=True, exist_ok=True)
    write_feed(f'{data}/sample.bin', gen_products(10), 1)
    write_feed(f'{data}/catalog.bin', gen_products(200000), 1)
    write_feed(f'{data}/feed-full.bin', gen_products(200000), 2)
    write_feed(f'{data}/feed-snapshot.bin', gen_products(200000), 3)
    write_feed(f'{data}/changelog.bin', gen_changelog(5000), 4)
    print('wrote dev fixtures to', data)
