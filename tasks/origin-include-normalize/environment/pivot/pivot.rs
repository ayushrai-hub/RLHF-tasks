use crate::model::{Ctx, Edge};

pub struct Node {
    pub name: String,
}

pub fn op_a(ctx: &Ctx, nodes: &[Node]) -> Vec<Edge> {
    let mut out = Vec::new();
    for nd in nodes {
        for edge in &ctx.edges {
            if edge.from == nd.name && edge.ord > 0 {
                out.push(edge.clone());
            }
        }
    }
    out.sort_by(|a, b| a.to.cmp(&b.to).then(a.ord.cmp(&b.ord)));
    out
}
