//! Single-pass inline parser. It scans the inline content left to right,
//! building the node list, recording emphasis delimiter runs and `[`/`![`
//! brackets on one delimiter stack, and resolving a link or image when a `]`
//! closes an active bracket. Emphasis is paired by `process_emphasis`, which is
//! run bounded to a link's text as each link resolves and once over everything
//! at the end. See `docs/INLINE.md`, `docs/EMPHASIS.md`, and `docs/LINKS.md`.

use crate::node::{DelimRun, Kind, Node};
use crate::text::{decode_entity, is_ascii_punct, is_unicode_punct, is_unicode_ws};

/// Parse inline content into the node arena (already threaded into a list).
pub fn parse(input: &str) -> Vec<Node> {
    let mut p = Parser {
        chars: input.chars().collect(),
        pos: 0,
        nodes: Vec::new(),
        tail: None,
        stack: Vec::new(),
    };
    p.run();
    p.process_emphasis(0);
    p.nodes
}

struct Parser {
    chars: Vec<char>,
    pos: usize,
    nodes: Vec<Node>,
    tail: Option<usize>,
    /// Node indices of the `Delim` and `Bracket` nodes, in document order.
    stack: Vec<usize>,
}

impl Parser {
    fn push(&mut self, kind: Kind) -> usize {
        let idx = self.nodes.len();
        let prev = self.tail;
        self.nodes.push(Node { kind, prev, next: None });
        if let Some(t) = prev {
            self.nodes[t].next = Some(idx);
        }
        self.tail = Some(idx);
        idx
    }

    fn push_text(&mut self, s: &str) {
        if !s.is_empty() {
            self.push(Kind::Text(s.to_string()));
        }
    }

    fn run(&mut self) {
        let n = self.chars.len();
        let mut pending = String::new();
        macro_rules! flush {
            () => {
                if !pending.is_empty() {
                    let s = std::mem::take(&mut pending);
                    self.push(Kind::Text(s));
                }
            };
        }
        while self.pos < n {
            let c = self.chars[self.pos];
            match c {
                '\\' => {
                    if self.pos + 1 < n && self.chars[self.pos + 1] == '\n' {
                        flush!();
                        self.push(Kind::HardBreak);
                        self.pos += 2;
                    } else if self.pos + 1 < n && !is_ascii_punct(self.chars[self.pos + 1]) {
                        pending.push(self.chars[self.pos + 1]);
                        self.pos += 2;
                    } else {
                        pending.push('\\');
                        self.pos += 1;
                    }
                }
                '`' => {
                    flush!();
                    if !self.scan_code_span() {
                        // not closed: the run of backticks is literal
                        let mut j = self.pos;
                        while j < n && self.chars[j] == '`' {
                            j += 1;
                        }
                        let lit: String = self.chars[self.pos..j].iter().collect();
                        self.push_text(&lit);
                        self.pos = j;
                    }
                }
                '&' => {
                    if let Some((decoded, len)) = decode_entity(&self.chars[self.pos..]) {
                        pending.push_str(&decoded);
                        self.pos += len;
                    } else {
                        pending.push('&');
                        self.pos += 1;
                    }
                }
                '\n' => {
                    let trimmed = pending.trim_end_matches(' ');
                    let spaces = pending.chars().count() - trimmed.chars().count();
                    pending.truncate(trimmed.len());
                    flush!();
                    if spaces >= 1 {
                        self.push(Kind::HardBreak);
                    } else {
                        self.push(Kind::SoftBreak);
                    }
                    self.pos += 1;
                    while self.pos < n && self.chars[self.pos] == ' ' {
                        self.pos += 1;
                    }
                }
                '[' => {
                    flush!();
                    let node = self.push(Kind::Bracket { image: false, active: true });
                    self.stack.push(node);
                    self.pos += 1;
                }
                '!' if self.pos + 1 < n && self.chars[self.pos + 1] == '[' => {
                    flush!();
                    let node = self.push(Kind::Bracket { image: true, active: true });
                    self.stack.push(node);
                    self.pos += 2;
                }
                ']' => {
                    flush!();
                    self.handle_close_bracket();
                }
                '*' | '_' => {
                    flush!();
                    self.scan_delim_run(c);
                }
                _ => {
                    pending.push(c);
                    self.pos += 1;
                }
            }
        }
        if !pending.is_empty() {
            self.push(Kind::Text(pending));
        }
    }

    /// Scan a code span starting at `self.pos` (on a backtick). On success
    /// pushes a Code node and advances `self.pos`; returns whether it closed.
    fn scan_code_span(&mut self) -> bool {
        let n = self.chars.len();
        let start = self.pos;
        let mut j = start;
        while j < n && self.chars[j] == '`' {
            j += 1;
        }
        let open_len = j - start;
        let mut k = j;
        while k < n {
            if self.chars[k] == '`' {
                let mut m = k;
                while m < n && self.chars[m] == '`' {
                    m += 1;
                }
                if m - k >= open_len {
                    let raw: String = self.chars[j..k].iter().collect();
                    self.push(Kind::Code(normalize_code(&raw)));
                    self.pos = k + open_len;
                    return true;
                }
                k = m;
            } else {
                k += 1;
            }
        }
        false
    }

    fn scan_delim_run(&mut self, c: char) {
        let n = self.chars.len();
        let start = self.pos;
        let mut j = start;
        while j < n && self.chars[j] == c {
            j += 1;
        }
        let run = j - start;
        let before = if start == 0 { '\n' } else { self.chars[start - 1] };
        let after = if j >= n { '\n' } else { self.chars[j] };
        let (can_open, can_close) = flanking(c, before, after);
        let node = self.push(Kind::Delim(DelimRun {
            ch: c,
            num: run,
            orig: run,
            can_open,
            can_close,
        }));
        self.stack.push(node);
        self.pos = j;
    }

    /// Handle a `]` at `self.pos`: resolve an inline link/image against the last
    /// active bracket, or emit a literal `]`.
    fn handle_close_bracket(&mut self) {
        self.pos += 1; // consume ']'
        let opener_si = match self
            .stack
            .iter()
            .rposition(|&nx| matches!(self.nodes[nx].kind, Kind::Bracket { .. }))
        {
            Some(x) => x,
            None => {
                self.push_text("]");
                return;
            }
        };
        let opener = self.stack[opener_si];
        let (image, active) = match self.nodes[opener].kind {
            Kind::Bracket { image, active } => (image, active),
            _ => unreachable!(),
        };
        if !active {
            self.stack.remove(opener_si);
            self.push_text("]");
            return;
        }
        let saved = self.pos;
        if let Some((dest, title)) = self.parse_inline_link() {
            if image {
                self.nodes[opener].kind = Kind::ImageOpen { dest, title };
                self.push(Kind::ImageClose);
            } else {
                self.nodes[opener].kind = Kind::LinkOpen { dest, title };
                self.push(Kind::LinkClose);
            }
            // pair emphasis within the just-closed link/image text
            self.process_emphasis(opener_si + 1);
            self.stack.remove(opener_si);
            let _ = image;
        } else {
            self.pos = saved;
            self.stack.remove(opener_si);
            self.push_text("]");
        }
    }

    /// Try to parse `(dest (title)?)` at `self.pos`. Destinations are a bare run
    /// of non-space, non-`)` characters, or `<...>`; titles are `"..."`.
    fn parse_inline_link(&mut self) -> Option<(String, Option<String>)> {
        let n = self.chars.len();
        if self.pos >= n || self.chars[self.pos] != '(' {
            return None;
        }
        let mut i = self.pos + 1;
        let skip_ws = |chars: &[char], mut i: usize| {
            while i < chars.len() && (chars[i] == ' ' || chars[i] == '\t' || chars[i] == '\n') {
                i += 1;
            }
            i
        };
        i = skip_ws(&self.chars, i);
        // destination
        let dest;
        if i < n && self.chars[i] == '<' {
            let mut j = i + 1;
            let mut d = String::new();
            while j < n && self.chars[j] != '>' && self.chars[j] != '\n' {
                d.push(self.chars[j]);
                j += 1;
            }
            if j >= n || self.chars[j] != '>' {
                return None;
            }
            dest = d;
            i = j + 1;
        } else {
            let mut j = i;
            let mut d = String::new();
            while j < n {
                let ch = self.chars[j];
                if ch == ' ' || ch == '\t' || ch == '\n' || ch == ')' {
                    break;
                }
                d.push(ch);
                j += 1;
            }
            dest = d;
            i = j;
        }
        i = skip_ws(&self.chars, i);
        // optional title in double quotes
        let mut title = None;
        if i < n && self.chars[i] == '"' {
            let mut j = i + 1;
            let mut t = String::new();
            while j < n && self.chars[j] != '"' {
                t.push(self.chars[j]);
                j += 1;
            }
            if j >= n {
                return None;
            }
            title = Some(t);
            i = j + 1;
            i = skip_ws(&self.chars, i);
        }
        if i < n && self.chars[i] == ')' {
            self.pos = i + 1;
            Some((dest, title))
        } else {
            None
        }
    }

    /// Pair emphasis delimiters on the stack at positions `>= bottom`, splicing
    /// `<em>`/`<strong>` markers into the node list. Bracket entries on the stack
    /// are skipped as candidates but mark search boundaries.
    fn process_emphasis(&mut self, bottom: usize) {
        let nodes = &mut self.nodes;
        let stack = &mut self.stack;
        let mut openers_bottom = [[bottom as i64 - 1; 3]; 2];
        let ci = |ch: char| if ch == '*' { 0 } else { 1 };

        let mut c = bottom;
        while c < stack.len() {
            let closer = stack[c];
            let (cch, corig, ccan_close) = match &nodes[closer].kind {
                Kind::Delim(d) => (d.ch, d.orig, d.can_close),
                _ => {
                    c += 1;
                    continue;
                }
            };
            if !ccan_close {
                c += 1;
                continue;
            }
            let limit = openers_bottom[ci(cch)][corig % 3];
            let mut o = c as i64 - 1;
            let mut found: Option<usize> = None;
            while o >= 0 && o > limit && o >= bottom as i64 {
                let opener = stack[o as usize];
                if let Kind::Delim(od) = &nodes[opener].kind {
                    let odd = false;
                    if od.ch == cch && od.can_open && !odd {
                        found = Some(o as usize);
                        break;
                    }
                }
                o -= 1;
            }
            match found {
                Some(opos) => {
                    let opener = stack[opos];
                    let use_delims = 1;
                    let strong = use_delims == 2;
                    let open_idx = push_free(nodes, Kind::Open(strong));
                    insert_after(nodes, opener, open_idx);
                    let close_idx = push_free(nodes, Kind::Close(strong));
                    insert_before(nodes, closer, close_idx);
                    consume(nodes, opener, use_delims);
                    consume(nodes, closer, use_delims);
                    stack.drain(opos + 1..c);
                    c = opos + 1;
                    if delim_num(nodes, opener) == 0 {
                        unlink(nodes, opener);
                        stack.remove(opos);
                        c -= 1;
                    }
                    if delim_num(nodes, closer) == 0 {
                        unlink(nodes, closer);
                        stack.remove(c);
                    }
                }
                None => {
                    openers_bottom[ci(cch)][corig % 3] = c as i64 - 1;
                    if !delim_field(nodes, closer, 'O') {
                        // closer cannot open either: drop it
                        // (kept on stack as literal text via its node)
                        stack.remove(c);
                    } else {
                        c += 1;
                    }
                }
            }
        }
        // drop the delimiters we processed from the stack (their nodes remain)
        while stack.len() > bottom {
            stack.pop();
        }
    }
}

/// `which`: 'o' => closer.can_open, 'O' => closer.can_open (same; kept for read).
fn delim_field(nodes: &[Node], idx: usize, _which: char) -> bool {
    if let Kind::Delim(d) = &nodes[idx].kind {
        d.can_open
    } else {
        false
    }
}

fn delim_num(nodes: &[Node], idx: usize) -> usize {
    if let Kind::Delim(d) = &nodes[idx].kind {
        d.num
    } else {
        0
    }
}

fn consume(nodes: &mut [Node], idx: usize, n: usize) {
    if let Kind::Delim(d) = &mut nodes[idx].kind {
        d.num -= n;
    }
}

fn push_free(nodes: &mut Vec<Node>, kind: Kind) -> usize {
    nodes.push(Node { kind, prev: None, next: None });
    nodes.len() - 1
}

fn insert_after(nodes: &mut [Node], at: usize, new: usize) {
    let nxt = nodes[at].next;
    nodes[new].prev = Some(at);
    nodes[new].next = nxt;
    nodes[at].next = Some(new);
    if let Some(nx) = nxt {
        nodes[nx].prev = Some(new);
    }
}

fn insert_before(nodes: &mut [Node], at: usize, new: usize) {
    let prv = nodes[at].prev;
    nodes[new].next = Some(at);
    nodes[new].prev = prv;
    nodes[at].prev = Some(new);
    if let Some(p) = prv {
        nodes[p].next = Some(new);
    }
}

fn unlink(nodes: &mut [Node], idx: usize) {
    let prv = nodes[idx].prev;
    let nxt = nodes[idx].next;
    if let Some(p) = prv {
        nodes[p].next = nxt;
    }
    if let Some(nx) = nxt {
        nodes[nx].prev = prv;
    }
    nodes[idx].kind = Kind::Removed;
    nodes[idx].prev = None;
    nodes[idx].next = None;
}

fn normalize_code(raw: &str) -> String {
    raw.chars().map(|c| if c == '\n' { ' ' } else { c }).collect()
}

fn flanking(ch: char, before: char, after: char) -> (bool, bool) {
    let after_ws = is_unicode_ws(after);
    let before_ws = is_unicode_ws(before);

    let left_flanking = !after_ws && !is_unicode_punct(after);
    let right_flanking = !before_ws && !is_unicode_punct(before);

    let _ = ch;
    (left_flanking, right_flanking)
}
