#!/usr/bin/env tclsh8.6
# Stub CGI dispatcher — returns 501 for all graded endpoints.
package require Tcl 8.6

proc send_response {status content_type body} {
    if {$status != 200} {
        puts "Status: $status\r"
    }
    puts "Content-Type: $content_type\r"
    puts "\r"
    puts $body
    flush stdout
}

set method [expr {[info exists ::env(REQUEST_METHOD)] ? $::env(REQUEST_METHOD) : "GET"}]
set uri    [expr {[info exists ::env(REQUEST_URI)]    ? $::env(REQUEST_URI)    : "/"}]

# Strip query string for routing
set path [lindex [split $uri "?"] 0]

if {$method eq "GET" && $path eq "/healthz"} {
    send_response 200 "application/json" {{"status":"ok"}}
} else {
    send_response 501 "application/json" {{"error":"not_implemented"}}
}
