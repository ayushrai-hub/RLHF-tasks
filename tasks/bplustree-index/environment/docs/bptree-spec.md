bptree on-disk index format and behaviour specification

This document is the authoritative contract for the `bpt` tool and the on-disk
index it produces. Every byte of every produced index file, and every byte the
tool prints, is fixed by the rules below. Where a number is given it is exact.

1. Scope and vocabulary

The index is a B+tree. Keys are unsigned 64-bit integers. Values are opaque
byte strings of length 1..255. Interior (internal) nodes carry separator keys
and child page ids. Leaf nodes carry key/value entries and a pointer to the next
leaf. The tree stores each present key exactly once, in a leaf.

Two capacity numbers govern the shape of the tree and never change:

  LEAF_CAP     = 4    a leaf holds at most 4 entries
  INT_FANOUT   = 5    an internal node holds at most 5 children, i.e. at most 4
                      separator keys

2. On-disk file layout

The file is a sequence of fixed-size pages. Each page is exactly 4096 bytes.
Page ids are 32-bit and number the pages from 0. Page 0 is the superblock; it is
not a tree node. Real nodes occupy page ids 1 and up. The file length is always
`page_count * 4096`.

All multi-byte integers on disk are big-endian. Every page is zero-padded from
the end of its meaningful content to 4096 bytes.

2.1 Superblock (page 0)

  offset 0   4 bytes   magic, the ASCII bytes "BPT1"
  offset 4   uint32    page_size, always 4096
  offset 8   uint32    root_page_id
  offset 12  uint32    page_count, total pages including the superblock
  offset 16  uint16    leaf_cap, always 4
  offset 18  uint16    int_fanout, always 5
  offset 20  uint16    height, the number of levels in the tree
  (rest zero)

The height of a tree whose root is a leaf is 1. Each additional internal level
adds 1.

2.2 Node header (pages 1..page_count-1)

  offset 0   uint32    page_id, equal to this page's own id
  offset 4   uint8     flags, 0 for an internal node, 1 for a leaf node
  offset 5   uint16    nkeys, the number of keys stored in this node
  offset 7   uint8     zero

For a leaf, nkeys is the number of entries. For an internal node, nkeys is the
number of separator keys, and the number of children is nkeys+1.

2.3 Internal node body (starts at offset 8)

  uint32              child[0]
  then, repeated nkeys times:
    uint64            key[j]
    uint32            child[j+1]

so the layout is child0, key0, child1, key1, child2, ... . The children are
page ids. Every key in the subtree under child[j] is < key[j], and every key in
the subtree under child[j+1] is >= key[j].

2.4 Leaf node body (starts at offset 8)

  uint32              next_leaf, the page id of the next leaf in ascending key
                      order, or 0xFFFFFFFF if this is the last leaf
  then, repeated nkeys times:
    uint64            key[j]
    uint8             vlen[j]
    vlen[j] bytes     value[j]

Entries within a leaf are stored in ascending key order.

3. Canonical page numbering

The page id written into a node and referenced by its parent/next pointers is
its canonical id. Canonical ids are assigned by a breadth-first walk of the
finished tree, independent of any transient ids used while the tree was being
built:

  - The superblock is page 0.
  - The root is page 1.
  - Visit nodes level by level from the root downward. Within a level, visit
    nodes in left-to-right order, which is the order their parents reference
    them (child[0], child[1], ... for each parent in turn). Assign the next
    sequential id to each node as it is visited.

Thus for any given tree shape and contents there is exactly one legal set of
page ids and exactly one legal file image. page_count is 1 plus the number of
nodes. Leaf next_leaf pointers use canonical ids.

4. Operation files

An operation file is UTF-8 text, one operation per line, lines separated by a
single newline. Blank lines are ignored. Each line is one of:

  I <key> <value>     insert or overwrite
  D <key>             delete

`<key>` is a decimal unsigned 64-bit integer. `<value>` is a whitespace-free
token of 1..255 printable ASCII characters. Operations are applied strictly in
file order. Inserting a key already present replaces its value and changes no
structure. Deleting a key that is absent changes nothing.

5. Insertion

An insert descends from the root to the unique leaf whose key range covers the
key, and places the entry in ascending order (or overwrites in place). If the
leaf then holds LEAF_CAP+1 entries it splits; the split may cascade upward.

5.1 Leaf split

A leaf that reaches 5 entries is split into a left node and a right node. The
left node keeps the first 3 entries; the right node takes the remaining 2. The
separator handed to the parent is a copy of the first key of the right node; the
key itself remains present in the right leaf. The right node is a new leaf and
becomes the left node's successor in the leaf chain: the left node's next pointer
becomes the right node, and the right node's next pointer becomes what the left
node's next pointer was before the split.

5.2 Internal split

An internal node that reaches 5 separator keys (6 children) is split into a left
node and a right node. The left node keeps the first 2 keys and the first 3
children; the right node takes the last 2 keys and the last 3 children. The
middle key (the 3rd of the 5, index 2) is removed from the node entirely and
handed to the parent as the separator between the two halves.

5.3 Propagation and root growth

When a node splits, the separator and the new right node are inserted into the
parent, which may itself overflow and split by the same rules. If the root
splits, a new internal root is created holding the single promoted separator and
the two halves as its two children; the height grows by 1.

6. Deletion

A delete descends to the leaf holding the key and removes the entry. If the key
is absent nothing happens. Removal may drop a node below its minimum occupancy,
which is then repaired.

6.1 Minimum occupancy

  A non-root leaf must hold at least 2 entries.
  A non-root internal node must hold at least 3 children (at least 2 keys).
  The root is exempt: a root leaf may hold any number of entries including 0; a
  root internal node must hold at least 1 key (2 children).

6.2 Repair of an underflowing node

Let N be a node that has fallen below its minimum, let P be its parent, and let i
be the index of N among P's children (so N is child[i]). Repair chooses exactly
one of borrow or merge:

  Borrow is attempted first. A sibling can lend only if it would remain at or
  above its minimum after giving one element away. The left sibling (child[i-1])
  is preferred; the right sibling (child[i+1]) is used only when the left sibling
  does not exist or cannot lend.

    Leaf, borrow from left: the left sibling's last entry moves to the front of
    N. The separator P.key[i-1] becomes N's new first key.

    Leaf, borrow from right: the right sibling's first entry moves to the end of
    N. The separator P.key[i] becomes the right sibling's new first key.

    Internal, borrow from left: P.key[i-1] descends to become N's new first key,
    and the left sibling's last child moves to become N's new first child; the
    left sibling's last key is removed from it and becomes the new P.key[i-1].

    Internal, borrow from right: P.key[i] descends to become N's new last key, and
    the right sibling's first child moves to become N's new last child; the right
    sibling's first key is removed from it and becomes the new P.key[i].

  Merge is used when neither sibling can lend. Merging with the left sibling is
  preferred; the right sibling is merged only when there is no left sibling.

    Leaf merge: the two leaves' entries are concatenated into the left one in key
    order, the left node's next pointer becomes the right node's next pointer, and
    the separator between them together with the right child pointer is removed
    from P.

    Internal merge: the separator between the two nodes in P is pulled down and
    placed between the left node's keys and the right node's keys; the children of
    both nodes are concatenated (left's children then right's children); that
    separator and the right child pointer are removed from P.

  A merge removes a key and a child from P, which may then underflow; the same
  repair is applied to P, and so on up the tree.

6.3 Root collapse

If repairs empty the root internal node down to a single child (0 keys), that
child becomes the new root and the height drops by 1. A root leaf that becomes
empty remains the root as an empty leaf with height 1.

7. Commands

  bpt build <ops-file> --out <idx>
      Start from an empty tree (a single empty root leaf) and apply the
      operations in <ops-file> in order, then write the index to <idx>.

  bpt apply <idx-in> <ops-file> <idx-out>
      Load the index at <idx-in>, apply the operations in <ops-file> in order,
      and write the resulting index to <idx-out>. <idx-in> and <idx-out> may
      differ; <idx-in> is not modified.

  bpt get <idx> <key>
      Print the value bytes for <key> followed by a newline, or the line
      NOT-FOUND if the key is absent.

  bpt range <idx> <lo> <hi>
      Print every entry whose key lies in the inclusive range [<lo>,<hi>] in
      ascending key order, each as the key in decimal, a single tab, the value
      bytes, and a newline. The scan walks the leaf chain. If no key is in range
      nothing is printed.

  bpt dump <idx>
      Print a canonical textual description of the tree, exactly:

        line 1: height <H>
        line 2: root <root_page_id>
        then one line per node in ascending canonical page-id order:
          for an internal node:
            internal page <id> keys <k0> <k1> ... children <c0> <c1> ...
          for a leaf node:
            leaf page <id> next <n> entries <k0>:<v0> <k1>:<v1> ...

      Tokens are separated by exactly one space, there is no trailing space, and
      each line ends with a newline. <n> is the next leaf's canonical id, or the
      single character - when there is no next leaf. Keys are decimal. An empty
      root leaf prints its line as: leaf page 1 next - entries  (the word
      entries followed by nothing).

All output is written to standard output. On a usage error (wrong argument
count, unreadable file, malformed operation) the tool prints nothing to standard
output and exits with a non-zero status.
