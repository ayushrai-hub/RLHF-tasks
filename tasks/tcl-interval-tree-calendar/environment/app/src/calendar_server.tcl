#!/usr/bin/env tclsh8.6

set ::PORT [expr {[info exists ::env(BIND_PORT)] ? int($::env(BIND_PORT)) : 8080}]
set ::DB   [expr {[info exists ::env(CALENDAR_DB)] ? $::env(CALENDAR_DB) : "/app/data/calendar.db"}]
set ::QLOG "/app/data/query_log.ndjson"

package require sqlite3

proc db_open {} {
    if {![llength [info commands ::cal_db]]} {
        sqlite3 ::cal_db $::DB
        catch {::cal_db eval {PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL}}
    }
}
proc dbq {sql} {
    db_open
    set result {}
    if {[catch {
        ::cal_db eval $sql row {
            set vals {}
            foreach col $row(*) { lappend vals $row($col) }
            lappend result [join $vals \t]
        }
    }]} { return {} }
    return $result
}
proc dbr {sql} {
    set rows [dbq $sql]
    if {$rows eq {}} { return {} }
    return [split [lindex $rows 0] \t]
}
proc dbe {sql} {
    db_open
    catch {::cal_db eval $sql}
}
proc db_insert {sql} {
    db_open
    if {[catch {::cal_db eval $sql} err]} { error $err }
    return [::cal_db last_insert_rowid]
}
proc now_ms {} { clock milliseconds }
proc now_us {} { clock microseconds }

proc jstr {s} {
    set s [string map [list \\ \\\\ \" \\\" \n \\n \r \\r \t \\t] $s]
    return "\"$s\""
}
proc json_str {json key} {
    set q "\""
    set pat "${q}${key}${q}\\s*:\\s*${q}(\[^${q}]*)${q}"
    if {[regexp $pat $json -> v]} { return $v }
    return ""
}
proc json_num {json key} {
    set q "\""
    set pat "${q}${key}${q}\\s*:\\s*(-?\\d+)"
    if {[regexp $pat $json -> v]} { return $v }
    return ""
}
proc extract_metadata {json} {
    set OB [format %c 123]
    set CB [format %c 125]
    set pat "\"metadata\"\\s*:\\s*"
    if {![regexp -indices $pat $json m]} { return "{}" }
    set pos [expr {[lindex $m 1] + 1}]
    set jlen [string length $json]
    while {$pos < $jlen} {
        set c [string index $json $pos]
        if {$c ne " " && $c ne "\t" && $c ne "\n" && $c ne "\r"} break
        incr pos
    }
    if {$pos >= $jlen || [string index $json $pos] ne $OB} { return "{}" }
    set start $pos; set depth 1; incr pos
    while {$pos < $jlen && $depth > 0} {
        set c [string index $json $pos]
        if {$c eq $OB} { incr depth }
        if {$c eq $CB} { incr depth -1 }
        incr pos
    }
    return [string range $json $start [expr {$pos-1}]]
}
proc sq {s} { string map [list ' ''] $s }
proc qs_get {qs key} {
    foreach pair [split $qs &] {
        set eq [string first = $pair]
        if {$eq < 0} continue
        if {[string range $pair 0 [expr {$eq-1}]] eq $key} {
            return [string range $pair [expr {$eq+1}] end]
        }
    }
    return ""
}
proc null_val {v} {
    if {$v eq "" || $v eq "NULL"} { return "NULL" }
    return $v
}
proc update_max_end {nid} {
    set r [dbr "SELECT end_ms,tree_left_id,tree_right_id FROM events WHERE id=$nid"]
    if {$r eq {}} return
    set best [lindex $r 0]; set lid [lindex $r 1]; set rid [lindex $r 2]
    if {$lid ne "" && $lid ne "NULL"} {
        set v [lindex [dbr "SELECT max_end_ms FROM events WHERE id=$lid"] 0]
        if {$v ne "" && $v > $best} { set best $v }
    }
    if {$rid ne "" && $rid ne "NULL"} {
        set v [lindex [dbr "SELECT max_end_ms FROM events WHERE id=$rid"] 0]
        if {$v ne "" && $v > $best} { set best $v }
    }
    dbe "UPDATE events SET max_end_ms=$best WHERE id=$nid"
}
proc propagate_up {nid} {
    set cur $nid
    while {$cur ne "" && $cur ne "NULL"} {
        update_max_end $cur
        set pr [dbr "SELECT tree_parent_id FROM events WHERE id=$cur"]
        if {$pr eq {}} break
        set cur [lindex $pr 0]
        if {$cur eq "NULL"} break
    }
}
proc find_root {} {
    set r [dbr "SELECT id FROM events WHERE tree_parent_id IS NULL LIMIT 1"]
    if {$r eq {}} { return "" }
    return [lindex $r 0]
}
proc insert_event {name start_ms end_ms meta} {
    set now [now_ms]; set sn [sq $name]; set sm [sq $meta]
    set root [find_root]
    set cols "name,start_ms,end_ms,metadata_json,max_end_ms,tree_left_id,tree_right_id,tree_parent_id,created_at_ms"
    if {$root eq ""} {
        return [db_insert "INSERT INTO events ($cols) VALUES ('$sn',$start_ms,$end_ms,'$sm',$end_ms,NULL,NULL,NULL,$now)"]
    }
    set pid $root; set go_left 0
    while 1 {
        set nr [dbr "SELECT id,start_ms,tree_left_id,tree_right_id FROM events WHERE id=$pid"]
        set ns [lindex $nr 1]; set nl [lindex $nr 2]; set nrr [lindex $nr 3]
        if {$start_ms < $ns} {
            set go_left 1
            if {$nl eq "" || $nl eq "NULL"} break
            set pid $nl
        } else {
            set go_left 0
            if {$nrr eq "" || $nrr eq "NULL"} break
            set pid $nrr
        }
    }
    set new_id [db_insert "INSERT INTO events ($cols) VALUES ('$sn',$start_ms,$end_ms,'$sm',$end_ms,NULL,NULL,$pid,$now)"]
    if {$go_left} { dbe "UPDATE events SET tree_left_id=$new_id WHERE id=$pid"
    } else         { dbe "UPDATE events SET tree_right_id=$new_id WHERE id=$pid" }
    propagate_up $pid
    return $new_id
}
proc update_event {eid new_name new_end} {
    set r [dbr "SELECT name,end_ms FROM events WHERE id=$eid"]
    if {$r eq {}} { return 0 }
    set cur_name [lindex $r 0]; set cur_end [lindex $r 1]
    if {$new_name ne "" && $new_name ne $cur_name} {
        set sn [sq $new_name]
        dbe "UPDATE events SET name='$sn' WHERE id=$eid"
    }
    if {$new_end ne "" && $new_end != $cur_end} {
        dbe "UPDATE events SET end_ms=$new_end,max_end_ms=$new_end WHERE id=$eid"
        propagate_up $eid
    }
    return 1
}
proc detach_from_parent {node_id pid repl} {
    if {$pid eq "" || $pid eq "NULL"} return
    set pleft [lindex [dbr "SELECT tree_left_id FROM events WHERE id=$pid"] 0]
    set r [null_val $repl]
    if {$pleft == $node_id} { dbe "UPDATE events SET tree_left_id=$r WHERE id=$pid"
    } else                   { dbe "UPDATE events SET tree_right_id=$r WHERE id=$pid" }
}
proc bst_delete {eid} {
    set nr [dbr "SELECT id,tree_left_id,tree_right_id,tree_parent_id FROM events WHERE id=$eid"]
    if {$nr eq {}} { return 0 }
    set lid [lindex $nr 1]; set rid [lindex $nr 2]; set pid [lindex $nr 3]
    set hl [expr {$lid ne "" && $lid ne "NULL"}]
    set hr [expr {$rid ne "" && $rid ne "NULL"}]
    if {!$hl && !$hr} {
        detach_from_parent $eid $pid ""
        dbe "DELETE FROM events WHERE id=$eid"
        if {$pid ne "" && $pid ne "NULL"} { propagate_up $pid }
    } elseif {!$hl} {
        detach_from_parent $eid $pid $rid
        dbe "UPDATE events SET tree_parent_id=[null_val $pid] WHERE id=$rid"
        dbe "DELETE FROM events WHERE id=$eid"
        if {$pid ne "" && $pid ne "NULL"} { propagate_up $pid } else { update_max_end $rid }
    } elseif {!$hr} {
        detach_from_parent $eid $pid $lid
        dbe "UPDATE events SET tree_parent_id=[null_val $pid] WHERE id=$lid"
        dbe "DELETE FROM events WHERE id=$eid"
        if {$pid ne "" && $pid ne "NULL"} { propagate_up $pid } else { update_max_end $lid }
    } else {
        set succ $rid
        while 1 {
            set sl [lindex [dbr "SELECT tree_left_id FROM events WHERE id=$succ"] 0]
            if {$sl eq "" || $sl eq "NULL"} break
            set succ $sl
        }
        set sr2 [dbr "SELECT tree_right_id,tree_parent_id FROM events WHERE id=$succ"]
        set sright [lindex $sr2 0]; set sparent [lindex $sr2 1]
        if {$sparent != $eid} {
            if {$sright ne "" && $sright ne "NULL"} {
                dbe "UPDATE events SET tree_left_id=$sright WHERE id=$sparent"
                dbe "UPDATE events SET tree_parent_id=$sparent WHERE id=$sright"
            } else {
                dbe "UPDATE events SET tree_left_id=NULL WHERE id=$sparent"
            }
            set np [null_val $pid]
            dbe "UPDATE events SET tree_left_id=$lid,tree_right_id=$rid,tree_parent_id=$np WHERE id=$succ"
            dbe "UPDATE events SET tree_parent_id=$succ WHERE id=$lid"
            dbe "UPDATE events SET tree_parent_id=$succ WHERE id=$rid"
        } else {
            set np [null_val $pid]; set sr_v [null_val $sright]
            dbe "UPDATE events SET tree_left_id=$lid,tree_right_id=$sr_v,tree_parent_id=$np WHERE id=$succ"
            dbe "UPDATE events SET tree_parent_id=$succ WHERE id=$lid"
            if {$sright ne "" && $sright ne "NULL"} {
                dbe "UPDATE events SET tree_parent_id=$succ WHERE id=$sright"
            }
        }
        detach_from_parent $eid $pid $succ
        dbe "DELETE FROM events WHERE id=$eid"
        if {$sparent != $eid} { propagate_up $sparent } else { propagate_up $succ }
    }
    return 1
}
proc stab_query {at} {
    set root [find_root]
    if {$root eq ""} { return {} }
    set results {}; set stack [list $root]
    while {[llength $stack] > 0} {
        set nid [lindex $stack 0]; set stack [lrange $stack 1 end]
        set r [dbr "SELECT id,name,start_ms,end_ms,max_end_ms,tree_left_id,tree_right_id,metadata_json FROM events WHERE id=$nid"]
        if {$r eq {}} continue
        set id [lindex $r 0]; set nm [lindex $r 1]; set s [lindex $r 2]; set e [lindex $r 3]
        set lc [lindex $r 5]; set rc [lindex $r 6]; set meta [lindex $r 7]
        if {$s <= $at && $at <= $e} { lappend results [list $id $nm $s $e $meta] }
        if {$lc ne "" && $lc ne "NULL"} {
            set lm [lindex [dbr "SELECT max_end_ms FROM events WHERE id=$lc"] 0]
            if {$lm ne "" && $lm >= $at} { lappend stack $lc }
        }
        if {$rc ne "" && $rc ne "NULL"} {
            set rm [lindex [dbr "SELECT max_end_ms FROM events WHERE id=$rc"] 0]
            if {$rm ne "" && $rm >= $at} { lappend stack $rc }
        }
    }
    return $results
}
proc overlap_query {qs qe} {
    set root [find_root]
    if {$root eq ""} { return {} }
    set results {}; set stack [list $root]
    while {[llength $stack] > 0} {
        set nid [lindex $stack 0]; set stack [lrange $stack 1 end]
        set r [dbr "SELECT id,name,start_ms,end_ms,max_end_ms,tree_left_id,tree_right_id,metadata_json FROM events WHERE id=$nid"]
        if {$r eq {}} continue
        set id [lindex $r 0]; set nm [lindex $r 1]; set s [lindex $r 2]; set e [lindex $r 3]
        set lc [lindex $r 5]; set rc [lindex $r 6]; set meta [lindex $r 7]
        if {$s <= $qe && $e >= $qs} { lappend results [list $id $nm $s $e $meta] }
        if {$lc ne "" && $lc ne "NULL"} {
            set lm [lindex [dbr "SELECT max_end_ms FROM events WHERE id=$lc"] 0]
            if {$lm ne "" && $lm >= $qs} { lappend stack $lc }
        }
        if {$rc ne "" && $rc ne "NULL" && $s <= $qe} { lappend stack $rc }
    }
    return $results
}
proc evlist_json {evlist} {
    set parts {}
    foreach ev $evlist {
        set id [lindex $ev 0]; set nm [lindex $ev 1]; set s [lindex $ev 2]; set e [lindex $ev 3]
        set meta [lindex $ev 4]
        if {$meta eq ""} { set meta "{}" }
        lappend parts "{\"id\":$id,\"name\":[jstr $nm],\"start_ms\":$s,\"end_ms\":$e,\"metadata\":$meta}"
    }
    return "\[[ join $parts , ]\]"
}
proc gaps_json {gaps} {
    set parts {}
    foreach g $gaps {
        lappend parts "{\"start_ms\":[lindex $g 0],\"end_ms\":[lindex $g 1]}"
    }
    return "\[[join $parts ,]\]"
}
proc density_json {buckets} {
    set parts {}
    foreach b $buckets {
        set bs [lindex $b 0]; set be [lindex $b 1]; set cov [lindex $b 2]
        lappend parts "{\"bucket_start\":$bs,\"bucket_end\":$be,\"busy_ms\":$cov}"
    }
    return "\[[join $parts ,]\]"
}
proc append_qlog {entry} {
    catch {
        set f [open $::QLOG a]
        puts $f $entry
        close $f
    }
}

source /app/src/analytics.tcl

proc send_resp {sock status body} {
    array set msgs {200 OK 201 Created 400 {Bad Request} 404 {Not Found} 501 {Not Implemented}}
    set msg [expr {[info exists msgs($status)] ? $msgs($status) : "Error"}]
    set clen [string length $body]
    set hdr "HTTP/1.0 $status $msg\r\nContent-Type: application/json\r\nContent-Length: $clen\r\nConnection: close\r\n\r\n"
    puts -nonewline $sock $hdr$body
    flush $sock
}
proc read_line {sock} {
    set line ""
    while 1 {
        set c [read $sock 1]
        if {$c eq "" || $c eq "\n"} { break }
        if {$c ne "\r"} { append line $c }
    }
    return $line
}
proc handle_request {sock addr _port} {
    fconfigure $sock -translation binary -buffering none -blocking 1
    set req_line [read_line $sock]
    if {$req_line eq ""} { catch {close $sock}; return }
    set clen 0
    while 1 {
        set hdr_line [read_line $sock]
        if {$hdr_line eq ""} break
        if {[regexp -nocase {^content-length:[[:space:]]*([0-9]+)} $hdr_line -> cl]} {
            set clen [expr {int($cl)}]
        }
    }
    set body ""
    if {$clen > 0} { set body [read $sock $clen] }
    if {![regexp {^([A-Z]+)[[:space:]]+([^[:space:]]+)} $req_line -> method full_path]} {
        catch {close $sock}; return
    }
    set qi [string first ? $full_path]
    if {$qi >= 0} {
        set path [string range $full_path 0 [expr {$qi-1}]]
        set qs   [string range $full_path [expr {$qi+1}] end]
    } else { set path $full_path; set qs "" }

    if {$method eq "GET" && $path eq "/healthz"} {
        send_resp $sock 200 {{"status":"ok"}}

    } elseif {$method eq "POST" && $path eq "/events"} {
        set name [json_str $body "name"]
        set sms  [json_num $body "start_ms"]
        set ems  [json_num $body "end_ms"]
        if {$name eq "" || $sms eq "" || $ems eq ""} {
            send_resp $sock 400 {{"error":"missing_required_fields"}}
        } else {
            set meta [extract_metadata $body]
            if {[catch {set new_id [insert_event $name $sms $ems $meta]} err]} {
                send_resp $sock 400 "{\"error\":\"internal\"}"
            } else {
                set row [dbr "SELECT id,name,start_ms,end_ms,max_end_ms FROM events WHERE id=$new_id"]
                set rid [lindex $row 0]; set rn [lindex $row 1]
                set rs [lindex $row 2]; set re [lindex $row 3]; set rm [lindex $row 4]
                send_resp $sock 201 "{\"id\":$rid,\"name\":[jstr $rn],\"start_ms\":$rs,\"end_ms\":$re,\"max_end_ms\":$rm}"
            }
        }

    } elseif {$method eq "GET" && [regexp {^/events/(\d+)$} $path -> eid]} {
        set row [dbr "SELECT id,name,start_ms,end_ms,max_end_ms,metadata_json FROM events WHERE id=$eid"]
        if {$row eq {}} {
            send_resp $sock 404 {{"error":"not_found"}}
        } else {
            set id [lindex $row 0]; set nm [lindex $row 1]; set s [lindex $row 2]
            set e [lindex $row 3]; set mx [lindex $row 4]; set meta [lindex $row 5]
            if {$meta eq ""} { set meta "{}" }
            send_resp $sock 200 "{\"id\":$id,\"name\":[jstr $nm],\"start_ms\":$s,\"end_ms\":$e,\"max_end_ms\":$mx,\"metadata\":$meta}"
        }

    } elseif {$method eq "PUT" && [regexp {^/events/(\d+)$} $path -> eid]} {
        set new_name [json_str $body "name"]
        set new_end  [json_num $body "end_ms"]
        if {$new_name eq "" && $new_end eq ""} {
            send_resp $sock 400 {{"error":"no_fields_provided"}}
        } else {
            set ex [lindex [dbr "SELECT id FROM events WHERE id=$eid"] 0]
            if {$ex eq "" || $ex eq "NULL"} {
                send_resp $sock 404 {{"error":"not_found"}}
            } else {
                update_event $eid $new_name $new_end
                set row [dbr "SELECT id,name,start_ms,end_ms,max_end_ms,metadata_json FROM events WHERE id=$eid"]
                set id [lindex $row 0]; set nm [lindex $row 1]; set s [lindex $row 2]
                set e [lindex $row 3]; set mx [lindex $row 4]; set meta [lindex $row 5]
                if {$meta eq ""} { set meta "{}" }
                send_resp $sock 200 "{\"id\":$id,\"name\":[jstr $nm],\"start_ms\":$s,\"end_ms\":$e,\"max_end_ms\":$mx,\"metadata\":$meta}"
            }
        }

    } elseif {$method eq "GET" && $path eq "/stab"} {
        set at [qs_get $qs "at"]
        if {$at eq "" || ![string is integer -strict $at]} {
            send_resp $sock 400 {{"error":"missing_at"}}
        } else {
            set t0 [now_us]
            set evlist [stab_query $at]
            set dur [expr {[now_us] - $t0}]
            set cnt [llength $evlist]; set ts [now_ms]
            dbe "INSERT INTO stab_log (at_ms,result_count,duration_us,ts_ms) VALUES ($at,$cnt,$dur,$ts)"
            append_qlog "{\"query_type\":\"stab\",\"param_ms\":$at,\"result_count\":$cnt,\"duration_us\":$dur,\"ts_ms\":$ts}"
            send_resp $sock 200 "{\"at\":$at,\"events\":[evlist_json $evlist]}"
        }

    } elseif {$method eq "GET" && $path eq "/overlap"} {
        set qs_s [qs_get $qs "start"]; set qs_e [qs_get $qs "end"]
        if {$qs_s eq "" || $qs_e eq ""} {
            send_resp $sock 400 {{"error":"missing_params"}}
        } else {
            set t0 [now_us]
            set evlist [overlap_query $qs_s $qs_e]
            set dur [expr {[now_us] - $t0}]
            set cnt [llength $evlist]; set ts [now_ms]
            dbe "INSERT INTO overlap_log (start_ms,end_ms,result_count,duration_us,ts_ms) VALUES ($qs_s,$qs_e,$cnt,$dur,$ts)"
            append_qlog "{\"query_type\":\"overlap\",\"param_start_ms\":$qs_s,\"param_end_ms\":$qs_e,\"result_count\":$cnt,\"duration_us\":$dur,\"ts_ms\":$ts}"
            send_resp $sock 200 "{\"start\":$qs_s,\"end\":$qs_e,\"events\":[evlist_json $evlist]}"
        }

    } elseif {$method eq "DELETE" && [string match /events/* $path]} {
        set eid [string range $path 8 end]
        if {![string is integer -strict $eid]} {
            send_resp $sock 400 {{"error":"invalid_id"}}
        } else {
            set ex [lindex [dbr "SELECT id FROM events WHERE id=$eid"] 0]
            if {$ex eq "" || $ex eq "NULL"} {
                send_resp $sock 404 {{"error":"not_found"}}
            } else {
                bst_delete $eid
                send_resp $sock 200 "{\"id\":$eid,\"deleted\":true}"
            }
        }

    } elseif {$method eq "GET" && $path eq "/stats"} {
        set total [lindex [dbr "SELECT COUNT(*) FROM events"] 0]
        if {$total eq "" || $total == 0} {
            send_resp $sock 200 {{"total_events":0,"tree_depth":0,"overlapping_pairs":0,"leaf_count":0,"min_start_ms":0}}
        } else {
            set d_sql "WITH RECURSIVE d(id,lv) AS (SELECT id,1 FROM events WHERE tree_parent_id IS NULL UNION ALL SELECT e.id,d.lv+1 FROM events e JOIN d ON e.tree_parent_id=d.id) SELECT COALESCE(MAX(lv),0) FROM d"
            set p_sql "SELECT COUNT(*) FROM events a JOIN events b ON a.id < b.id WHERE a.start_ms <= b.end_ms AND b.start_ms <= a.end_ms"
            set l_sql "SELECT COUNT(*) FROM events WHERE tree_left_id IS NULL AND tree_right_id IS NULL"
            set m_sql "SELECT MIN(start_ms) FROM events"
            set depth  [lindex [dbr $d_sql] 0]
            set pairs  [lindex [dbr $p_sql] 0]
            set leaves [lindex [dbr $l_sql] 0]
            set min_s  [lindex [dbr $m_sql] 0]
            if {$depth  eq ""} { set depth  0 }
            if {$pairs  eq ""} { set pairs  0 }
            if {$leaves eq ""} { set leaves 0 }
            if {$min_s  eq ""} { set min_s  0 }
            send_resp $sock 200 "{\"total_events\":$total,\"tree_depth\":$depth,\"overlapping_pairs\":$pairs,\"leaf_count\":$leaves,\"min_start_ms\":$min_s}"
        }

    } elseif {$method eq "GET" && $path eq "/peak"} {
        set ps [qs_get $qs "start"]; set pe [qs_get $qs "end"]
        if {![string is integer -strict $ps] || ![string is integer -strict $pe] || $ps > $pe} {
            send_resp $sock 400 {{"error":"invalid_params"}}
        } else {
            if {[catch {set pk [peak_concurrency $ps $pe]} err]} {
                send_resp $sock 501 {{"error":"not_implemented"}}
            } else {
                set mc [lindex $pk 0]; set at [lindex $pk 1]; set pdur [lindex $pk 2]
                set ids [lrange $pk 3 end]
                set ids_json "\[[join $ids ,]\]"
                send_resp $sock 200 "{\"start\":$ps,\"end\":$pe,\"max_concurrency\":$mc,\"at_ms\":$at,\"peak_duration_ms\":$pdur,\"events_at_peak\":$ids_json}"
            }
        }

    } elseif {$method eq "GET" && $path eq "/schedule"} {
        set ps [qs_get $qs "start"]; set pe [qs_get $qs "end"]
        if {![string is integer -strict $ps] || ![string is integer -strict $pe] || $ps > $pe} {
            send_resp $sock 400 {{"error":"invalid_params"}}
        } else {
            if {[catch {set res [max_non_overlapping $ps $pe]} err]} {
                send_resp $sock 501 {{"error":"not_implemented"}}
            } else {
                set k [lindex $res 0]; set cov [lindex $res 1]
                set ids [lrange $res 2 end]
                set ids_json "\[[join $ids ,]\]"
                send_resp $sock 200 "{\"start\":$ps,\"end\":$pe,\"max_non_overlapping\":$k,\"covered_ms\":$cov,\"selected_ids\":$ids_json}"
            }
        }

    } elseif {$method eq "GET" && $path eq "/gaps"} {
        set ps [qs_get $qs "start"]; set pe [qs_get $qs "end"]
        if {![string is integer -strict $ps] || ![string is integer -strict $pe] || $ps > $pe} {
            send_resp $sock 400 {{"error":"invalid_params"}}
        } else {
            if {[catch {set g [compute_gaps $ps $pe]} err]} {
                send_resp $sock 501 {{"error":"not_implemented"}}
            } else {
                send_resp $sock 200 "{\"start\":$ps,\"end\":$pe,\"gaps\":[gaps_json $g]}"
            }
        }

    } elseif {$method eq "GET" && $path eq "/coverage"} {
        set ps [qs_get $qs "start"]; set pe [qs_get $qs "end"]
        if {![string is integer -strict $ps] || ![string is integer -strict $pe] || $ps > $pe} {
            send_resp $sock 400 {{"error":"invalid_params"}}
        } else {
            if {[catch {set cov [compute_coverage $ps $pe]} err]} {
                send_resp $sock 501 {{"error":"not_implemented"}}
            } else {
                set win [expr {$pe - $ps + 1}]
                set free [expr {$win - $cov}]
                send_resp $sock 200 "{\"start\":$ps,\"end\":$pe,\"covered_ms\":$cov,\"free_ms\":$free}"
            }
        }

    } elseif {$method eq "GET" && $path eq "/longest_gap"} {
        set ps [qs_get $qs "start"]; set pe [qs_get $qs "end"]
        if {![string is integer -strict $ps] || ![string is integer -strict $pe] || $ps > $pe} {
            send_resp $sock 400 {{"error":"invalid_params"}}
        } else {
            if {[catch {set g [longest_gap_in $ps $pe]} err]} {
                send_resp $sock 501 {{"error":"not_implemented"}}
            } else {
                if {$g eq {}} {
                    send_resp $sock 200 "{\"start\":$ps,\"end\":$pe,\"gap\":null}"
                } else {
                    set gs [lindex $g 0]; set ge [lindex $g 1]
                    set dur [expr {$ge - $gs + 1}]
                    send_resp $sock 200 "{\"start\":$ps,\"end\":$pe,\"gap\":{\"start_ms\":$gs,\"end_ms\":$ge,\"duration_ms\":$dur}}"
                }
            }
        }

    } elseif {$method eq "GET" && $path eq "/density"} {
        set ps [qs_get $qs "start"]; set pe [qs_get $qs "end"]; set pb [qs_get $qs "bucket_ms"]
        if {![string is integer -strict $ps] || ![string is integer -strict $pe] || \
            ![string is integer -strict $pb] || $ps > $pe || $pb < 1} {
            send_resp $sock 400 {{"error":"invalid_params"}}
        } else {
            if {[catch {set d [compute_density $ps $pe $pb]} err]} {
                send_resp $sock 501 {{"error":"not_implemented"}}
            } else {
                send_resp $sock 200 "{\"start\":$ps,\"end\":$pe,\"bucket_ms\":$pb,\"buckets\":[density_json $d]}"
            }
        }

    } elseif {$method eq "GET" && $path eq "/timeline"} {
        set ps [qs_get $qs "start"]; set pe [qs_get $qs "end"]; set pr [qs_get $qs "resolution_ms"]
        if {![string is integer -strict $ps] || ![string is integer -strict $pe] || \
            ![string is integer -strict $pr] || $ps > $pe || $pr < 1} {
            send_resp $sock 400 {{"error":"invalid_params"}}
        } else {
            if {[catch {set slots [compute_timeline $ps $pe $pr]} err]} {
                send_resp $sock 501 {{"error":"not_implemented"}}
            } else {
                set parts {}
                foreach sl $slots {
                    set ss [lindex $sl 0]; set se [lindex $sl 1]; set pc [lindex $sl 2]
                    lappend parts "{\"slot_start\":$ss,\"slot_end\":$se,\"peak_concurrency\":$pc}"
                }
                set slots_json "\[[join $parts ,]\]"
                send_resp $sock 200 "{\"start\":$ps,\"end\":$pe,\"resolution_ms\":$pr,\"slots\":$slots_json}"
            }
        }

    } elseif {$method eq "GET" && $path eq "/conflicts"} {
        set ps [qs_get $qs "start"]; set pe [qs_get $qs "end"]; set pt [qs_get $qs "threshold"]
        if {![string is integer -strict $ps] || ![string is integer -strict $pe] || \
            ![string is integer -strict $pt] || $ps > $pe || $pt < 0} {
            send_resp $sock 400 {{"error":"invalid_params"}}
        } else {
            if {[catch {set evlist [find_conflicts $ps $pe $pt]} err]} {
                send_resp $sock 501 {{"error":"not_implemented"}}
            } else {
                set parts {}
                foreach ev $evlist {
                    set id [lindex $ev 0]; set nm [lindex $ev 1]; set s [lindex $ev 2]; set e [lindex $ev 3]
                    lappend parts "{\"id\":$id,\"name\":[jstr $nm],\"start_ms\":$s,\"end_ms\":$e}"
                }
                set evlist_json "\[[join $parts ,]\]"
                send_resp $sock 200 "{\"start\":$ps,\"end\":$pe,\"threshold\":$pt,\"conflicting_events\":$evlist_json}"
            }
        }

    } elseif {$method eq "GET" && $path eq "/heatmap"} {
        set ps [qs_get $qs "start"]; set pe [qs_get $qs "end"]; set pr [qs_get $qs "resolution_ms"]
        if {![string is integer -strict $ps] || ![string is integer -strict $pe] || \
            ![string is integer -strict $pr] || $ps > $pe || $pr < 1} {
            send_resp $sock 400 {{"error":"invalid_params"}}
        } else {
            if {[catch {set slots [compute_heatmap $ps $pe $pr]} err]} {
                send_resp $sock 501 {{"error":"not_implemented"}}
            } else {
                set parts {}
                foreach sl $slots {
                    set ss [lindex $sl 0]; set se [lindex $sl 1]
                    set hlist [lindex $sl 2]; set mean [lindex $sl 3]
                    set hjson "\[[join $hlist ,]\]"
                    lappend parts "{\"slot_start\":$ss,\"slot_end\":$se,\"histogram\":$hjson,\"mean_concurrency\":$mean}"
                }
                set slots_json "\[[join $parts ,]\]"
                send_resp $sock 200 "{\"start\":$ps,\"end\":$pe,\"resolution_ms\":$pr,\"slots\":$slots_json}"
            }
        }

    } elseif {$method eq "GET" && $path eq "/merge"} {
        set ps [qs_get $qs "start"]; set pe [qs_get $qs "end"]
        if {![string is integer -strict $ps] || ![string is integer -strict $pe] || $ps > $pe} {
            send_resp $sock 400 {{"error":"invalid_params"}}
        } else {
            if {[catch {set merged [compute_merged $ps $pe]} err]} {
                send_resp $sock 501 {{"error":"not_implemented"}}
            } else {
                set cov 0; set parts {}
                foreach iv $merged {
                    set s [lindex $iv 0]; set e [lindex $iv 1]
                    incr cov [expr {$e - $s + 1}]
                    lappend parts "{\"start_ms\":$s,\"end_ms\":$e}"
                }
                set merged_json "\[[join $parts ,]\]"
                send_resp $sock 200 "{\"start\":$ps,\"end\":$pe,\"merged_intervals\":$merged_json,\"covered_ms\":$cov}"
            }
        }

    } elseif {$method eq "GET" && $path eq "/event_concurrency"} {
        set ps [qs_get $qs "start"]; set pe [qs_get $qs "end"]
        if {![string is integer -strict $ps] || ![string is integer -strict $pe] || $ps > $pe} {
            send_resp $sock 400 {{"error":"invalid_params"}}
        } else {
            if {[catch {set evlist [event_concurrency $ps $pe]} err]} {
                send_resp $sock 501 {{"error":"not_implemented"}}
            } else {
                set parts {}
                foreach ev $evlist {
                    set id [lindex $ev 0]; set nm [lindex $ev 1]; set s [lindex $ev 2]
                    set e [lindex $ev 3]; set d [lindex $ev 4]
                    lappend parts "{\"id\":$id,\"name\":[jstr $nm],\"start_ms\":$s,\"end_ms\":$e,\"max_depth\":$d}"
                }
                set evlist_json "\[[join $parts ,]\]"
                send_resp $sock 200 "{\"start\":$ps,\"end\":$pe,\"events\":$evlist_json}"
            }
        }

    } elseif {$method eq "GET" && $path eq "/free_slots"} {
        set ps [qs_get $qs "start"]; set pe [qs_get $qs "end"]; set pm [qs_get $qs "min_duration_ms"]
        if {![string is integer -strict $ps] || ![string is integer -strict $pe] || \
            ![string is integer -strict $pm] || $ps > $pe || $pm < 1} {
            send_resp $sock 400 {{"error":"invalid_params"}}
        } else {
            if {[catch {set fslots [free_slots_min $ps $pe $pm]} err]} {
                send_resp $sock 501 {{"error":"not_implemented"}}
            } else {
                set parts {}
                foreach sl $fslots {
                    set gs [lindex $sl 0]; set ge [lindex $sl 1]; set dur [lindex $sl 2]
                    lappend parts "{\"start_ms\":$gs,\"end_ms\":$ge,\"duration_ms\":$dur}"
                }
                set slots_json "\[[join $parts ,]\]"
                send_resp $sock 200 "{\"start\":$ps,\"end\":$pe,\"min_duration_ms\":$pm,\"free_slots\":$slots_json}"
            }
        }

    } elseif {$method eq "GET" && $path eq "/weighted_schedule"} {
        set ps [qs_get $qs "start"]; set pe [qs_get $qs "end"]
        if {![string is integer -strict $ps] || ![string is integer -strict $pe] || $ps > $pe} {
            send_resp $sock 400 {{"error":"invalid_params"}}
        } else {
            if {[catch {set res [weighted_schedule $ps $pe]} err]} {
                send_resp $sock 501 {{"error":"not_implemented"}}
            } else {
                set mw [lindex $res 0]; set cov [lindex $res 1]
                set ids [lrange $res 2 end]
                set ids_json "\[[join $ids ,]\]"
                send_resp $sock 200 "{\"start\":$ps,\"end\":$pe,\"max_weight\":$mw,\"selected_ids\":$ids_json,\"covered_ms\":$cov}"
            }
        }

    } elseif {$method eq "GET" && $path eq "/coloring"} {
        set ps [qs_get $qs "start"]; set pe [qs_get $qs "end"]
        if {![string is integer -strict $ps] || ![string is integer -strict $pe] || $ps > $pe} {
            send_resp $sock 400 {{"error":"invalid_params"}}
        } else {
            if {[catch {set res [compute_coloring $ps $pe]} err]} {
                send_resp $sock 501 {{"error":"not_implemented"}}
            } else {
                set nc [lindex $res 0]
                set assigns [lrange $res 1 end]
                set parts {}
                foreach a $assigns {
                    set aid [lindex $a 0]; set col [lindex $a 1]
                    lappend parts "{\"id\":$aid,\"color\":$col}"
                }
                set asgn_json "\[[join $parts ,]\]"
                send_resp $sock 200 "{\"start\":$ps,\"end\":$pe,\"num_colors\":$nc,\"assignments\":$asgn_json}"
            }
        }

    } elseif {$method eq "GET" && $path eq "/concurrency_runs"} {
        set ps [qs_get $qs "start"]; set pe [qs_get $qs "end"]
        if {![string is integer -strict $ps] || ![string is integer -strict $pe] || $ps > $pe} {
            send_resp $sock 400 {{"error":"invalid_params"}}
        } else {
            if {[catch {set res [compute_concurrency_runs $ps $pe]} err]} {
                send_resp $sock 501 {{"error":"not_implemented"}}
            } else {
                set parts {}
                foreach r $res {
                    set rs [lindex $r 0]; set re [lindex $r 1]; set rc [lindex $r 2]
                    lappend parts "{\"start_ms\":$rs,\"end_ms\":$re,\"concurrency\":$rc}"
                }
                set runs_json "\[[join $parts ,]\]"
                send_resp $sock 200 "{\"start\":$ps,\"end\":$pe,\"runs\":$runs_json}"
            }
        }

    } elseif {$method eq "GET" && $path eq "/interval_cover"} {
        set ps [qs_get $qs "start"]; set pe [qs_get $qs "end"]; set pt [qs_get $qs "target_ms"]
        if {![string is integer -strict $ps] || ![string is integer -strict $pe] || \
            ![string is integer -strict $pt] || $ps > $pe || $pt < 1} {
            send_resp $sock 400 {{"error":"invalid_params"}}
        } else {
            if {[catch {set res [interval_cover $ps $pe $pt]} err]} {
                send_resp $sock 501 {{"error":"not_implemented"}}
            } else {
                set mn [lindex $res 0]
                set ids [lindex $res 1]
                set ac [lindex $res 2]
                set ids_json "\[[join $ids ,]\]"
                if {$mn eq "null"} {
                    send_resp $sock 200 "{\"start\":$ps,\"end\":$pe,\"target_ms\":$pt,\"min_events\":null,\"selected_ids\":$ids_json,\"achieved_coverage\":$ac}"
                } else {
                    send_resp $sock 200 "{\"start\":$ps,\"end\":$pe,\"target_ms\":$pt,\"min_events\":$mn,\"selected_ids\":$ids_json,\"achieved_coverage\":$ac}"
                }
            }
        }

    } elseif {$method eq "GET" && $path eq "/earliest_available"} {
        set pa [qs_get $qs "after"]; set pd [qs_get $qs "duration_ms"]
        if {![string is integer -strict $pa] || ![string is integer -strict $pd] || $pd < 1} {
            send_resp $sock 400 {{"error":"invalid_params"}}
        } else {
            if {[catch {set res [earliest_available $pa $pd]} err]} {
                send_resp $sock 501 {{"error":"not_implemented"}}
            } else {
                set ss [lindex $res 0]; set se [lindex $res 1]
                send_resp $sock 200 "{\"after\":$pa,\"duration_ms\":$pd,\"slot_start\":$ss,\"slot_end\":$se}"
            }
        }

    } elseif {$method eq "GET" && $path eq "/room_schedule"} {
        set ps [qs_get $qs "start"]; set pe [qs_get $qs "end"]; set pr [qs_get $qs "rooms"]
        if {![string is integer -strict $ps] || ![string is integer -strict $pe] || \
            ![string is integer -strict $pr] || $ps > $pe || $pr < 1} {
            send_resp $sock 400 {{"error":"invalid_params"}}
        } else {
            if {[catch {set res [room_schedule $ps $pe $pr]} err]} {
                send_resp $sock 501 {{"error":"not_implemented"}}
            } else {
                set ms [lindex $res 0]
                set pairs [lrange $res 1 end]
                set parts {}
                foreach p $pairs {
                    set aid [lindex $p 0]; set room [lindex $p 1]
                    lappend parts "{\"id\":$aid,\"room\":$room}"
                }
                set asgn_json "\[[join $parts ,]\]"
                send_resp $sock 200 "{\"start\":$ps,\"end\":$pe,\"rooms\":$pr,\"max_scheduled\":$ms,\"assignments\":$asgn_json}"
            }
        }

    } elseif {$method eq "GET" && $path eq "/overlap_components"} {
        set ps [qs_get $qs "start"]; set pe [qs_get $qs "end"]
        if {![string is integer -strict $ps] || ![string is integer -strict $pe] || $ps > $pe} {
            send_resp $sock 400 {{"error":"invalid_params"}}
        } else {
            if {[catch {set res [overlap_components $ps $pe]} err]} {
                send_resp $sock 501 {{"error":"not_implemented"}}
            } else {
                set parts {}
                set cid 0
                foreach c $res {
                    set mn [lindex $c 0]; set mx [lindex $c 1]
                    set ids [lrange $c 2 end]
                    set ids_json "\[[join $ids ,]\]"
                    lappend parts "{\"component_id\":$cid,\"event_ids\":$ids_json,\"min_start_ms\":$mn,\"max_end_ms\":$mx}"
                    incr cid
                }
                set comps_json "\[[join $parts ,]\]"
                send_resp $sock 200 "{\"start\":$ps,\"end\":$pe,\"components\":$comps_json}"
            }
        }

    } elseif {$method eq "GET" && $path eq "/depth_profile"} {
        set ps [qs_get $qs "start"]; set pe [qs_get $qs "end"]
        if {![string is integer -strict $ps] || ![string is integer -strict $pe] || $ps > $pe} {
            send_resp $sock 400 {{"error":"invalid_params"}}
        } else {
            if {[catch {set res [compute_depth_profile $ps $pe]} err]} {
                send_resp $sock 501 {{"error":"not_implemented"}}
            } else {
                set max_d [lindex $res 0]
                set total_ms [lindex $res 1]
                set parts {}
                for {set d 0} {$d <= $max_d} {incr d} {
                    set dms [lindex $res [expr {$d + 2}]]
                    lappend parts "{\"depth\":$d,\"total_ms\":$dms}"
                }
                set prof_json "\[[join $parts ,]\]"
                send_resp $sock 200 "{\"start\":$ps,\"end\":$pe,\"total_ms\":$total_ms,\"max_depth\":$max_d,\"profile\":$prof_json}"
            }
        }

    } elseif {$method eq "GET" && $path eq "/window_stats"} {
        set ps [qs_get $qs "start"]; set pe [qs_get $qs "end"]
        if {![string is integer -strict $ps] || ![string is integer -strict $pe] || $ps > $pe} {
            send_resp $sock 400 {{"error":"invalid_params"}}
        } else {
            if {[catch {set res [compute_window_stats $ps $pe]} err]} {
                send_resp $sock 501 {{"error":"not_implemented"}}
            } else {
                set total_ms  [lindex $res 0]
                set covered   [lindex $res 1]
                set max_d     [lindex $res 2]
                set mean_d    [lindex $res 3]
                set var_d     [lindex $res 4]
                set p50       [lindex $res 5]
                send_resp $sock 200 "{\"start\":$ps,\"end\":$pe,\"total_ms\":$total_ms,\"covered_ms\":$covered,\"max_depth\":$max_d,\"mean_depth\":$mean_d,\"variance_depth\":$var_d,\"p50_depth\":$p50}"
            }
        }

    } else {
        send_resp $sock 404 {{"error":"not_found"}}
    }
    catch {close $sock}
}

file mkdir /app/run
set pidf [open /app/run/server.pid w]
puts $pidf [pid]
close $pidf
set server [socket -server handle_request $::PORT]
puts "calendar_server listening on :$::PORT"
flush stdout
vwait forever
