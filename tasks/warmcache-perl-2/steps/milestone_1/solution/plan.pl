#!/usr/bin/perl
# Edge-CDN warm-cache planner (current descriptor revision). Reads /app/warmcache.dat and
# writes one JSON file per stage to /app/out/. Usage: perl plan.pl <decode|reconcile|rollup>
#   decode     validate/decode canonical base64 frames -> OBJ prerequisites + HIT weights + invalid
#   reconcile  inner-join OBJ against HIT, assign each object a disposition by precedence
#              (PIN > QUARANTINE > COLD > WARM), topologically order the warmed objects, dangling
#   rollup     group warmed objects by zone with a retention rule, POSIX cksum digest of the block
# All rules are the current revision of /app/docs/chronicle.md. Pure Perl, no shell-out.
use strict;
use warnings;
use MIME::Base64 qw(decode_base64 encode_base64);

my $DAT = "/app/warmcache.dat";
my $OUTDIR = "/app/out";

# ---- policy in force (settled by the chronicle's amendment chain) ----
my $PIN_MARK  = "0";
my %QUAR      = (Q => 1, X => 1);
my $COLD      = 90000;
my %HOT       = (H => 1);
my $RETAIN    = 2;
my %PRIORITY  = (W => 1);

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

sub canon_b64 {
    my ($s) = @_;
    return undef if length($s) == 0 || (length($s) % 4) != 0;
    return undef unless $s =~ /^[A-Za-z0-9+\/]+={0,2}$/;
    my $raw = decode_base64($s);
    return undef if encode_base64($raw, "") ne $s;
    return $raw;
}

sub is_key  { my ($s) = @_; return $s =~ /^[A-Z][A-Z0-9]{1,5}$/ ? 1 : 0; }
sub is_hits { my ($s) = @_; return $s =~ /^(0|[1-9][0-9]{0,8})$/ ? 1 : 0; }
sub is_ascii { my ($s) = @_; return $s =~ /^[\x00-\x7f]*$/ ? 1 : 0; }

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
    for my $raw (split(/\n/, read_dat(), -1)) {
        my $line = $raw; $line =~ s/\r$//;
        next if $line =~ /^\s*$/;
        my @f = split(/ /, $line, -1);
        if (scalar(@f) != 3) {
            my $seq = (@f && $f[0] =~ /^[1-9][0-9]*$/) ? ($f[0] + 0) : -1;
            push @invalid, [$seq, "BAD_FRAME"]; next;
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

sub disposition {
    my ($key, $w) = @_;
    my $zone = substr($key, 0, 1);
    return "PIN" if length($key) >= 2 && substr($key, 1, 1) eq $PIN_MARK;
    return "QUARANTINE" if $QUAR{$zone};
    return "COLD" if $w < $COLD && !$HOT{$zone};
    return "WARM";
}

# ---- stage 2: reconcile ----
sub reconcile_all {
    my ($objs, $hits) = decode_all();
    my @joined = sort { $a cmp $b } grep { exists $hits->{$_} } keys %$objs;
    my %disp = map { $_ => disposition($_, $hits->{$_}) } @joined;
    my @warmed = grep { $disp{$_} eq "PIN" || $disp{$_} eq "WARM" } @joined;
    my %wset = map { $_ => 1 } @warmed;
    my (%adj, %indeg, %rev, @dangling);
    for my $n (@warmed) { $adj{$n} = []; $rev{$n} = []; }
    for my $n (@warmed) {
        for my $d (@{ $objs->{$n} }) {
            if ($wset{$d}) { push @{ $adj{$n} }, $d; }
            else { push @dangling, [$n, $d]; }
        }
    }
    for my $n (@warmed) {
        $indeg{$n} = scalar(@{ $adj{$n} });
        for my $d (@{ $adj{$n} }) { push @{ $rev{$d} }, $n; }
    }
    my @ready = sort { $a cmp $b } grep { $indeg{$_} == 0 } @warmed;
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
    my $resolvable = (scalar(@order) == scalar(@warmed)) ? 1 : 0;
    return (\@joined, \%disp, $resolvable, \@order, \@dangling, $hits);
}

# ---- stage 3: rollup ----
sub rollup_all {
    my ($joined, $disp, $resolvable, $order, $dangling, $hits) = reconcile_all();
    return (undef) unless $resolvable;
    my (%cnt, %wt);
    for my $k (@$joined) {
        next unless $disp->{$k} eq "PIN" || $disp->{$k} eq "WARM";
        my $z = substr($k, 0, 1);
        $cnt{$z}++; $wt{$z} += $hits->{$k};
    }
    my (@zones, $ovc, $ovw, $totc, $totw); $ovc = $ovw = $totc = $totw = 0;
    for my $z (sort keys %cnt) {
        $totc += $cnt{$z}; $totw += $wt{$z};
        if ($cnt{$z} >= $RETAIN || $PRIORITY{$z}) { push @zones, [$z, $cnt{$z}, $wt{$z}]; }
        else { $ovc += $cnt{$z}; $ovw += $wt{$z}; }
    }
    my $block = "";
    for my $r (@zones) { $block .= sprintf("%s %d %d\n", @$r); }
    my $digest = cksum_crc($block);
    return (1, \@zones, $ovc, $ovw, $totc, $totw, $digest);
}

# ---- JSON emit ----
sub jstr { my ($s) = @_; return '"' . $s . '"'; }
sub jlist { return "[" . join(",", @_) . "]"; }

sub emit_decode {
    my ($objs, $hits, $invalid) = decode_all();
    my @ol;
    for my $k (sort { $a cmp $b } keys %$objs) {
        my @ds = map { jstr($_) } @{ $objs->{$k} };
        push @ol, jlist(jstr($k), jlist(@ds));
    }
    my @hl; for my $k (sort { $a cmp $b } keys %$hits) { push @hl, jlist(jstr($k), $hits->{$k}); }
    my @il; for my $e (@$invalid) { push @il, jlist($e->[0], jstr($e->[1])); }
    return '{"objs":' . jlist(@ol) . ',"hits":' . jlist(@hl) . ',"invalid":' . jlist(@il) . "}\n";
}

sub emit_reconcile {
    my ($joined, $disp, $resolvable, $order, $dangling) = reconcile_all();
    my @jl = map { jstr($_) } @$joined;
    my @dl = map { jlist(jstr($_), jstr($disp->{$_})) } @$joined;
    my @pl = map { jstr($_) } @$order;
    my @gl = map { jlist(jstr($_->[0]), jstr($_->[1])) } @$dangling;
    return '{"joined":' . jlist(@jl)
        . ',"disposition":' . jlist(@dl)
        . ',"resolvable":' . ($resolvable ? "true" : "false")
        . ',"plan":' . jlist($resolvable ? @pl : ())
        . ',"dangling":' . jlist(@gl) . "}\n";
}

sub emit_rollup {
    my ($ok, $zones, $ovc, $ovw, $totc, $totw, $digest) = rollup_all();
    return '{"zones":[],"overflow":null,"total":null,"digest":null}' . "\n" unless $ok;
    my @zl = map { jlist(jstr($_->[0]), $_->[1], $_->[2]) } @$zones;
    return '{"zones":' . jlist(@zl)
        . ',"overflow":{"count":' . $ovc . ',"weight":' . $ovw . '}'
        . ',"total":{"count":' . $totc . ',"weight":' . $totw . '}'
        . ',"digest":' . $digest . "}\n";
}

my $stage = $ARGV[0] // "";
my $out;
if    ($stage eq "decode")    { $out = emit_decode(); }
elsif ($stage eq "reconcile") { $out = emit_reconcile(); }
elsif ($stage eq "rollup")    { $out = emit_rollup(); }
else { print STDERR "usage: plan.pl <decode|reconcile|rollup>\n"; exit 2; }
mkdir($OUTDIR) unless -d $OUTDIR;
open(my $ofh, ">", "$OUTDIR/$stage.json") or die "cannot write $OUTDIR/$stage.json: $!";
print $ofh $out;
close($ofh);
