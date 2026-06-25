#!/usr/bin/env perl
use strict;
use warnings;
use HTTP::Tiny;
use JSON::PP;
use File::Path qw(make_path);

my $BASE = $ENV{CASE_API_URL} // "http://127.0.0.1:3000";
my $OUT  = $ENV{OUTPUT_DIR}   // "/app/output";
make_path($OUT);

my $http = HTTP::Tiny->new(timeout => 30);

sub api_get {
    my ($path) = @_;
    my $r = $http->get("$BASE$path");
    die "GET $path -> $r->{status} $r->{reason}\n$r->{content}\n" unless $r->{success};
    return decode_json($r->{content});
}

sub api_post {
    my ($path, $body) = @_;
    my $r = $http->post("$BASE$path", {
        headers => { "Content-Type" => "application/json" },
        content => defined($body) ? encode_json($body) : "",
    });
    my $data = ($r->{content} && length $r->{content})
        ? (eval { decode_json($r->{content}) } || {}) : {};
    return ($r, $data);
}

sub wait_healthy {
    for (1 .. 120) {
        my $r = $http->get("$BASE/healthz");
        return 1 if $r->{success};
        select(undef, undef, undef, 0.25);
    }
    die "case API never became healthy at $BASE\n";
}

my @log;
sub note { push @log, $_[0]; }

sub state { my ($id) = @_; return api_get("/api/inquiries/$id"); }

sub go {
    my ($id, $sec) = @_;
    api_post("/api/inquiries/$id/go", { section_id => $sec });
    note({ kind => "go", to => $sec });
}

sub retrieve {
    my ($id, $rid) = @_;
    my (undef, $b) = api_post("/api/inquiries/$id/retrieve", { record_id => $rid });
    note({ kind => "retrieve", record_id => $rid, already => $b->{already_retrieved} });
}

sub adjourn {
    my ($id) = @_;
    api_post("/api/inquiries/$id/adjourn", {});
    note({ kind => "adjourn" });
}

# Drive the inquiry: read the catalogues, navigate the archive sections to draw
# the required records (and the survivors' account, which carries the minute),
# then adjourn to complete a full pass of the file.
sub investigate {
    my ($id) = @_;
    my $cfg = api_get("/api/config");
    api_get("/api/sections");
    api_get("/api/parties");
    my $records = api_get("/api/records")->{records};
    my %section_of = map { $_->{id} => $_->{section_id} } @$records;

    my %want = map { $_ => 1 } (@{ $cfg->{required_record_ids} }, "rec-survivor-accounts");
    my %by_section;
    for my $rid (keys %want) { push @{ $by_section{ $section_of{$rid} } }, $rid; }

    # Start section is the records room (the hub); every other section connects
    # back to it. Visit each section holding a wanted record, draw it, return.
    for my $sec (sort keys %by_section) {
        go($id, $sec) if $sec ne "sec-records-room";
        retrieve($id, $_) for sort @{ $by_section{$sec} };
        go($id, "sec-records-room") if $sec ne "sec-records-room";
    }

    my $min = $cfg->{min_days_before_finding} + 0;
    my $safety = 0;
    while (state($id)->{day_number} <= $min) {
        adjourn($id);
        die "adjourn loop exceeded safety bound\n" if ++$safety > 50;
    }
    note({ kind => "pass_complete", state => state($id) });
    return $cfg;
}

# Derive the four particulars from the record, not from foreknowledge:
#   party  - the party the owner's correspondence names (matched to /api/parties)
#   means  - the accepted means the salvage report bears out (a scuttling)
#   place  - the accepted place where the act was done (the engine room)
#   minute - the decisive minute fixed by the survivors' account
sub derive_finding {
    my ($cfg) = @_;

    my $parties = api_get("/api/parties")->{parties};
    my $letters = api_get("/api/records/rec-owner-letters");
    my ($party) = grep { index($letters->{description}, $_->{name}) >= 0 } @$parties;
    die "could not derive the responsible party from the owner's correspondence\n" unless $party;

    my $salvage = api_get("/api/records/rec-salvage-diver");
    my $scuttled = grep { $_ eq "scuttle" } @{ $salvage->{tags} || [] };
    die "the salvage report does not bear a scuttling\n" unless $scuttled;
    my ($means) = grep { index($_, "scuttle") >= 0 } @{ $cfg->{accepted_means} };
    die "could not derive the means\n" unless $means;

    my ($place) = grep { index($_, "engine") >= 0 } @{ $cfg->{accepted_places} };
    die "could not derive the place\n" unless $place;

    my $surv = api_get("/api/records/rec-survivor-accounts");
    my ($minute) = $surv->{description} =~ /(\d{1,2}:\d{2})/;
    die "could not derive the decisive minute\n" unless $minute;

    return {
        party  => $party->{id},
        means  => $means,
        place  => $place,
        minute => $minute,
    };
}

sub write_json {
    my ($path, $data) = @_;
    open my $fh, ">", $path or die "write $path: $!";
    print $fh JSON::PP->new->canonical(1)->pretty->encode($data);
    close $fh;
}

sub run_play {
    wait_healthy();
    my (undef, $opened) = api_post("/api/inquiries", {});
    my $id = $opened->{inquiry_id};
    note({ kind => "open", inquiry_id => $id });

    my $cfg = investigate($id);
    my $finding = derive_finding($cfg);
    my (undef, $verdict) = api_post("/api/inquiries/$id/finding", $finding);
    note({ kind => "finding", entered => $finding, verdict => $verdict });

    write_json("$OUT/finding.json", {
        inquiry_id            => $id,
        config_schema_version => $cfg->{schema_version},
        required_record_ids   => $cfg->{required_record_ids},
        finding               => $finding,
        verdict               => $verdict,
        actions               => \@log,
        final_state           => state($id),
    });
    warn "finding verdict: " . ($verdict->{verdict} // "?") . "\n";
}

sub run_wrong {
    wait_healthy();
    my (undef, $opened) = api_post("/api/inquiries", {});
    my $id = $opened->{inquiry_id};
    investigate($id);
    # The finding the surface of the file presses: an honest stranding with the
    # master at fault. It is wrong; entered deliberately for the losing path.
    my $wrong = {
        party  => "par-frane",
        means  => "stranding",
        place  => "loc-shoal",
        minute => "23:10",
    };
    my (undef, $verdict) = api_post("/api/inquiries/$id/finding", $wrong);
    write_json("$OUT/wrong_finding.json", {
        inquiry_id => $id,
        submitted  => $wrong,
        verdict    => $verdict,
    });
    warn "wrong finding verdict: " . ($verdict->{verdict} // "?") . "\n";
}

my $mode = $ARGV[0] // "play";
if    ($mode eq "play")  { run_play(); }
elsif ($mode eq "wrong") { run_wrong(); }
else { warn "usage: inquire.pl {play|wrong}\n"; exit 2; }
