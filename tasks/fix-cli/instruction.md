# Fix CLI Sum Tool

## High-Level Goal

Repair a buggy Python CLI program at `/app/sum_cli.py` that reads integers from a text file, sums them, and prints the result. The program must handle various edge cases and error conditions robustly.

## Critical Success Factors

- **Correctness**: Must produce accurate results for all valid inputs
- **Reliability**: Must handle edge cases without crashing
- **Determinism**: Must produce identical output for identical inputs
- **Security**: Must not execute arbitrary code or access unauthorized resources
- **Performance**: Must handle files up to 10MB in size efficiently

## Environment Specifications

### Provided Files
- `/app/sum_cli.py`: The buggy Python CLI program to fix
- `/tmp/`: Writable directory for temporary files (10MB available)
- `/app/output/`: Directory for any output files (read-only for testing)
- `/logs/`: Directory for log files (read-only for testing)

### Execution Environment
- **Python Version**: 3.13.0 (system default)
- **Available Memory**: 1GB
- **CPU**: 1 core
- **Disk Space**: 100MB available (excluding system files)
- **Network**: Disabled (all external connections blocked)
- **User**: Non-root user with limited permissions

### Verifier Behavior
- Runs tests from a temporary directory
- Uses system Python with no additional packages
- Validates both stdout and stderr output
- Enforces strict resource limits (CPU, memory, execution time)

What does NOT exist / must not be relied on:

- No additional Python packages beyond the Python standard library.
- No external services.

## Technical Requirements

### 1. Command-Line Interface
- **Invocation**: `python /app/sum_cli.py <input_file>`
- **Help**: `python /app/sum_cli.py -h` or `python /app/sum_cli.py --help`
- **Arguments**:
  - `input_file` (positional, required): Path to input text file
  - `-h, --help` (optional): Show usage information and exit
- **Exit Codes**:
  - `0`: Success (valid input processed or help shown)
  - `1`: File not found or not readable
  - `2`: Invalid command-line arguments
  - `3`: Internal error (unexpected condition)

### 2. Input Processing
- **File Handling**:
  - Must support files up to 10MB
  - Must handle LF (Unix) and CRLF (Windows) line endings
  - Must support UTF-8 encoded files with or without BOM
- **Line Processing**:
  - Each line is processed independently
  - Leading/trailing whitespace is stripped
  - Lines are split on whitespace to extract individual tokens
  - Empty lines and whitespace-only lines are ignored
- **Number Parsing**:
  - Each token is parsed as an integer: `-?\d+` (optional minus followed by digits)
  - Range: -2^63 to 2^63-1 (64-bit signed integers)
  - Invalid tokens (non-integers) are silently skipped
  - No scientific notation or decimal points allowed

### 3. Output Specification
- **Success Case**:
  - Single line to stdout: `SUM=<number>\n`
  - Trailing newline required
  - No other output to stdout
- **Error Cases**:
  - File not found: Error message to stderr, exit code 1
  - Invalid arguments: Error message to stderr, exit code 2
  - Read permission denied: Error message to stderr, exit code 1
  - No valid integers found: `SUM=0\n` to stdout, exit code 0

### 4. Performance Requirements
- Must process a 10MB file in under 5 seconds
- Must use constant memory (O(1) space complexity)
- Must be interruptible (handle SIGINT gracefully)

### 5. Security Constraints
- Must not use:
  - `eval()`, `exec()`, `compile()`
  - `os.system()`, `subprocess.run()`, or similar
  - `pickle`, `marshal`, or other serialization modules
  - Direct file system access outside input file
  - Network access
  - Environment variables
- Must validate all input paths
- Must handle symlinks safely
- Must not leak file descriptors

### 6. Resource Limits
- Maximum runtime: 30 seconds
- Maximum memory: 50MB
- Maximum output: 1KB
- Maximum open files: 10
- No child processes allowed

## Input/Output Specifications

### Input File Format
- **Location**: Any readable path (typically under `/tmp/` for testing)
- **Encoding**: UTF-8 (with or without BOM)
- **Line Endings**: LF (`\n`) or CRLF (`\r\n`)
- **Line Length**: Up to 1,000,000 characters
- **File Size**: Up to 10MB
- **Permissions**: Readable by the current user

### Expected Outputs
- **Successful Execution**:
  ```
  SUM=<number>
  ```
  Where `<number>` is the sum of all valid integers in the input file

- **Error Cases**:
  - File not found:
    ```
    Error: File not found: /path/to/missing.txt
    ```
  - Permission denied:
    ```
    Error: Permission denied: /path/to/protected.txt
    ```
  - Invalid arguments:
    ```
    Usage: python /app/sum_cli.py <input_file>
    ```

### Test Cases
```
# Test 1: Basic sum
echo -e "1\n2\n3" > /tmp/input1.txt
python /app/sum_cli.py /tmp/input1.txt  # Expected: SUM=6

# Test 2: Negative numbers
echo -e "-1\n-2\n-3" > /tmp/input2.txt
python /app/sum_cli.py /tmp/input2.txt  # Expected: SUM=-6

# Test 3: Mixed input
echo -e "1\n 2\n  \n 3\nnot_a_number\n-4" > /tmp/input3.txt
python /app/sum_cli.py /tmp/input3.txt  # Expected: SUM=2

# Test 4: Empty file
touch /tmp/empty.txt
python /app/sum_cli.py /tmp/empty.txt   # Expected: SUM=0

# Test 5: File not found
python /app/sum_cli.py /does/not/exist  # Expected: Error message, exit code 1
```

## Strict Constraints & Anti-Cheating Measures

### Modification Boundary
- **Allowed**: Only modify `/app/sum_cli.py`
- **Forbidden**:
  - Modifying any file outside `/app/sum_cli.py`
  - Creating new files or directories
  - Changing file permissions
  - Accessing network resources
  - Using external commands or subprocesses
  - Installing packages or modifying system state

### Anti-Cheating Protections
- **Input Validation**:
  - Must handle any valid input file path
  - Must not assume file location or naming pattern
  - Must not hardcode test case solutions
- **Output Validation**:
  - Must produce exact output format
  - No debug output or logging to stdout/stderr unless specified
  - No timing or fingerprinting attempts
- **Resource Usage**:
  - Must respect memory and CPU limits
  - Must not fork or spawn processes
  - Must not access files outside allowed paths

### Verification Process
1. **Static Analysis**:
   - No banned functions or modules
   - No hardcoded solutions
   - No file system access outside input file

2. **Dynamic Analysis**:
   - Runtime monitoring for forbidden operations
   - Resource usage tracking
   - Output validation against known test cases

3. **Fuzzing**:
   - Random input generation
   - Edge case testing
   - Memory safety checks

### Security Restrictions
- **Blocked System Calls**:
  - `socket`, `connect`, `bind` (network)
  - `fork`, `exec`, `system` (process)
  - `chmod`, `chown` (permissions)
  - `open` with write flags (read-only mode)
  - `unlink`, `rmdir` (deletion)

- **Restricted Modules**:
  ```python
  # Blocked modules
  import os     # Limited to os.path.exists(), os.access()
  import sys    # Allowed for argv, stderr, exit
  # All other modules must be explicitly allowed
  ```

## Verification & Testing Protocol

### Test Suite Coverage
1. **Functional Tests**
   - Basic summation of positive/negative numbers
   - Empty input file
   - Very large input files (up to 10MB)
   - Files with maximum line length
   - Files with mixed content (valid/invalid lines)
   - Files with various line endings (LF/CRLF)
   - Files with UTF-8 BOM
   - Files with unusual permissions
   - Symlinked input files

2. **Error Condition Tests**
   - Non-existent file
   - Directory instead of file
   - Permission denied
   - Invalid command-line arguments
   - Missing arguments
   - Too many arguments
   - Special files (device files, FIFOs)
   - Broken symlinks

3. **Performance Tests**
   - Large input files (10MB, 1M lines)
   - Maximum line length (1M characters)
   - Rapid sequential file processing
   - Resource exhaustion cases

4. **Security Tests**
   - Path traversal attempts
   - Symbolic link attacks
   - Permission escalation attempts
   - Memory exhaustion attempts
   - CPU exhaustion attempts
   - File descriptor exhaustion
   - Environment variable manipulation
   - Signal handling (SIGINT, SIGTERM)

### Verification Process
1. **Setup**:
   - Fresh container instance
   - Resource limits applied
   - Network disabled
   - Read-only filesystem except `/tmp`

2. **Execution**:
   - Run with various test inputs
   - Monitor system calls
   - Measure resource usage
   - Capture all output

3. **Validation**:
   - Verify exit codes
   - Validate output format
   - Check for memory leaks
   - Ensure no files were modified
   - Confirm no network activity
   - Verify resource limits were respected

### Pass/Fail Criteria
- **Pass**:
  - All test cases pass
  - No security violations
  - Within resource limits
  - Correct output format
  - Proper error handling

- **Fail**:
  - Any test case fails
  - Security violation detected
  - Resource limit exceeded
  - Incorrect output format
  - Crash or unhandled exception
  - Any forbidden operation

## Instruction–Test Alignment Matrix

| Requirement | Instruction Coverage | Test Coverage | Verifiable | Notes |
|-------------|----------------------|---------------|------------|-------|
| **Core Functionality** | | | | |
| Sum positive integers | ✅ Explicitly described | ✅ Multiple test cases | ✅ Automated | Basic functionality |
| Handle negative numbers | ✅ Explicitly described | ✅ Dedicated test case | ✅ Automated | Sign handling |
| Process large numbers | ✅ Range specified | ✅ Edge case tests | ✅ Automated | 64-bit integer support |
| **Input Handling** | | | | |
| Skip blank lines | ✅ Explicitly described | ✅ Multiple test cases | ✅ Automated | Whitespace handling |
| Skip non-integer lines | ✅ Explicitly described | ✅ Dedicated test case | ✅ Automated | Error resilience |
| Handle empty file | ✅ Explicitly described | ✅ Dedicated test case | ✅ Automated | Edge case |
| **Error Conditions** | | | | |
| File not found | ✅ Explicitly described | ✅ Dedicated test case | ✅ Automated | Error handling |
| Permission denied | ✅ Explicitly described | ✅ Dedicated test case | ✅ Automated | Security |
| Invalid arguments | ✅ Explicitly described | ✅ Multiple test cases | ✅ Automated | CLI validation |
| **Performance** | | | | |
| Handle 10MB file | ✅ Explicit requirement | ✅ Performance test | ✅ Automated | Scalability |
| Constant memory | ✅ Explicit requirement | ✅ Memory monitoring | ✅ Automated | Efficiency |
| **Security** | | | | |
| No code execution | ✅ Explicit restriction | ✅ Static analysis | ✅ Automated | Safety |
| No network access | ✅ Explicit restriction | ✅ Network monitoring | ✅ Automated | Security |
| Input validation | ✅ Explicit requirement | ✅ Fuzzing tests | ✅ Automated | Robustness |
| **Output Format** | | | | |
| Exact output format | ✅ Explicit specification | ✅ Strict validation | ✅ Automated | Consistency |
| Proper exit codes | ✅ Explicit specification | ✅ All code paths tested | ✅ Automated | Scriptability |

## Anti-Cheating Validation

### Detection Methods
1. **Static Analysis**
   - Pattern matching for hardcoded solutions
   - AST inspection for banned functions
   - Bytecode analysis for obfuscation attempts

2. **Dynamic Analysis**
   - System call monitoring
   - File system access tracking
   - Network activity monitoring
   - Resource usage profiling

3. **Differential Testing**
   - Compare multiple solution approaches
   - Verify consistent behavior across runs
   - Check for environment dependencies

### Known Exploit Vectors (Mitigated)
- **Path Traversal**: Normalize and validate all paths
- **Timing Attacks**: Constant-time string comparison
- **Resource Exhaustion**: Strict limits on memory/CPU
- **Environment Variables**: Whitelist-only access
- **Temporary Files**: Secure creation and cleanup

## Final Verification Checklist

### Before Submission
- [ ] All requirements are explicitly documented
- [ ] All tests pass with the oracle solution
- [ ] No security vulnerabilities detected
- [ ] Performance meets requirements
- [ ] Documentation is complete and accurate

### After Submission
- [ ] Task passes automated verification
- [ ] No false positives in anti-cheating checks
- [ ] Performance benchmarks within expected range
- [ ] Documentation matches implementation
