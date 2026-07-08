# Failure behavior

Invalid stage files, unknown combinations, or missing committed state cause a non-zero exit status.

On failure the implementation removes the output path if it already exists. Successful runs write the complete report atomically through the normal writer.

Diagnostic messages are emitted on standard error. Diagnostic text is not part of the report contract.
