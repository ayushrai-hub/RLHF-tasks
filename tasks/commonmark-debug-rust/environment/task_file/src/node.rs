//! The inline node arena. Nodes live in a `Vec` and are threaded into a doubly
//! linked list (by `prev`/`next` indices) so the emphasis pass can splice
//! emphasis markers in and drop spent delimiters without moving anything.

/// An unprocessed run of emphasis delimiters (`*` or `_`).
#[derive(Clone)]
pub struct DelimRun {
    pub ch: char,
    /// Remaining (unconsumed) delimiters in the run.
    pub num: usize,
    /// Original run length, used by the rule-of-3 match test.
    pub orig: usize,
    pub can_open: bool,
    pub can_close: bool,
}

#[derive(Clone)]
pub enum Kind {
    /// Literal text, HTML-escaped at render time.
    Text(String),
    /// A code span's already-normalised content.
    Code(String),
    SoftBreak,
    HardBreak,
    /// An unprocessed emphasis delimiter run.
    Delim(DelimRun),
    /// An emphasis opener; `true` for `<strong>`, `false` for `<em>`.
    Open(bool),
    /// An emphasis closer; `true` for `</strong>`, `false` for `</em>`.
    Close(bool),
    /// A `[` or `![` bracket awaiting a possible link/image. `image` is true for
    /// `![`; once `active` is cleared the bracket can no longer open a link.
    Bracket { image: bool, active: bool },
    /// A resolved link opener (`<a href=…>`) and its closer (`</a>`).
    LinkOpen { dest: String, title: Option<String> },
    LinkClose,
    /// A resolved image opener and closer; the children between supply the alt
    /// text and are not rendered as HTML.
    ImageOpen { dest: String, title: Option<String> },
    ImageClose,
    /// A tombstone for a node removed from the list.
    Removed,
}

#[derive(Clone)]
pub struct Node {
    pub kind: Kind,
    pub prev: Option<usize>,
    pub next: Option<usize>,
}

impl Node {
    fn new(kind: Kind) -> Self {
        Node { kind, prev: None, next: None }
    }
    pub fn text(s: String) -> Self {
        Node::new(Kind::Text(s))
    }
    pub fn code(s: String) -> Self {
        Node::new(Kind::Code(s))
    }
    pub fn soft_break() -> Self {
        Node::new(Kind::SoftBreak)
    }
    pub fn hard_break() -> Self {
        Node::new(Kind::HardBreak)
    }
    pub fn delim(run: DelimRun) -> Self {
        Node::new(Kind::Delim(run))
    }
    pub fn bracket(image: bool) -> Self {
        Node::new(Kind::Bracket { image, active: true })
    }
}

/// Thread the nodes (in `Vec` order) into a doubly linked list, returning the
/// head index. Tombstones are not produced here; every node is linked.
pub fn link(nodes: &mut [Node]) -> Option<usize> {
    if nodes.is_empty() {
        return None;
    }
    for i in 0..nodes.len() {
        nodes[i].prev = if i == 0 { None } else { Some(i - 1) };
        nodes[i].next = if i + 1 == nodes.len() { None } else { Some(i + 1) };
    }
    Some(0)
}
