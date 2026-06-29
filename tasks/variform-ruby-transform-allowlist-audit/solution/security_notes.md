# Security notes, variform-ruby-transform-allowlist-audit

Inspired by Ruby on Rails Active Storage CVE-2025-24293 / GHSA-r4mg-4433-c7g3 (MIT
licensed). The codebase under /app/environment/ is an original implementation that
reproduces the image-transformation command-injection vulnerability class; it is not a
copy of the upstream Rails code. Every accepted transformation flows into the processor
command line, so a transformation that slips past validation is an ImageMagick option
injection (CWE-77 command injection, CWE-94 code injection).

- allow-list scope (CWE-77), in lib/variform/validation/method_allowlist.rb. The
  supported-method allow list carried the pass-through methods apply, loader, and saver,
  which forward a full processing pipeline, a raw reader target, and a raw writer target
  to the processor (for example a coder string such as msl: or a label target) that the
  option deny list is not designed to catch. The fix removes apply, loader, and saver
  from the allow list. Confirmed with testdata/exploits/exploit_passthrough_saver.json.

- method gate matching (CWE-77), in lib/variform/validation/method_gate.rb. The gate
  decided a method was supported when an allowed name appeared anywhere inside the
  candidate, a substring match, so a crafted name that embeds an allowed method plus
  extra whitespace-separated option tokens passed and those tokens reached the command.
  The fix requires an exact match against the allow list. Confirmed with
  testdata/exploits/exploit_method_smuggle.json.

- method name canonicalization (CWE-77), in lib/variform/validation/method_gate.rb. The
  same gate first reduced the candidate to its first whitespace-separated token before
  matching, so the match ran against only the leading word and a name such as
  "crop -write ..." was treated as "crop"; the validator and the command builder then
  disagreed on the canonical name. The fix matches the whole name as given, with no
  first-token reduction, so any extra whitespace-separated token makes the name
  unsupported. Confirmed with testdata/exploits/exploit_method_smuggle.json.

- case-sensitive option scan (CWE-77), in lib/variform/validation/scalar_scan.rb. The
  forbidden-option scan compared the raw argument text, so a forbidden option supplied
  in a different letter case slipped through. The fix lowercases the text before the
  comparison so the check is case insensitive. Confirmed with
  testdata/exploits/exploit_case_flag.json.

- option sign coverage (CWE-77), in lib/variform/validation/scalar_scan.rb. The scan
  matched only the hyphen form of each forbidden option, so the same option written in
  its plus form, for example +write, was not caught even though it names the identical
  processor option. The fix treats the leading sign as meaningless and matches both the
  hyphen and the plus form of every forbidden token. Confirmed with
  testdata/exploits/exploit_plus_flag.json.

- reader and writer indirection (CWE-77), in lib/variform/validation/scalar_scan.rb. The
  scan looked only for named option tokens and never for a coder pseudo-protocol or
  filename indirection, so an argument token such as msl:/tmp/x, a leading at-sign
  read-from-file, or a pipe handed a reader or writer target straight to the processor.
  The fix rejects any argument token that begins with an at sign, contains a pipe, or
  carries a letters-then-colon scheme prefix. Confirmed with
  testdata/exploits/exploit_coder_indirection.json.

- hash key coverage (CWE-77), in lib/variform/validation/hash_scan.rb. The object
  argument walk scanned only the values, never the hash keys, so a forbidden option used
  as an object key was never inspected and reached the command. The fix scans the key as
  well as the value. Confirmed with testdata/exploits/exploit_hash_key.json.

- nested argument recursion (CWE-77), in lib/variform/validation/list_scan.rb. The array
  argument walk inspected only top-level string elements and skipped nested arrays and
  objects, so a forbidden option hidden one level deep was never scanned. The fix
  recurses into every nested element through the shared argument scan. Confirmed with
  testdata/exploits/exploit_nested_list.json.
