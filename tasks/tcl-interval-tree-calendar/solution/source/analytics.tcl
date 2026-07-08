# Analytics module — oracle implementation.

proc read_events_se {} {
    set out {}
    foreach line [dbq "SELECT id,start_ms,end_ms FROM events"] {
        set f [split $line \t]
        if {[llength $f] < 3} continue
        lappend out [list [lindex $f 0] [lindex $f 1] [lindex $f 2]]
    }
    return $out
}

# §8: returns {max_concurrency at_ms peak_duration_ms id1 id2 ...}
proc peak_concurrency {S E} {
    set evs [read_events_se]
    set cands [list $S]
    foreach ev $evs {
        set s [lindex $ev 1]
        if {$s > $S && $s <= $E} { lappend cands $s }
    }
    set cands [lsort -integer -unique $cands]
    set best 0; set bestt $S; set seen 0
    foreach t $cands {
        set c 0
        foreach ev $evs {
            set s [lindex $ev 1]; set e [lindex $ev 2]
            if {$s <= $t && $t <= $e} { incr c }
        }
        if {!$seen || $c > $best} { set best $c; set bestt $t; set seen 1 }
    }
    # peak_duration_ms via change-point sweep over [S, E]
    set cp [list $S]
    foreach ev $evs {
        set s [lindex $ev 1]; set e [lindex $ev 2]
        if {$s > $S && $s <= $E} { lappend cp $s }
        set ep1 [expr {$e + 1}]
        if {$ep1 > $S && $ep1 <= $E} { lappend cp $ep1 }
    }
    lappend cp [expr {$E + 1}]
    set cp [lsort -integer -unique $cp]
    set pdur 0
    for {set i 0} {$i < [llength $cp] - 1} {incr i} {
        set t [lindex $cp $i]
        set nt [lindex $cp [expr {$i+1}]]
        set c 0
        foreach ev $evs {
            set s [lindex $ev 1]; set e [lindex $ev 2]
            if {$s <= $t && $t <= $e} { incr c }
        }
        if {$c == $best} { incr pdur [expr {$nt - $t}] }
    }
    set ids {}
    foreach ev $evs {
        set id [lindex $ev 0]; set s [lindex $ev 1]; set e [lindex $ev 2]
        if {$s <= $bestt && $bestt <= $e} { lappend ids $id }
    }
    set ids [lsort -integer $ids]
    return [concat [list $best $bestt $pdur] $ids]
}

# §9: returns {count covered_ms id1 id2 ...}
proc max_non_overlapping {S E} {
    set count 0; set last 0; set have 0; set ids {}; set covered 0
    foreach line [dbq "SELECT id,start_ms,end_ms FROM events WHERE start_ms>=$S AND end_ms<=$E ORDER BY end_ms ASC, start_ms ASC, id ASC"] {
        set f [split $line \t]
        if {[llength $f] < 3} continue
        set id [lindex $f 0]; set s [lindex $f 1]; set e [lindex $f 2]
        if {!$have || $s > $last} {
            incr count
            incr covered [expr {$e - $s + 1}]
            set last $e; set have 1
            lappend ids $id
        }
    }
    return [concat [list $count $covered] $ids]
}

proc compute_gaps {S E} {
    set busy {}
    foreach line [dbq "SELECT start_ms,end_ms FROM events WHERE start_ms<=$E AND end_ms>=$S"] {
        set f [split $line \t]
        if {[llength $f] < 2} continue
        set s [lindex $f 0]; set e [lindex $f 1]
        if {$s < $S} { set s $S }
        if {$e > $E} { set e $E }
        lappend busy [list $s $e]
    }
    set merged {}
    foreach iv [lsort -integer -index 0 $busy] {
        set s [lindex $iv 0]; set e [lindex $iv 1]
        if {[llength $merged] == 0} {
            lappend merged [list $s $e]
        } else {
            set li [lindex $merged end]
            set ls [lindex $li 0]; set le [lindex $li 1]
            if {$s <= $le + 1} {
                if {$e > $le} { lset merged end [list $ls $e] }
            } else {
                lappend merged [list $s $e]
            }
        }
    }
    set gaps {}; set cur $S
    foreach iv $merged {
        set s [lindex $iv 0]; set e [lindex $iv 1]
        if {$s > $cur} { lappend gaps [list $cur [expr {$s-1}]] }
        if {$e + 1 > $cur} { set cur [expr {$e+1}] }
    }
    if {$cur <= $E} { lappend gaps [list $cur $E] }
    return $gaps
}

proc compute_coverage {S E} {
    set busy {}
    foreach line [dbq "SELECT start_ms,end_ms FROM events WHERE start_ms<=$E AND end_ms>=$S"] {
        set f [split $line \t]
        if {[llength $f] < 2} continue
        set s [lindex $f 0]; set e [lindex $f 1]
        if {$s < $S} { set s $S }
        if {$e > $E} { set e $E }
        lappend busy [list $s $e]
    }
    set merged {}
    foreach iv [lsort -integer -index 0 $busy] {
        set s [lindex $iv 0]; set e [lindex $iv 1]
        if {[llength $merged] == 0} {
            lappend merged [list $s $e]
        } else {
            set li [lindex $merged end]
            set ls [lindex $li 0]; set le [lindex $li 1]
            if {$s <= $le} {
                if {$e > $le} { lset merged end [list $ls $e] }
            } else {
                lappend merged [list $s $e]
            }
        }
    }
    set covered 0
    foreach iv $merged { incr covered [expr {[lindex $iv 1] - [lindex $iv 0] + 1}] }
    return $covered
}

proc longest_gap_in {S E} {
    set gaps [compute_gaps $S $E]
    if {[llength $gaps] == 0} { return {} }
    set best {}; set best_len -1
    foreach g $gaps {
        set gs [lindex $g 0]; set ge [lindex $g 1]
        set l [expr {$ge - $gs + 1}]
        if {$l > $best_len} { set best_len $l; set best $g }
    }
    return $best
}

proc compute_density {S E B} {
    set result {}
    set bs $S
    while {$bs <= $E} {
        set be [expr {min($bs + $B - 1, $E)}]
        set covered [compute_coverage $bs $be]
        lappend result [list $bs $be $covered]
        set bs [expr {$bs + $B}]
    }
    return $result
}

proc compute_timeline {S E R} {
    set evs [read_events_se]
    set result {}
    set bs $S
    while {$bs <= $E} {
        set be [expr {min($bs + $R - 1, $E)}]
        set cands [list $bs]
        foreach ev $evs {
            set s [lindex $ev 1]
            if {$s > $bs && $s <= $be} { lappend cands $s }
        }
        set cands [lsort -integer -unique $cands]
        set best 0
        foreach t $cands {
            set c 0
            foreach ev $evs {
                set s [lindex $ev 1]; set e [lindex $ev 2]
                if {$s <= $t && $t <= $e} { incr c }
            }
            if {$c > $best} { set best $c }
        }
        lappend result [list $bs $be $best]
        set bs [expr {$bs + $R}]
    }
    return $result
}

proc find_conflicts {S E T} {
    set evs_full {}
    foreach line [dbq "SELECT id,name,start_ms,end_ms FROM events WHERE start_ms<=$E AND end_ms>=$S ORDER BY start_ms ASC, id ASC"] {
        set f [split $line \t]
        if {[llength $f] < 4} continue
        lappend evs_full [list [lindex $f 0] [lindex $f 1] [lindex $f 2] [lindex $f 3]]
    }
    set cands [list $S]
    foreach ev $evs_full {
        set s [lindex $ev 2]
        if {$s > $S && $s <= $E} { lappend cands $s }
    }
    set cands [lsort -integer -unique $cands]
    set conflict_ts {}
    foreach t $cands {
        set c 0
        foreach ev $evs_full {
            set s [lindex $ev 2]; set e [lindex $ev 3]
            if {$s <= $t && $t <= $e} { incr c }
        }
        if {$c > $T} { lappend conflict_ts $t }
    }
    if {[llength $conflict_ts] == 0} { return {} }
    set result {}
    foreach ev $evs_full {
        set id [lindex $ev 0]; set s [lindex $ev 2]; set e [lindex $ev 3]
        set clip_s [expr {max($s, $S)}]; set clip_e [expr {min($e, $E)}]
        set found 0
        foreach t $conflict_ts {
            if {$clip_s <= $t && $t <= $clip_e} { set found 1; break }
        }
        if {$found} { lappend result $ev }
    }
    return $result
}

# §17: concurrency histogram per slot.
# Returns list of {slot_start slot_end histogram_list mean_concurrency}.
# histogram_list[k] = integer instants in slot where exactly k events are active.
proc compute_heatmap {S E R} {
    set evs [read_events_se]
    set result {}
    set bs $S
    while {$bs <= $E} {
        set be [expr {min($bs + $R - 1, $E)}]
        set slot_ms [expr {$be - $bs + 1}]
        set cp [list $bs]
        foreach ev $evs {
            set s [lindex $ev 1]; set e [lindex $ev 2]
            if {$s > $bs && $s <= $be} { lappend cp $s }
            set ep1 [expr {$e + 1}]
            if {$ep1 > $bs && $ep1 <= $be} { lappend cp $ep1 }
        }
        lappend cp [expr {$be + 1}]
        set cp [lsort -integer -unique $cp]
        array unset hist
        set weight_sum 0
        for {set i 0} {$i < [llength $cp] - 1} {incr i} {
            set t [lindex $cp $i]
            set nt [lindex $cp [expr {$i+1}]]
            set run [expr {$nt - $t}]
            set c 0
            foreach ev $evs {
                set s [lindex $ev 1]; set e2 [lindex $ev 2]
                if {$s <= $t && $t <= $e2} { incr c }
            }
            if {[info exists hist($c)]} { incr hist($c) $run } else { set hist($c) $run }
            set weight_sum [expr {$weight_sum + $c * $run}]
        }
        set max_level 0
        foreach k [array names hist] { if {$k > $max_level} { set max_level $k } }
        set hlist {}
        for {set k 0} {$k <= $max_level} {incr k} {
            if {[info exists hist($k)]} { lappend hlist $hist($k) } else { lappend hlist 0 }
        }
        set mean [format "%.6f" [expr {double($weight_sum) / $slot_ms}]]
        lappend result [list $bs $be $hlist $mean]
        set bs [expr {$bs + $R}]
    }
    return $result
}

# §18: merged busy intervals using §11 strict-overlap merge.
# Returns list of {start_ms end_ms} pairs.
proc compute_merged {S E} {
    set busy {}
    foreach line [dbq "SELECT start_ms,end_ms FROM events WHERE start_ms<=$E AND end_ms>=$S"] {
        set f [split $line \t]
        if {[llength $f] < 2} continue
        set s [lindex $f 0]; set e [lindex $f 1]
        if {$s < $S} { set s $S }
        if {$e > $E} { set e $E }
        lappend busy [list $s $e]
    }
    set merged {}
    foreach iv [lsort -integer -index 0 $busy] {
        set s [lindex $iv 0]; set e [lindex $iv 1]
        if {[llength $merged] == 0} {
            lappend merged [list $s $e]
        } else {
            set li [lindex $merged end]
            set ls [lindex $li 0]; set le [lindex $li 1]
            if {$s <= $le} {
                if {$e > $le} { lset merged end [list $ls $e] }
            } else {
                lappend merged [list $s $e]
            }
        }
    }
    return $merged
}

# §19: max concurrency each event experiences within its clipped range in [S,E].
# Returns list of {id name start_ms end_ms max_depth}, sorted max_depth DESC, start_ms ASC, id ASC.
proc event_concurrency {S E} {
    set evs [read_events_se]
    set target {}
    foreach line [dbq "SELECT id,name,start_ms,end_ms FROM events WHERE start_ms<=$E AND end_ms>=$S ORDER BY start_ms ASC, id ASC"] {
        set f [split $line \t]
        if {[llength $f] < 4} continue
        lappend target [list [lindex $f 0] [lindex $f 1] [lindex $f 2] [lindex $f 3]]
    }
    set tagged {}
    foreach ev $target {
        set id [lindex $ev 0]; set nm [lindex $ev 1]; set es [lindex $ev 2]; set ee [lindex $ev 3]
        set cs [expr {max($es, $S)}]; set ce [expr {min($ee, $E)}]
        set cands [list $cs]
        foreach ev2 $evs {
            set s2 [lindex $ev2 1]
            if {$s2 > $cs && $s2 <= $ce} { lappend cands $s2 }
        }
        set cands [lsort -integer -unique $cands]
        set max_depth 0
        foreach t $cands {
            set c 0
            foreach ev2 $evs {
                set s2 [lindex $ev2 1]; set e2 [lindex $ev2 2]
                if {$s2 <= $t && $t <= $e2} { incr c }
            }
            if {$c > $max_depth} { set max_depth $c }
        }
        lappend tagged [list [expr {0-$max_depth}] $es $id $id $nm $es $ee $max_depth]
    }
    # Sort: neg_depth ASC (depth DESC), then start_ms ASC, then id ASC
    set tagged [lsort -command {apply {{a b} {
        foreach i {0 1 2} {
            set d [expr {[lindex $a $i] - [lindex $b $i]}]
            if {$d != 0} {return $d}
        }
        return 0
    }}} $tagged]
    set out {}
    foreach r $tagged {
        lappend out [list [lindex $r 3] [lindex $r 4] [lindex $r 5] [lindex $r 6] [lindex $r 7]]
    }
    return $out
}

# §21: Weighted interval scheduling DP.
# Returns {max_weight_str covered_ms id1 id2 ...} where max_weight_str is "%.2f" formatted.
# Events sorted end_ms ASC, id ASC; DP finds maximum-weight non-overlapping subset.
proc weighted_schedule {S E} {
    set evs {}
    foreach line [dbq "SELECT id,start_ms,end_ms,metadata_json FROM events WHERE start_ms>=$S AND end_ms<=$E ORDER BY end_ms ASC, id ASC"] {
        set f [split $line \t]
        if {[llength $f] < 3} continue
        set id [lindex $f 0]; set s [lindex $f 1]; set e [lindex $f 2]
        set w 1.0
        if {[llength $f] >= 4} {
            set mj [join [lrange $f 3 end] "\t"]
            if {[regexp {"weight"\s*:\s*(-?[0-9]+(?:\.[0-9]*)?)} $mj -> wstr]} {
                catch { set w [expr {double($wstr)}] }
            }
        }
        lappend evs [list $id $s $e $w]
    }
    set n [llength $evs]
    if {$n == 0} { return [list "0.00" 0] }
    # Build p(i) for each event i (1-indexed): largest j < i with evs[j-1].end_ms < evs[i-1].start_ms
    set p_arr [list 0]
    for {set i 1} {$i <= $n} {incr i} {
        set si [lindex [lindex $evs [expr {$i-1}]] 1]
        set pi 0
        for {set j [expr {$i-1}]} {$j >= 1} {incr j -1} {
            if {[lindex [lindex $evs [expr {$j-1}]] 2] < $si} { set pi $j; break }
        }
        lappend p_arr $pi
    }
    # OPT[0]=0; OPT[i]=max(OPT[i-1], weight_i + OPT[p(i)])
    set opt_arr [list 0.0]
    for {set i 1} {$i <= $n} {incr i} {
        set wi [lindex [lindex $evs [expr {$i-1}]] 3]
        set pi [lindex $p_arr $i]
        set c_with [expr {$wi + [lindex $opt_arr $pi]}]
        set c_skip [lindex $opt_arr [expr {$i-1}]]
        if {$c_with > $c_skip} {
            lappend opt_arr $c_with
        } else {
            lappend opt_arr $c_skip
        }
    }
    # Traceback
    set ids {}; set covered 0
    set i $n
    while {$i > 0} {
        set ev [lindex $evs [expr {$i-1}]]
        set wi [lindex $ev 3]; set pi [lindex $p_arr $i]
        set c_with [expr {$wi + [lindex $opt_arr $pi]}]
        if {$c_with > [lindex $opt_arr [expr {$i-1}]]} {
            lappend ids [lindex $ev 0]
            incr covered [expr {[lindex $ev 2] - [lindex $ev 1] + 1}]
            set i $pi
        } else { incr i -1 }
    }
    set ids [lreverse $ids]
    return [concat [list [format "%.2f" [lindex $opt_arr $n]] $covered] $ids]
}

# §22: Minimum interval graph coloring via earliest-start greedy.
# Returns {num_colors {id1 color1} {id2 color2} ...} sorted color ASC, id ASC.
proc compute_coloring {S E} {
    set evs {}
    foreach line [dbq "SELECT id,start_ms,end_ms FROM events WHERE start_ms<=$E AND end_ms>=$S ORDER BY start_ms ASC, id ASC"] {
        set f [split $line \t]
        if {[llength $f] < 3} continue
        lappend evs [list [lindex $f 0] [lindex $f 1] [lindex $f 2]]
    }
    if {[llength $evs] == 0} { return [list 0] }
    set colors {}
    set num_colors 0
    foreach ev $evs {
        set eid [lindex $ev 0]; set s [lindex $ev 1]; set e [lindex $ev 2]
        set used {}
        set j 0
        foreach prev $evs {
            if {$j >= [llength $colors]} break
            set ps [lindex $prev 1]; set pe [lindex $prev 2]
            if {$ps <= $e && $pe >= $s} { lappend used [lindex $colors $j] }
            incr j
        }
        set c 0
        while {[lsearch -integer $used $c] >= 0} { incr c }
        lappend colors $c
        if {[expr {$c + 1}] > $num_colors} { set num_colors [expr {$c + 1}] }
    }
    # Build {id color} pairs, sort color ASC then id ASC
    set tagged {}
    set j 0
    foreach ev $evs {
        lappend tagged [list [lindex $ev 0] [lindex $colors $j]]
        incr j
    }
    set tagged [lsort -command {apply {{a b} {
        set dc [expr {[lindex $a 1] - [lindex $b 1]}]
        if {$dc != 0} { return $dc }
        return [expr {[lindex $a 0] - [lindex $b 0]}]
    }}} $tagged]
    return [concat [list $num_colors] $tagged]
}

# §23: Concurrency run-length encoding over [S, E].
# Returns list of {start_ms end_ms concurrency} triples — maximal constant-concurrency runs,
# adjacent same-level runs merged, sorted start_ms ASC.
proc compute_concurrency_runs {S E} {
    set rows {}
    foreach line [dbq "SELECT id,start_ms,end_ms FROM events WHERE start_ms<=$E AND end_ms>=$S"] {
        set f [split $line \t]
        if {[llength $f] < 3} continue
        lappend rows [list [lindex $f 0] [lindex $f 1] [lindex $f 2]]
    }
    # Build change-point set
    array set cp_set {}
    set cp_set($S) 1
    set cp_set([expr {$E + 1}]) 1
    foreach r $rows {
        set s [lindex $r 1]; set e [lindex $r 2]
        if {$s > $S && $s <= $E} { set cp_set($s) 1 }
        set ep1 [expr {$e + 1}]
        if {$ep1 > $S && $ep1 <= $E} { set cp_set($ep1) 1 }
    }
    set cps [lsort -integer [array names cp_set]]
    # Build raw runs
    set runs {}
    for {set i 0} {$i < [llength $cps] - 1} {incr i} {
        set t [lindex $cps $i]
        set tnext [lindex $cps [expr {$i + 1}]]
        set c 0
        foreach r $rows {
            set s [lindex $r 1]; set e [lindex $r 2]
            if {$s <= $t && $t <= $e} { incr c }
        }
        lappend runs [list $t [expr {$tnext - 1}] $c]
    }
    # Merge adjacent runs with same concurrency
    set merged {}
    foreach r $runs {
        if {[llength $merged] == 0} {
            lappend merged $r
        } else {
            set last [lindex $merged end]
            if {[lindex $last 2] == [lindex $r 2]} {
                set merged [lreplace $merged end end \
                    [list [lindex $last 0] [lindex $r 1] [lindex $last 2]]]
            } else {
                lappend merged $r
            }
        }
    }
    return $merged
}

# §24: Greedy minimum-cardinality interval cover.
# Returns {min_events ids achieved_coverage} on success, {null {} achieved_coverage} if unreachable.
proc interval_cover {S E T_target} {
    set eff [expr {min($T_target, $E - $S + 1)}]
    set goal [expr {$S + $eff - 1}]
    set clipped {}
    foreach line [dbq "SELECT id,start_ms,end_ms FROM events WHERE start_ms<=$E AND end_ms>=$S"] {
        set f [split $line \t]
        if {[llength $f] < 3} continue
        set id [lindex $f 0]
        set cs [expr {max([lindex $f 1], $S)}]
        set ce [expr {min([lindex $f 2], $E)}]
        lappend clipped [list $id $cs $ce]
    }
    set remaining $clipped
    set frontier [expr {$S - 1}]
    set selected {}
    while {$frontier < $goal && [llength $remaining] > 0} {
        set fron1 [expr {$frontier + 1}]
        set best {}
        foreach r $remaining {
            set cs [lindex $r 1]; set ce [lindex $r 2]
            if {$cs <= $fron1 && $ce > $frontier} {
                if {[llength $best] == 0 || $ce > [lindex $best 2] ||
                    ($ce == [lindex $best 2] && [lindex $r 0] < [lindex $best 0])} {
                    set best $r
                }
            }
        }
        if {[llength $best] == 0} break
        set frontier [lindex $best 2]
        lappend selected [lindex $best 0]
        set new_rem {}
        foreach r $remaining {
            if {[lindex $r 0] ne [lindex $best 0]} { lappend new_rem $r }
        }
        set remaining $new_rem
    }
    set achieved [expr {max(0, $frontier - $S + 1)}]
    if {$frontier >= $goal} {
        set ids [lsort -integer $selected]
        return [list [llength $ids] $ids $achieved]
    } else {
        return [list null {} $achieved]
    }
}

# §25: Earliest free slot of duration D starting at or after A.
# Returns {slot_start slot_end}.
proc earliest_available {A D} {
    set rows {}
    foreach line [dbq "SELECT start_ms,end_ms FROM events WHERE end_ms>=$A ORDER BY start_ms"] {
        set f [split $line \t]
        if {[llength $f] < 2} continue
        set s [expr {max([lindex $f 0], $A)}]
        set e [lindex $f 1]
        lappend rows [list $s $e]
    }
    if {[llength $rows] == 0} {
        return [list $A [expr {$A + $D - 1}]]
    }
    set rows [lsort -integer -index 0 $rows]
    # Merge busy intervals
    set merged {}
    foreach r $rows {
        set bs [lindex $r 0]; set be [lindex $r 1]
        if {[llength $merged] == 0} {
            lappend merged [list $bs $be]
        } else {
            set last [lindex $merged end]
            set ls [lindex $last 0]; set le [lindex $last 1]
            if {$bs <= $le} {
                set merged [lreplace $merged end end [list $ls [expr {max($le, $be)}]]]
            } else {
                lappend merged [list $bs $be]
            }
        }
    }
    # Scan gaps
    set current $A
    foreach m $merged {
        set ms [lindex $m 0]; set me [lindex $m 1]
        if {[expr {$ms - $current}] >= $D} {
            return [list $current [expr {$current + $D - 1}]]
        }
        set current [expr {$me + 1}]
    }
    return [list $current [expr {$current + $D - 1}]]
}

# §20: free gaps with duration >= M, sorted duration_ms DESC, start_ms ASC.
# Returns list of {start_ms end_ms duration_ms}.
proc free_slots_min {S E M} {
    set gaps [compute_gaps $S $E]
    set tagged {}
    foreach g $gaps {
        set gs [lindex $g 0]; set ge [lindex $g 1]
        set dur [expr {$ge - $gs + 1}]
        if {$dur >= $M} {
            lappend tagged [list [expr {0-$dur}] $gs $ge $dur]
        }
    }
    # Sort: neg_dur ASC (dur DESC), then start_ms ASC
    set tagged [lsort -command {apply {{a b} {
        foreach i {0 1} {
            set d [expr {[lindex $a $i] - [lindex $b $i]}]
            if {$d != 0} {return $d}
        }
        return 0
    }}} $tagged]
    set out {}
    foreach r $tagged {
        lappend out [list [lindex $r 1] [lindex $r 2] [lindex $r 3]]
    }
    return $out
}

# §26: R-machine interval partitioning maximizing scheduled count.
# Returns list {max_scheduled {id1 room1} {id2 room2} ...} sorted id ASC.
proc room_schedule {S E R} {
    set evs {}
    foreach line [dbq "SELECT id,start_ms,end_ms FROM events WHERE start_ms>=$S AND end_ms<=$E ORDER BY end_ms ASC, id ASC"] {
        set f [split $line \t]
        if {[llength $f] < 3} continue
        lappend evs [list [lindex $f 0] [lindex $f 1] [lindex $f 2]]
    }
    set room_end {}
    for {set r 0} {$r < $R} {incr r} { lappend room_end free }
    set assigns {}
    foreach ev $evs {
        set eid [lindex $ev 0]; set s [lindex $ev 1]; set e [lindex $ev 2]
        set busy_avail {}
        set free_avail {}
        for {set r 0} {$r < $R} {incr r} {
            set re [lindex $room_end $r]
            if {$re eq "free"} {
                lappend free_avail $r
            } elseif {$re < $s} {
                lappend busy_avail [list $r $re]
            }
        }
        set chosen -1
        if {[llength $busy_avail] > 0} {
            set best_r -1; set best_end -1
            foreach pr $busy_avail {
                set r [lindex $pr 0]; set re [lindex $pr 1]
                if {$best_r == -1 || $re > $best_end} {
                    set best_r $r; set best_end $re
                }
            }
            set chosen $best_r
        } elseif {[llength $free_avail] > 0} {
            set chosen [lindex $free_avail 0]
        }
        if {$chosen == -1} continue
        set room_end [lreplace $room_end $chosen $chosen $e]
        lappend assigns [list $eid $chosen]
    }
    set assigns [lsort -command {apply {{a b} {
        return [expr {[lindex $a 0] - [lindex $b 0]}]
    }}} $assigns]
    return [concat [list [llength $assigns]] $assigns]
}

# Union-find helper for §27.
proc uf_find {pname i} {
    upvar $pname parent
    while {$parent($i) != $i} {
        set parent($i) $parent($parent($i))
        set i $parent($i)
    }
    return $i
}

# §27: connected components of the overlap graph, sorted min_start_ms ASC.
# Returns list of {min_start_ms max_end_ms id1 id2 ...} per component.
proc overlap_components {S E} {
    set evs {}
    foreach line [dbq "SELECT id,start_ms,end_ms FROM events WHERE start_ms<=$E AND end_ms>=$S"] {
        set f [split $line \t]
        if {[llength $f] < 3} continue
        lappend evs [list [lindex $f 0] [lindex $f 1] [lindex $f 2]]
    }
    set n [llength $evs]
    if {$n == 0} { return {} }
    array set parent {}
    for {set i 0} {$i < $n} {incr i} { set parent($i) $i }
    for {set i 0} {$i < $n} {incr i} {
        set ei [lindex $evs $i]
        set si [lindex $ei 1]; set eei [lindex $ei 2]
        for {set j [expr {$i+1}]} {$j < $n} {incr j} {
            set ej [lindex $evs $j]
            set sj [lindex $ej 1]; set eej [lindex $ej 2]
            if {$si <= $eej && $sj <= $eei} {
                set ri [uf_find parent $i]
                set rj [uf_find parent $j]
                if {$ri != $rj} { set parent($ri) $rj }
            }
        }
    }
    array set groups {}
    for {set i 0} {$i < $n} {incr i} {
        set r [uf_find parent $i]
        lappend groups($r) $i
    }
    set comps {}
    foreach r [array names groups] {
        set members $groups($r)
        set ids {}
        set mn {}
        set mx {}
        foreach idx $members {
            set ev [lindex $evs $idx]
            lappend ids [lindex $ev 0]
            set s [lindex $ev 1]; set e [lindex $ev 2]
            if {$mn eq "" || $s < $mn} { set mn $s }
            if {$mx eq "" || $e > $mx} { set mx $e }
        }
        set ids [lsort -integer $ids]
        lappend comps [list $mn $mx $ids]
    }
    set comps [lsort -command {apply {{a b} {
        return [expr {[lindex $a 0] - [lindex $b 0]}]
    }}} $comps]
    set out {}
    foreach c $comps {
        lappend out [concat [list [lindex $c 0] [lindex $c 1]] [lindex $c 2]]
    }
    return $out
}

# §28: returns {max_depth total_ms d0_ms d1_ms ... dmax_depth_ms}
proc compute_depth_profile {S E} {
    set evs [read_events_se]
    set total_ms [expr {$E - $S + 1}]

    set cp_set [list $S [expr {$E + 1}]]
    foreach ev $evs {
        set s [lindex $ev 1]; set e [lindex $ev 2]
        if {$s > $S && $s <= $E} { lappend cp_set $s }
        set ep1 [expr {$e + 1}]
        if {$ep1 > $S && $ep1 <= $E} { lappend cp_set $ep1 }
    }
    set cps [lsort -integer -unique $cp_set]

    array set depth_total {}
    set max_depth 0
    for {set i 0} {$i < [llength $cps] - 1} {incr i} {
        set t  [lindex $cps $i]
        set nt [lindex $cps [expr {$i+1}]]
        set dur [expr {$nt - $t}]
        set c 0
        foreach ev $evs {
            if {[lindex $ev 1] <= $t && $t <= [lindex $ev 2]} { incr c }
        }
        if {![info exists depth_total($c)]} { set depth_total($c) 0 }
        incr depth_total($c) $dur
        if {$c > $max_depth} { set max_depth $c }
    }
    if {![info exists depth_total(0)]} { set depth_total(0) 0 }

    set result [list $max_depth $total_ms]
    for {set d 0} {$d <= $max_depth} {incr d} {
        if {[info exists depth_total($d)]} {
            lappend result $depth_total($d)
        } else {
            lappend result 0
        }
    }
    return $result
}

# §29: returns {total_ms covered_ms max_depth mean_str var_str p50}
proc compute_window_stats {S E} {
    set evs [read_events_se]
    set total_ms [expr {$E - $S + 1}]

    set cp_set [list $S [expr {$E + 1}]]
    foreach ev $evs {
        set s [lindex $ev 1]; set e [lindex $ev 2]
        if {$s > $S && $s <= $E} { lappend cp_set $s }
        set ep1 [expr {$e + 1}]
        if {$ep1 > $S && $ep1 <= $E} { lappend cp_set $ep1 }
    }
    set cps [lsort -integer -unique $cp_set]

    set runs {}
    for {set i 0} {$i < [llength $cps] - 1} {incr i} {
        set t  [lindex $cps $i]
        set nt [lindex $cps [expr {$i+1}]]
        set dur [expr {$nt - $t}]
        set c 0
        foreach ev $evs {
            if {[lindex $ev 1] <= $t && $t <= [lindex $ev 2]} { incr c }
        }
        lappend runs [list $c $dur]
    }

    set covered_ms 0
    set max_depth  0
    set wsum       0.0
    foreach run $runs {
        set c [lindex $run 0]; set d [lindex $run 1]
        if {$c > 0} { incr covered_ms $d }
        if {$c > $max_depth} { set max_depth $c }
        set wsum [expr {$wsum + double($c) * $d}]
    }
    set mean_depth [expr {$wsum / $total_ms}]

    set vsum 0.0
    foreach run $runs {
        set c    [lindex $run 0]; set d [lindex $run 1]
        set diff [expr {double($c) - $mean_depth}]
        set vsum [expr {$vsum + $d * $diff * $diff}]
    }
    set var_depth [expr {$vsum / $total_ms}]

    set target_pos [expr {($total_ms - 1) / 2}]
    set pos 0; set p50 0
    foreach run $runs {
        set c [lindex $run 0]; set d [lindex $run 1]
        if {$pos + $d > $target_pos} { set p50 $c; break }
        incr pos $d
    }

    return [list $total_ms $covered_ms $max_depth \
                 [format "%.6g" $mean_depth] \
                 [format "%.6g" $var_depth] \
                 $p50]
}
