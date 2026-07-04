#!/bin/bash
set -euo pipefail

# Oracle solution: a pure standard-library Rust program that, for each monic integer
# quintic, reports irreducibility over Q, the exact discriminant, the Galois group over
# Q (one of C5, D5, F20, A5, S5), radical-solvability, and the exact pair-sum resolvent.
#
# Three from-scratch engines:
#   1. Galois data via Dedekind's theorem (factor f mod many good primes, read the
#      Frobenius cycle types, map the set of cycle types to the transitive subgroup
#      of S5). irreducible <=> (5) seen; G<=A5 <=> no odd cycle type; in A5: (3 1 1)=>A5,
#      (2 2 1)=>D5, else C5; else (2 1 1 1)/(3 1 1)/(3 2)=>S5 else F20; solvable <=>
#      reducible or group in {C5,D5,F20}.
#   2. The exact discriminant det(Sylvester(f,f')) via a base-1e9 signed big integer and
#      a division-free subset-DP determinant.
#   3. The pair-sum resolvent R2(Z) = prod_{i<j}(Z-(x_i+x_j)), a monic degree-10 integer
#      polynomial. Its coefficients are recovered with exact big integers from the
#      quintic's power sums (Newton's identities), composed into the power sums of the
#      pair sums, then turned back into elementary symmetric functions (Newton again).
#      No roots, no floating point, no fixed-width integers.

cd /app
export CARGO_NET_OFFLINE=true
mkdir -p /app/src

cat > /app/Cargo.toml <<'TOML_EOF'
[package]
name = "coral-galois-lantern"
version = "0.1.0"
edition = "2021"

[[bin]]
name = "coral-galois-lantern"
path = "src/main.rs"

[dependencies]

[profile.release]
opt-level = 3
TOML_EOF

cat > /app/src/main.rs <<'RUST_EOF'
use std::env;
use std::fs;
use std::process;
use std::collections::HashSet;

// ===== finite-field Dedekind classification =====
fn pnorm(a: &mut Vec<i64>, p: i64) {
    for x in a.iter_mut() {
        *x = ((*x % p) + p) % p;
    }
    while a.len() > 1 && *a.last().unwrap() == 0 {
        a.pop();
    }
    if a.is_empty() {
        a.push(0);
    }
}

fn pdeg(a: &[i64]) -> isize {
    (a.len() as isize) - 1
}

fn is_zero(a: &[i64]) -> bool {
    a.len() == 1 && a[0] == 0
}

fn psub(a: &[i64], b: &[i64], p: i64) -> Vec<i64> {
    let n = a.len().max(b.len());
    let mut r = vec![0i64; n];
    for i in 0..a.len() {
        r[i] += a[i];
    }
    for i in 0..b.len() {
        r[i] -= b[i];
    }
    pnorm(&mut r, p);
    r
}

fn pmul(a: &[i64], b: &[i64], p: i64) -> Vec<i64> {
    if is_zero(a) || is_zero(b) {
        return vec![0];
    }
    let mut r = vec![0i64; a.len() + b.len() - 1];
    for (i, &ai) in a.iter().enumerate() {
        if ai != 0 {
            for (j, &bj) in b.iter().enumerate() {
                r[i + j] = (r[i + j] + ai * bj) % p;
            }
        }
    }
    pnorm(&mut r, p);
    r
}

fn modinv(a: i64, p: i64) -> i64 {
    // p prime, a not divisible by p
    let mut res = 1i64;
    let mut base = ((a % p) + p) % p;
    let mut e = p - 2;
    while e > 0 {
        if e & 1 == 1 {
            res = res * base % p;
        }
        base = base * base % p;
        e >>= 1;
    }
    res
}

// returns (quotient, remainder)
fn pdivmod(a: &[i64], b: &[i64], p: i64) -> (Vec<i64>, Vec<i64>) {
    let mut a = a.to_vec();
    pnorm(&mut a, p);
    let mut b = b.to_vec();
    pnorm(&mut b, p);
    let inv = modinv(*b.last().unwrap(), p);
    let qlen = if pdeg(&a) >= pdeg(&b) {
        (pdeg(&a) - pdeg(&b) + 1) as usize
    } else {
        1
    };
    let mut q = vec![0i64; qlen];
    while !is_zero(&a) && pdeg(&a) >= pdeg(&b) {
        let shift = (pdeg(&a) - pdeg(&b)) as usize;
        let coef = (*a.last().unwrap() * inv) % p;
        q[shift] = coef;
        for i in 0..b.len() {
            a[shift + i] = ((a[shift + i] - coef * b[i]) % p + p) % p;
        }
        pnorm(&mut a, p);
        if is_zero(&a) {
            break;
        }
    }
    pnorm(&mut q, p);
    (q, a)
}

fn pmod(a: &[i64], b: &[i64], p: i64) -> Vec<i64> {
    pdivmod(a, b, p).1
}

fn pgcd(a: &[i64], b: &[i64], p: i64) -> Vec<i64> {
    let mut a = a.to_vec();
    pnorm(&mut a, p);
    let mut b = b.to_vec();
    pnorm(&mut b, p);
    while !is_zero(&b) {
        let r = pmod(&a, &b, p);
        a = b;
        b = r;
    }
    if is_zero(&a) {
        return vec![0];
    }
    let inv = modinv(*a.last().unwrap(), p);
    for x in a.iter_mut() {
        *x = *x * inv % p;
    }
    a
}

// raise `base` to the p-th power modulo `modulus` in F_p[x] (one Frobenius step)
fn pow_p(base: &[i64], modulus: &[i64], p: i64) -> Vec<i64> {
    let mut result = vec![1i64];
    let mut b = pmod(base, modulus, p);
    let mut e = p;
    while e > 0 {
        if e & 1 == 1 {
            result = pmod(&pmul(&result, &b, p), modulus, p);
        }
        e >>= 1;
        if e > 0 {
            b = pmod(&pmul(&b, &b, p), modulus, p);
        }
    }
    result
}

fn poly_deriv_lowfirst(a: &[i64], p: i64) -> Vec<i64> {
    if a.len() <= 1 {
        return vec![0];
    }
    let mut r = vec![0i64; a.len() - 1];
    for i in 1..a.len() {
        r[i - 1] = (i as i64 % p) * a[i] % p;
    }
    pnorm(&mut r, p);
    r
}

// Reduce a monic-highest-first integer quintic to low-first mod p.
fn poly_mod_p(c: &[i64], p: i64) -> Vec<i64> {
    let mut v: Vec<i64> = c.iter().rev().map(|&x| ((x % p) + p) % p).collect();
    pnorm(&mut v, p);
    v
}

// cycle type (sorted ascending factor degrees) or None for a bad prime.
fn cycle_type_modp(c: &[i64], p: i64) -> Option<Vec<usize>> {
    // leading coeff is c[0] (highest-first). monic => 1, but guard anyway.
    if ((c[0] % p) + p) % p == 0 {
        return None;
    }
    let f = poly_mod_p(c, p);
    if pdeg(&f) != (c.len() as isize - 1) {
        return None;
    }
    // squarefree check
    let fp = poly_deriv_lowfirst(&f, p);
    if is_zero(&fp) {
        return None;
    }
    let g = pgcd(&f, &fp, p);
    if pdeg(&g) != 0 {
        return None; // not squarefree mod p -> bad prime
    }
    // distinct-degree factorization
    let x = vec![0i64, 1i64];
    let mut degs: Vec<usize> = Vec::new();
    let mut fcur = f.clone();
    let mut h = x.clone(); // x^(p^0)
    let mut d: usize = 1;
    while pdeg(&fcur) >= 1 && (d as isize) <= pdeg(&fcur) {
        h = pow_p(&h, &fcur, p); // h = x^(p^d) mod fcur
        let diff = psub(&h, &x, p);
        let g = pgcd(&diff, &fcur, p);
        if pdeg(&g) > 0 {
            let k = (pdeg(&g) as usize) / d;
            for _ in 0..k {
                degs.push(d);
            }
            let (q, _r) = pdivmod(&fcur, &g, p);
            fcur = q;
            pnorm(&mut fcur, p);
            if pdeg(&fcur) >= 1 {
                h = pmod(&h, &fcur, p);
            }
        }
        d += 1;
    }
    if pdeg(&fcur) >= 1 {
        degs.push(pdeg(&fcur) as usize);
    }
    degs.sort_unstable();
    Some(degs)
}

fn sieve(n: usize) -> Vec<i64> {
    let mut is_p = vec![true; n + 1];
    is_p[0] = false;
    if n >= 1 {
        is_p[1] = false;
    }
    let mut i = 2;
    while i * i <= n {
        if is_p[i] {
            let mut j = i * i;
            while j <= n {
                is_p[j] = false;
                j += i;
            }
        }
        i += 1;
    }
    (2..=n).filter(|&i| is_p[i]).map(|i| i as i64).collect()
}

#[derive(Clone)]
struct Outcome {
    irreducible: bool,
    group: Option<String>,
    solvable: bool,
}

fn classify(c: &[i64], primes: &[i64]) -> Outcome {
    let mut observed: HashSet<Vec<usize>> = HashSet::new();
    for &p in primes {
        if let Some(ct) = cycle_type_modp(c, p) {
            observed.insert(ct);
        }
    }
    let has = |t: &[usize]| observed.contains(&t.to_vec());
    let irreducible = has(&[5]);
    if !irreducible {
        return Outcome {
            irreducible: false,
            group: None,
            solvable: true,
        };
    }
    let odd_present = has(&[1, 1, 1, 2]) || has(&[1, 4]) || has(&[2, 3]);
    let in_a5 = !odd_present;
    let g = if in_a5 {
        if has(&[1, 1, 3]) {
            "A5"
        } else if has(&[1, 2, 2]) {
            "D5"
        } else {
            "C5"
        }
    } else if has(&[1, 1, 1, 2]) || has(&[1, 1, 3]) || has(&[2, 3]) {
        "S5"
    } else {
        "F20"
    };
    let solvable = g == "C5" || g == "D5" || g == "F20";
    Outcome {
        irreducible: true,
        group: Some(g.to_string()),
        solvable,
    }
}



const BASE: u64 = 1_000_000_000;

#[derive(Clone)]
struct Big { sign: i32, mag: Vec<u64> }

impl Big {
    fn zero() -> Big { Big { sign: 0, mag: vec![] } }
    fn from_i64(v: i64) -> Big {
        if v == 0 { return Big::zero(); }
        let sign = if v < 0 { -1 } else { 1 };
        let mut u = (v as i128).unsigned_abs() as u128;
        let mut mag = vec![];
        while u > 0 { mag.push((u % BASE as u128) as u64); u /= BASE as u128; }
        Big { sign, mag }
    }
    fn trim(mut self) -> Big {
        while let Some(&0) = self.mag.last() { self.mag.pop(); }
        if self.mag.is_empty() { self.sign = 0; }
        self
    }
    fn cmp_mag(a: &[u64], b: &[u64]) -> i32 {
        if a.len() != b.len() { return if a.len() < b.len() { -1 } else { 1 }; }
        for i in (0..a.len()).rev() { if a[i] != b[i] { return if a[i] < b[i] { -1 } else { 1 }; } }
        0
    }
    fn add_mag(a: &[u64], b: &[u64]) -> Vec<u64> {
        let mut r = vec![]; let mut carry = 0u64;
        for i in 0..a.len().max(b.len()) {
            let x = a.get(i).copied().unwrap_or(0) + b.get(i).copied().unwrap_or(0) + carry;
            r.push(x % BASE); carry = x / BASE;
        }
        if carry > 0 { r.push(carry); }
        r
    }
    fn sub_mag(a: &[u64], b: &[u64]) -> Vec<u64> {
        let mut r = vec![]; let mut borrow = 0i64;
        for i in 0..a.len() {
            let mut x = a[i] as i64 - b.get(i).copied().unwrap_or(0) as i64 - borrow;
            if x < 0 { x += BASE as i64; borrow = 1; } else { borrow = 0; }
            r.push(x as u64);
        }
        while let Some(&0) = r.last() { r.pop(); }
        r
    }
    fn add(&self, o: &Big) -> Big {
        if self.sign == 0 { return o.clone(); }
        if o.sign == 0 { return self.clone(); }
        if self.sign == o.sign {
            Big { sign: self.sign, mag: Big::add_mag(&self.mag, &o.mag) }.trim()
        } else {
            match Big::cmp_mag(&self.mag, &o.mag) {
                0 => Big::zero(),
                1 => Big { sign: self.sign, mag: Big::sub_mag(&self.mag, &o.mag) }.trim(),
                _ => Big { sign: o.sign, mag: Big::sub_mag(&o.mag, &self.mag) }.trim(),
            }
        }
    }
    fn sub(&self, o: &Big) -> Big { self.add(&o.neg()) }
    fn neg(&self) -> Big { Big { sign: -self.sign, mag: self.mag.clone() } }
    fn mul(&self, o: &Big) -> Big {
        if self.sign == 0 || o.sign == 0 { return Big::zero(); }
        let mut r = vec![0u128; self.mag.len() + o.mag.len()];
        for (i, &a) in self.mag.iter().enumerate() {
            let mut carry = 0u128;
            for (j, &b) in o.mag.iter().enumerate() {
                let cur = r[i + j] + a as u128 * b as u128 + carry;
                r[i + j] = cur % BASE as u128; carry = cur / BASE as u128;
            }
            let mut k = i + o.mag.len();
            while carry > 0 { let cur = r[k] + carry; r[k] = cur % BASE as u128; carry = cur / BASE as u128; k += 1; }
        }
        Big { sign: self.sign * o.sign, mag: r.iter().map(|&x| x as u64).collect() }.trim()
    }
    fn mul_small(&self, v: i64) -> Big { self.mul(&Big::from_i64(v)) }
    // exact division by a positive small integer d (panics if not exact)
    fn div_small(&self, d: i64) -> Big {
        if self.sign == 0 { return Big::zero(); }
        let dd = d as u128;
        let mut rem = 0u128;
        let mut out = vec![0u64; self.mag.len()];
        for i in (0..self.mag.len()).rev() {
            let cur = rem * BASE as u128 + self.mag[i] as u128;
            out[i] = (cur / dd) as u64;
            rem = cur % dd;
        }
        assert!(rem == 0, "non-exact division by {}", d);
        Big { sign: self.sign, mag: out }.trim()
    }
    fn to_string(&self) -> String {
        if self.sign == 0 { return "0".to_string(); }
        let mut s = String::new();
        if self.sign < 0 { s.push('-'); }
        s.push_str(&self.mag.last().unwrap().to_string());
        for i in (0..self.mag.len() - 1).rev() { s.push_str(&format!("{:09}", self.mag[i])); }
        s
    }
}

fn binom(n: usize, k: usize) -> i64 {
    let mut r = 1i64;
    for i in 0..k { r = r * (n - i) as i64 / (i as i64 + 1); }
    r
}

// R2 coefficients (highest-first, length 11) from monic quintic c=[1,c1,c2,c3,c4,c5]
fn resolvent_pairsum(c: &[i64]) -> Vec<Big> {
    // e_k = (-1)^k c_k  (elementary symmetric of the quintic's roots)
    let e: Vec<Big> = (1..=5).map(|k| {
        let v = if k % 2 == 0 { c[k] } else { -c[k] };
        Big::from_i64(v)
    }).collect();
    let eget = |i: usize| -> Big { if i >= 1 && i <= 5 { e[i - 1].clone() } else { Big::zero() } };

    // power sums p_0..p_10 via Newton (division-free):
    // p_k = sum_{i=1}^{k-1} (-1)^{i-1} e_i p_{k-i} + (-1)^{k-1} k e_k
    let mut p = vec![Big::from_i64(5)]; // p_0 = 5
    for k in 1..=10usize {
        let mut s = Big::zero();
        for i in 1..k {
            let term = eget(i).mul(&p[k - i]);
            if (i - 1) % 2 == 0 { s = s.add(&term); } else { s = s.sub(&term); }
        }
        let ek = eget(k).mul_small(k as i64);
        if (k - 1) % 2 == 0 { s = s.add(&ek); } else { s = s.sub(&ek); }
        p.push(s);
    }

    // pair-sum power sums q_0..q_10:
    // q_k = (1/2)[ sum_m C(k,m) p_m p_{k-m} - 2^k p_k ]
    let mut q = Vec::new();
    for k in 0..=10usize {
        let mut tot = Big::zero();
        for m in 0..=k {
            tot = tot.add(&p[m].mul(&p[k - m]).mul_small(binom(k, m)));
        }
        let twok = Big::from_i64(1i64 << k);
        tot = tot.sub(&twok.mul(&p[k]));
        q.push(tot.div_small(2));
    }

    // elementary symmetric of pair-sums via Newton (reverse), division by k:
    // e'_k = (1/k) sum_{i=1}^{k} (-1)^{i-1} e'_{k-i} q_i ; e'_0 = 1
    let mut ee = vec![Big::from_i64(1)];
    for k in 1..=10usize {
        let mut s = Big::zero();
        for i in 1..=k {
            let term = ee[k - i].mul(&q[i]);
            if (i - 1) % 2 == 0 { s = s.add(&term); } else { s = s.sub(&term); }
        }
        ee.push(s.div_small(k as i64));
    }

    // R2(Z) = sum_{k=0}^{10} (-1)^k e'_k Z^{10-k}
    (0..=10).map(|k| if k % 2 == 0 { ee[k].clone() } else { ee[k].neg() }).collect()
}


// determinant of an n x n Big matrix via subset DP (division-free)
fn det(mat: &[Vec<Big>]) -> Big {
    let n = mat.len();
    let full = 1usize << n;
    let mut dp = vec![Big::zero(); full];
    dp[0] = Big::from_i64(1);
    for mask in 0..full {
        if dp[mask].sign == 0 { continue; }
        let r = (mask as u32).count_ones() as usize;
        if r >= n { continue; }
        for j in 0..n {
            if mask & (1 << j) != 0 { continue; }
            // new inversions = set bits of mask strictly above j
            let above = (mask >> (j + 1)).count_ones();
            let mut term = dp[mask].mul(&mat[r][j]);
            if above & 1 == 1 { term = term.neg(); }
            let nm = mask | (1 << j);
            dp[nm] = dp[nm].add(&term);
        }
    }
    dp[full - 1].clone()
}

// disc of monic quintic c (highest-first, len 6) = det(Sylvester(f, f'))
fn discriminant(c: &[i64]) -> Big {
    let n = 5usize;
    let fp: Vec<i64> = (0..n).map(|i| c[i] * (n - i) as i64).collect(); // derivative highest-first, len 5
    let size = (n - 1) + n; // 9
    let mut m = vec![vec![Big::zero(); size]; size];
    for i in 0..(n - 1) {
        for j in 0..c.len() {
            m[i][i + j] = Big::from_i64(c[j]);
        }
    }
    for i in 0..n {
        for j in 0..fp.len() {
            m[(n - 1) + i][i + j] = Big::from_i64(fp[j]);
        }
    }
    det(&m)
}



// ===== driver =====
fn arr(v: &[Big]) -> String {
    let parts: Vec<String> = v.iter().map(|b| format!("\"{}\"", b.to_string())).collect();
    format!("[{}]", parts.join(", "))
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 3 {
        eprintln!("usage: {} <input> <output>", args[0]);
        process::exit(2);
    }
    let input = fs::read_to_string(&args[1]).unwrap_or_else(|err| { eprintln!("read {}: {}", args[1], err); process::exit(1); });
    let primes = sieve(8000);
    let mut entries: Vec<String> = Vec::new();
    for line in input.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') { continue; }
        let nums: Vec<i64> = line.split_whitespace().filter_map(|t| t.parse::<i64>().ok()).collect();
        if nums.len() != 6 { eprintln!("skip malformed: {}", line); continue; }
        let outc = classify(&nums, &primes);
        let disc = discriminant(&nums).to_string();
        let res = resolvent_pairsum(&nums);
        let polystr: Vec<String> = nums.iter().map(|x| x.to_string()).collect();
        let grpstr = match &outc.group { Some(s) => format!("\"{}\"", s), None => "null".to_string() };
        entries.push(format!(
            "  {{\"polynomial\": [{}], \"irreducible\": {}, \"discriminant\": \"{}\", \"galois_group\": {}, \"solvable_by_radicals\": {}, \"pair_sum_resolvent\": {}}}",
            polystr.join(", "), outc.irreducible, disc, grpstr, outc.solvable, arr(&res)));
    }
    fs::write(&args[2], format!("[\n{}\n]\n", entries.join(",\n"))).unwrap_or_else(|err| { eprintln!("write {}: {}", args[2], err); process::exit(1); });
}
RUST_EOF

cargo build --release --quiet
cargo run --release --quiet -- /app/data/quintics.txt /app/results.json
echo "oracle build + sample run complete"
