#!/usr/bin/perl
# Edge-CDN warm-cache planner (descriptor format revision 5, "R5"). Reads
# /app/warmcache.dat and writes one JSON file per stage to /app/out/.
# Usage: perl plan.pl <decode|order|digest>
#   decode  validate/decode base64 frames -> OBJ prerequisites + HIT weights + invalid list
#   order   inner-join OBJ against HIT, topologically order (C-locale tie-break), dangling
#   digest  djb2 plan hash + total hit weight + POSIX cksum of the newline-joined order
# All rules are the R5 generation of /app/docs/chronicle.md. Pure Perl, no shell-out.
use strict;
use warnings;
use MIME::Base64 qw(decode_base64 encode_base64);

my $DAT = "/app/warmcache.dat";
my $OUTDIR = "/app/out";

# ---- POSIX cksum CRC (matches the first field of /usr/bin/cksum) ----
my @CKTAB;
for my $n (0 .. 255) {
    my $c = ($n << 24) & 0xFFFFFFFF;
    for (1 .. 8) {
        if ($c & 0x80000000) { $c = (($c << 1) ^ 0x04C11DB7) & 0xFFFFFFFF; }
        else                 { $c = ($c << 1) & 0xFFFFFFFF; }
    }
    $CKTAB[$n] = $c;
}
sub cksum_crc {
    my ($s) = @_;
    my $crc = 0;
    for my $i (0 .. length($s) - 1) {
        my $b = ord(substr($s, $i, 1));
        $crc = ((($crc << 8) & 0xFFFFFFFF) ^ $CKTAB[(($crc >> 24) ^ $b) & 0xFF]) & 0xFFFFFFFF;
    }
    my $n = length($s);
    while ($n > 0) {
        $crc = ((($crc << 8) & 0xFFFFFFFF) ^ $CKTAB[(($crc >> 24) ^ ($n & 0xFF)) & 0xFF]) & 0xFFFFFFFF;
        $n >>= 8;
    }
    return (~$crc) & 0xFFFFFFFF;
}

# canonical RFC-4648 base64 of the payload; returns decoded bytes or undef
sub canon_b64 {
    my ($s) = @_;
    return undef if length($s) == 0 || (length($s) % 4) != 0;
    return undef unless $s =~ /^[A-Za-z0-9+\/]+={0,2}$/;
    my $raw = decode_base64($s);
    return undef if encode_base64($raw, "") ne $s;
    return $raw;
}

sub is_key { my ($s) = @_; return $s =~ /^[A-Z][A-Z0-9]{1,5}$/ ? 1 : 0; }
sub is_hits { my ($s) = @_; return $s =~ /^(0|[1-9][0-9]{0,8})$/ ? 1 : 0; }
sub is_ascii { my ($s) = @_; return $s =~ /^[\x00-\x7f]*$/ ? 1 : 0; }

# parse a decoded record; returns ($kind,$key,$payload_ref,undef) or (undef,undef,undef,$code)
sub parse_record {
    my ($text) = @_;
    my @f = split(/ /, $text, -1);
    return (undef, undef, undef, "BAD_REC") if scalar(@f) != 3;
    my ($kind, $key, $rest) = @f;
    return (undef, undef, undef, "BAD_KIND") if $kind ne "OBJ" && $kind ne "HIT";
    return (undef, undef, undef, "BAD_KEY") unless is_key($key);
    if ($kind eq "OBJ") {
        my @pre = ();
        if ($rest ne "-") {
            @pre = split(/,/, $rest, -1);
            for my $d (@pre) { return (undef, undef, undef, "BAD_PRE") unless is_key($d); }
        }
        return ("OBJ", $key, \@pre, undef);
    }
    return (undef, undef, undef, "BAD_HITS") unless is_hits($rest);
    return ("HIT", $key, ($rest + 0), undef);
}

sub read_dat {
    open(my $fh, "<", $DAT) or return "";
    local $/; my $s = <$fh>; close($fh); return defined($s) ? $s : "";
}

# ---- stage 1: decode ----
sub decode_all {
    my (%objs, %hits, @invalid, %seen_obj, %seen_hit);
    my $text = read_dat();
    for my $raw (split(/\n/, $text, -1)) {
        my $line = $raw; $line =~ s/\r$//;
        next if $line =~ /^\s*$/;
        my @f = split(/ /, $line, -1);
        if (scalar(@f) != 3) {
            my $seq = (@f && $f[0] =~ /^[1-9][0-9]*$/) ? ($f[0] + 0) : -1;
            push @invalid, [$seq, "BAD_FRAME"];
            next;
        }
        my ($seqs, $payload, $crcs) = @f;
        if ($seqs !~ /^[1-9][0-9]*$/) { push @invalid, [-1, "BAD_FRAME"]; next; }
        my $seq = $seqs + 0;
        my $data = canon_b64($payload);
        if (!defined $data) { push @invalid, [$seq, "BAD_B64"]; next; }
        if (!($crcs eq "0" || $crcs =~ /^[1-9][0-9]*$/) || ($crcs + 0) != cksum_crc($data)) {
            push @invalid, [$seq, "BAD_CRC"]; next;
        }
        if (!is_ascii($data)) { push @invalid, [$seq, "BAD_REC"]; next; }
        my ($kind, $key, $pv, $code) = parse_record($data);
        if (defined $code) { push @invalid, [$seq, $code]; next; }
        if ($kind eq "OBJ") {
            if ($seen_obj{$key}) { push @invalid, [$seq, "DUP"]; }
            else { $seen_obj{$key} = 1; $objs{$key} = $pv; }
        } else {
            if ($seen_hit{$key}) { push @invalid, [$seq, "DUP"]; }
            else { $seen_hit{$key} = 1; $hits{$key} = $pv; }
        }
    }
    @invalid = sort { $a->[0] <=> $b->[0] or $a->[1] cmp $b->[1] } @invalid;
    return (\%objs, \%hits, \@invalid);
}

# ---- stage 2: order ----
sub order_all {
    my ($objs, $hits, undef) = decode_all();
    my @joined = sort { $a cmp $b } grep { exists $hits->{$_} } keys %$objs;
    my %jset = map { $_ => 1 } @joined;
    my (%adj, %indeg, %rev, @dangling);
    for my $n (@joined) { $adj{$n} = []; $rev{$n} = []; }
    for my $n (@joined) {
        for my $d (@{ $objs->{$n} }) {
            if ($jset{$d}) { push @{ $adj{$n} }, $d; }
            else { push @dangling, [$n, $d]; }
        }
    }
    for my $n (@joined) {
        $indeg{$n} = scalar(@{ $adj{$n} });
        for my $d (@{ $adj{$n} }) { push @{ $rev{$d} }, $n; }
    }
    my @ready = sort { $a cmp $b } grep { $indeg{$_} == 0 } @joined;
    my @order;
    while (@ready) {
        my $n = shift @ready;
        push @order, $n;
        for my $m (@{ $rev{$n} }) {
            $indeg{$m}--;
            if ($indeg{$m} == 0) { push @ready, $m; @ready = sort { $a cmp $b } @ready; }
        }
    }
    @dangling = sort { $a->[0] cmp $b->[0] or $a->[1] cmp $b->[1] } @dangling;
    my $resolvable = (scalar(@order) == scalar(@joined)) ? 1 : 0;
    return ($resolvable, \@order, \@joined, \@dangling, $hits);
}

# ---- stage 3: digest ----
sub digest_all {
    my ($resolvable, $order, $joined, $dangling, $hits) = order_all();
    return (undef, undef, undef) unless $resolvable;
    my $h = 5381;
    my $hit_sum = 0;
    my $blob = "";
    for my $key (@$order) {
        for my $i (0 .. length($key) - 1) {
            $h = (($h * 33) ^ ord(substr($key, $i, 1))) & 0xFFFFFFFF;
        }
        $hit_sum += $hits->{$key};
        $blob .= $key . "\n";
    }
    my $crc = cksum_crc($blob);
    return ($h, $hit_sum, $crc);
}

# ---- JSON emit (ASCII keys/codes need no escaping) ----
sub jstr { my ($s) = @_; return '"' . $s . '"'; }
sub jlist { return "[" . join(",", @_) . "]"; }

sub emit_decode {
    my ($objs, $hits, $invalid) = decode_all();
    my @ol;
    for my $k (sort { $a cmp $b } keys %$objs) {
        my @ds = map { jstr($_) } @{ $objs->{$k} };
        push @ol, jlist(jstr($k), jlist(@ds));
    }
    my @hl;
    for my $k (sort { $a cmp $b } keys %$hits) { push @hl, jlist(jstr($k), $hits->{$k}); }
    my @il;
    for my $e (@$invalid) { push @il, jlist($e->[0], jstr($e->[1])); }
    return '{"objs":' . jlist(@ol) . ',"hits":' . jlist(@hl) . ',"invalid":' . jlist(@il) . "}\n";
}

sub emit_order {
    my ($resolvable, $order, $joined, $dangling) = order_all();
    my @ol = map { jstr($_) } @$order;
    my @jl = map { jstr($_) } @$joined;
    my @gl = map { jlist(jstr($_->[0]), jstr($_->[1])) } @$dangling;
    return '{"resolvable":' . ($resolvable ? "true" : "false")
        . ',"order":' . jlist($resolvable ? @ol : ())
        . ',"joined":' . jlist(@jl)
        . ',"dangling":' . jlist(@gl) . "}\n";
}

sub emit_digest {
    my ($h, $hit_sum, $crc) = digest_all();
    return '{"plan_hash":null,"hit_sum":null,"order_crc":null}' . "\n" unless defined $h;
    return '{"plan_hash":' . $h . ',"hit_sum":' . $hit_sum . ',"order_crc":' . $crc . "}\n";
}

my $stage = $ARGV[0] // "";
my $out;
if    ($stage eq "decode") { $out = emit_decode(); }
elsif ($stage eq "order")  { $out = emit_order(); }
elsif ($stage eq "digest") { $out = emit_digest(); }
else { print STDERR "usage: plan.pl <decode|order|digest>\n"; exit 2; }
mkdir($OUTDIR) unless -d $OUTDIR;
open(my $ofh, ">", "$OUTDIR/$stage.json") or die "cannot write $OUTDIR/$stage.json: $!";
print $ofh $out;
close($ofh);
