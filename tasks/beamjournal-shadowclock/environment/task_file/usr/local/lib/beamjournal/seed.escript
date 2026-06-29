#!/usr/bin/env escript
%%! -noshell

main([JournalPath, PlanPath]) ->
    Journal = <<
        5:16/little-unsigned-integer, 1, 5, "alpha", 0, "hello",
        5:16/little-unsigned-integer, 1, 3, "all", 1, "abcde",
        "DONE"
    >>,
    Plan = <<
        5, "alpha", 0, 1, 16#11, 1,
        1, "*", 1, 0, 0, 1,
        "DONE"
    >>,
    ok = file:write_file(JournalPath, Journal),
    ok = file:write_file(PlanPath, Plan);
main(_) ->
    halt(2).
