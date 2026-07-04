import struct

PAGE_SIZE = 4096
LEAF_CAP = 4
INT_FANOUT = 5
NO_PAGE = 0xFFFFFFFF
LEAF_MIN = 2
INT_MIN_KEYS = 2


class Node:
    __slots__ = ("leaf", "keys", "children", "values", "nxt", "pid")

    def __init__(self, leaf):
        self.leaf = leaf
        self.keys = []
        self.children = []
        self.values = []
        self.nxt = None
        self.pid = 0


class Tree:
    def __init__(self):
        self.root = Node(True)
        self.height = 1


def _leaf_pos(n, key):
    i = 0
    while i < len(n.keys) and n.keys[i] < key:
        i += 1
    return i


def _child_index(n, key):
    i = 0
    while i < len(n.keys) and key >= n.keys[i]:
        i += 1
    return i


def _split_leaf(n):
    right = Node(True)
    s = 3
    right.keys = n.keys[s:]
    right.values = n.values[s:]
    n.keys = n.keys[:s]
    n.values = n.values[:s]
    right.nxt = n.nxt
    n.nxt = right
    return (right.keys[0], right)


def _split_internal(n):
    right = Node(False)
    m = 2
    sep = n.keys[m]
    right.keys = n.keys[m + 1:]
    right.children = n.children[m + 1:]
    n.keys = n.keys[:m]
    n.children = n.children[:m + 1]
    return (sep, right)


def _insert_rec(n, key, value):
    if n.leaf:
        i = _leaf_pos(n, key)
        if i < len(n.keys) and n.keys[i] == key:
            n.values[i] = value
            return None
        n.keys.insert(i, key)
        n.values.insert(i, value)
        if len(n.keys) > LEAF_CAP:
            return _split_leaf(n)
        return None
    ci = _child_index(n, key)
    res = _insert_rec(n.children[ci], key, value)
    if res is None:
        return None
    sep, right = res
    n.keys.insert(ci, sep)
    n.children.insert(ci + 1, right)
    if len(n.keys) > INT_FANOUT - 1:
        return _split_internal(n)
    return None


def insert(t, key, value):
    res = _insert_rec(t.root, key, value)
    if res is not None:
        sep, right = res
        nr = Node(False)
        nr.keys = [sep]
        nr.children = [t.root, right]
        t.root = nr
        t.height += 1


def _fix_child(p, i):
    c = p.children[i]
    if c.leaf:
        under = len(c.keys) < LEAF_MIN
    else:
        under = len(c.keys) < INT_MIN_KEYS
    if not under:
        return
    left = p.children[i - 1] if i > 0 else None
    right = p.children[i + 1] if i + 1 < len(p.children) else None

    if c.leaf:
        if left is not None and len(left.keys) > LEAF_MIN:
            c.keys.insert(0, left.keys.pop())
            c.values.insert(0, left.values.pop())
            p.keys[i - 1] = c.keys[0]
            return
        if right is not None and len(right.keys) > LEAF_MIN:
            c.keys.append(right.keys.pop(0))
            c.values.append(right.values.pop(0))
            p.keys[i] = right.keys[0]
            return
        if left is not None:
            left.keys.extend(c.keys)
            left.values.extend(c.values)
            left.nxt = c.nxt
            del p.keys[i - 1]
            del p.children[i]
            return
        c.keys.extend(right.keys)
        c.values.extend(right.values)
        c.nxt = right.nxt
        del p.keys[i]
        del p.children[i + 1]
        return

    if left is not None and len(left.keys) > INT_MIN_KEYS:
        c.keys.insert(0, p.keys[i - 1])
        c.children.insert(0, left.children.pop())
        p.keys[i - 1] = left.keys.pop()
        return
    if right is not None and len(right.keys) > INT_MIN_KEYS:
        c.keys.append(p.keys[i])
        c.children.append(right.children.pop(0))
        p.keys[i] = right.keys.pop(0)
        return
    if left is not None:
        left.keys.append(p.keys[i - 1])
        left.keys.extend(c.keys)
        left.children.extend(c.children)
        del p.keys[i - 1]
        del p.children[i]
        return
    c.keys.append(p.keys[i])
    c.keys.extend(right.keys)
    c.children.extend(right.children)
    del p.keys[i]
    del p.children[i + 1]


def _delete_rec(n, key):
    if n.leaf:
        i = 0
        while i < len(n.keys) and n.keys[i] < key:
            i += 1
        if i < len(n.keys) and n.keys[i] == key:
            del n.keys[i]
            del n.values[i]
        return
    ci = _child_index(n, key)
    _delete_rec(n.children[ci], key)
    _fix_child(n, ci)


def delete(t, key):
    _delete_rec(t.root, key)
    if not t.root.leaf and len(t.root.keys) == 0:
        t.root = t.root.children[0]
        t.height -= 1


def apply_ops(t, ops):
    for op in ops:
        if op[0] == "I":
            insert(t, op[1], op[2])
        else:
            delete(t, op[1])


def build(ops):
    t = Tree()
    apply_ops(t, ops)
    return t


def parse_ops(text):
    ops = []
    for line in text.split("\n"):
        line = line.rstrip("\r")
        if line.strip() == "":
            continue
        parts = line.split()
        if parts[0] == "I":
            ops.append(("I", int(parts[1]), parts[2]))
        elif parts[0] == "D":
            ops.append(("D", int(parts[1])))
    return ops


def _bfs(t):
    order = []
    if t.root is None:
        return order
    q = [t.root]
    nxt = 1
    while q:
        n = q.pop(0)
        n.pid = nxt
        nxt += 1
        order.append(n)
        if not n.leaf:
            q.extend(n.children)
    return order


def dump(t):
    order = _bfs(t)
    lines = []
    lines.append("height %d" % t.height)
    lines.append("root %d" % (t.root.pid if t.root else 0))
    for n in order:
        if n.leaf:
            nx = str(n.nxt.pid) if n.nxt is not None else "-"
            s = "leaf page %d next %s entries" % (n.pid, nx)
            for i in range(len(n.keys)):
                s += " %d:%s" % (n.keys[i], n.values[i])
            lines.append(s)
        else:
            s = "internal page %d keys" % n.pid
            for k in n.keys:
                s += " %d" % k
            s += " children"
            for c in n.children:
                s += " %d" % c.pid
            lines.append(s)
    return "\n".join(lines) + "\n"


def serialize(t):
    order = _bfs(t)
    page_count = len(order) + 1
    buf = bytearray(page_count * PAGE_SIZE)
    buf[0:4] = b"BPT1"
    struct.pack_into(">I", buf, 4, PAGE_SIZE)
    struct.pack_into(">I", buf, 8, t.root.pid if t.root else 0)
    struct.pack_into(">I", buf, 12, page_count)
    struct.pack_into(">H", buf, 16, LEAF_CAP)
    struct.pack_into(">H", buf, 18, INT_FANOUT)
    struct.pack_into(">H", buf, 20, t.height)
    for n in order:
        base = n.pid * PAGE_SIZE
        struct.pack_into(">I", buf, base + 0, n.pid)
        buf[base + 4] = 1 if n.leaf else 0
        struct.pack_into(">H", buf, base + 5, len(n.keys))
        buf[base + 7] = 0
        off = base + 8
        if n.leaf:
            nx = n.nxt.pid if n.nxt is not None else NO_PAGE
            struct.pack_into(">I", buf, off, nx)
            off += 4
            for i in range(len(n.keys)):
                struct.pack_into(">Q", buf, off, n.keys[i])
                off += 8
                vb = n.values[i].encode("latin-1")
                buf[off] = len(vb)
                off += 1
                buf[off:off + len(vb)] = vb
                off += len(vb)
        else:
            struct.pack_into(">I", buf, off, n.children[0].pid)
            off += 4
            for i in range(len(n.keys)):
                struct.pack_into(">Q", buf, off, n.keys[i])
                off += 8
                struct.pack_into(">I", buf, off, n.children[i + 1].pid)
                off += 4
    return bytes(buf)


def get(t, key):
    n = t.root
    while not n.leaf:
        i = 0
        while i < len(n.keys) and key >= n.keys[i]:
            i += 1
        n = n.children[i]
    for i in range(len(n.keys)):
        if n.keys[i] == key:
            return n.values[i]
    return None


def range_scan(t, lo, hi):
    out = []
    if lo > hi:
        return out
    n = t.root
    while not n.leaf:
        i = 0
        while i < len(n.keys) and lo >= n.keys[i]:
            i += 1
        n = n.children[i]
    done = False
    while n is not None and not done:
        for i in range(len(n.keys)):
            k = n.keys[i]
            if k < lo:
                continue
            if k > hi:
                done = True
                break
            out.append((k, n.values[i]))
        if done:
            break
        n = n.nxt
    return out


def present_keys(ops):
    d = {}
    for op in ops:
        if op[0] == "I":
            d[op[1]] = op[2]
        else:
            d.pop(op[1], None)
    return d
