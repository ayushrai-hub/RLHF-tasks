//! Render the processed inline node list to HTML (see `docs/MODEL.md` and
//! `docs/LINKS.md`).

use crate::node::{Kind, Node};
use crate::text::escape_html;

/// Walk the linked list from its head, emitting the inline HTML.
pub fn render(nodes: &[Node]) -> String {
    let mut out = String::new();
    let mut cur = head(nodes);
    while let Some(i) = cur {
        match &nodes[i].kind {
            Kind::Text(s) => out.push_str(&escape_html(s)),
            Kind::Code(s) => {
                out.push_str("<code>");
                out.push_str(&escape_html(s));
                out.push_str("</code>");
            }
            Kind::SoftBreak => out.push('\n'),
            Kind::HardBreak => out.push_str("<br />\n"),
            Kind::Open(false) => out.push_str("<em>"),
            Kind::Open(true) => out.push_str("<strong>"),
            Kind::Close(false) => out.push_str("</em>"),
            Kind::Close(true) => out.push_str("</strong>"),
            Kind::Delim(d) => {
                for _ in 0..d.num {
                    out.push(d.ch);
                }
            }
            Kind::Bracket { image, .. } => out.push_str(if *image { "![" } else { "[" }),
            Kind::LinkOpen { dest, title } => {
                out.push_str("<a href=\"");
                out.push_str(&escape_attr(dest));
                out.push('"');
                if let Some(t) = title {
                    out.push_str(" title=\"");
                    out.push_str(&escape_attr(t));
                    out.push('"');
                }
                out.push('>');
            }
            Kind::LinkClose => out.push_str("</a>"),
            Kind::ImageOpen { dest, title } => {
                let (alt, after) = image_alt(nodes, i);
                out.push_str("<img src=\"");
                out.push_str(&escape_attr(dest));
                out.push_str("\" alt=\"");
                out.push_str(&alt);
                out.push('"');
                if let Some(t) = title {
                    out.push_str(" title=\"");
                    out.push_str(&escape_attr(t));
                    out.push('"');
                }
                out.push_str(" />");
                cur = after;
                continue;
            }
            Kind::ImageClose => {}
            Kind::Removed => {}
        }
        cur = nodes[i].next;
    }
    out
}

/// The alt text of an image: the plain text of its children (emphasis/link
/// markers dropped), HTML-escaped for the attribute. Returns the alt and the
/// node index just past the matching `ImageClose`.
fn image_alt(nodes: &[Node], open: usize) -> (String, Option<usize>) {
    let mut alt = String::new();
    let mut cur = nodes[open].next;
    while let Some(i) = cur {
        match &nodes[i].kind {
            Kind::ImageClose => return (escape_attr(&alt), nodes[i].next),
            Kind::Text(s) => alt.push_str(s),
            Kind::Code(_) => {}
            Kind::SoftBreak | Kind::HardBreak => alt.push('\n'),
            Kind::Delim(d) => {
                for _ in 0..d.num {
                    alt.push(d.ch);
                }
            }
            _ => {} // emphasis/link markers contribute no alt text
        }
        cur = nodes[i].next;
    }
    (escape_attr(&alt), None)
}

/// Escape a string for an HTML attribute value.
fn escape_attr(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for c in s.chars() {
        match c {
            '&' => out.push_str("&amp;"),
            '"' => out.push_str("&quot;"),
            '<' => out.push_str("&lt;"),
            '>' => out.push_str("&gt;"),
            _ => out.push(c),
        }
    }
    out
}

/// The live head of the list: the one non-removed node with no predecessor.
fn head(nodes: &[Node]) -> Option<usize> {
    for (i, n) in nodes.iter().enumerate() {
        if !matches!(n.kind, Kind::Removed) && n.prev.is_none() {
            return Some(i);
        }
    }
    None
}
