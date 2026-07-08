Differing bits are not the real problem. A kernel only matters here if the release build pushes its output across the contract it promises. CONTRACTS.md lists every kernel's documented invariant and gives each one a short id.

Go through the kernels and certify each as HAZARD or BENIGN. A kernel is HAZARD only when you can show an input where the release build genuinely violates its invariant while the strict build still keeps it. A divergence by itself proves nothing, since some kernels shift in their low bits yet stay inside their contract. Flagging a kernel you cannot back with a real violation counts against you.

Write /app/output/result_2.json, a JSON object mapping each kernel name to a record. Give every record a verdict key holding the string HAZARD or BENIGN. For each HAZARD also add a witness key holding the input argument array and an invariant key set to that kernel's short id from CONTRACTS.md. A benign kernel needs only its verdict. One entry might look like:

    "examplekernel": {"verdict": "HAZARD", "witness": [number], "invariant": "the_short_id"}
