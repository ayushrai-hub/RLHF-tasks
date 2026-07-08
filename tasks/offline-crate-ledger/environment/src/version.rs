use std::cmp::Ordering;

#[derive(Clone, Eq, PartialEq, Debug)]
pub struct Version {
    pub raw: String,
    nums: [u64; 3],
    pre: Option<String>,
}

impl Version {
    pub fn parse(s: &str) -> Result<Self, String> {
        let (core, pre) = match s.split_once('-') {
            Some((core, pre)) if !pre.is_empty() => (core, Some(pre.to_string())),
            Some(_) => return Err(format!("bad version {s}")),
            None => (s, None),
        };
        let parts: Vec<_> = core.split('.').collect();
        if parts.len() != 3 {
            return Err(format!("bad version {s}"));
        }
        let mut nums = [0u64; 3];
        for (idx, part) in parts.iter().enumerate() {
            nums[idx] = part.parse().map_err(|_| format!("bad version {s}"))?;
        }
        Ok(Self {
            raw: s.to_string(),
            nums,
            pre,
        })
    }
}

impl Ord for Version {
    fn cmp(&self, other: &Self) -> Ordering {
        match self.nums.cmp(&other.nums) {
            Ordering::Equal => self.pre.cmp(&other.pre),
            ord => ord,
        }
    }
}

impl PartialOrd for Version {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

pub fn satisfies_all(version: &Version, constraint: &str) -> bool {
    constraint.split(',').all(|part| satisfies_one(version, part.trim()))
}

pub fn satisfies_one(version: &Version, part: &str) -> bool {
    let ops = [">=", "<=", ">", "<", "="];
    for op in ops {
        if let Some(rhs) = part.strip_prefix(op) {
            if let Ok(other) = Version::parse(rhs) {
                return match op {
                    ">=" => version >= &other,
                    "<=" => version <= &other,
                    ">" => version > &other,
                    "<" => version < &other,
                    "=" => version == &other,
                    _ => false,
                };
            }
        }
    }
    false
}
