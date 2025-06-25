# clitest.py - A Generic Command-Line Testing Tool

`clitest.py` is a self-contained, language-agnostic test runner for command-line interface (CLI) tools. It is written in Python 3 and requires no third-party libraries, making it highly portable.

Tests are defined in a simple, expressive XML format allowing for detailed and well-documented test suites. The tool can run multiple test suites and report their results in one of several formats, including JUnit and TAP, making it easy to integrate with CI/CD systems like Jenkins, GitLab CI, and GitHub Actions.

## Features

* **Dependency-Free:** Runs anywhere with a standard Python 3 installation.
* **XML-Based Test Suites:** Create clear, commented, and structured test plans.
* **Multiple Output Formats:** Integrates seamlessly with a wide range of developer tools.
* **Full Environment Control:** Define environment variables, working directories, and setup/teardown commands to create stable and isolated tests.
* **Powerful Output Matching:** Go beyond exact string comparison with support for substring matching (`contains`), regular expressions (`regex`), and automatic normalization of whitespace and ANSI color codes.
* **Secure:** Executes commands directly without invoking a shell, preventing shell injection vulnerabilities.

## Example

The `clitest.py` code is itself tested by its own test specification:

```sh
$ python3 clitest.py clitest-*-tests.xml

  Tests for the --reporter junit feature
    ✓ Should produce valid JUnit XML for a passing suite
    ✓ Should produce valid JUnit XML for a failing suite
    ✓ Should aggregate results correctly in JUnit XML for multiple suites
    ✓ Should include verbose output in system-out for JUnit reporter

  Tests for the --reporter spec feature
    ✓ Should produce valid spec output for a passing suite
    ✓ Should produce valid spec output for a failing suite
    ✓ Should produce valid spec output for multiple suites
    ✓ Should produce verbose output with spec reporter

  Test the core features of clitest.py
    ✓ Should exit 0 and report a pass for a valid, passing suite
    ✓ Should exit 1 and report a failure for a valid, failing suite
    ✓ Should correctly process the 'normalize' attribute
    ✓ Should correctly process the 'match=regex' attribute
    ✓ Should correctly apply environment variables to subprocesses
    ✓ Should fail gracefully if the suite file is not found
    ✓ Should fail gracefully if the suite file is invalid XML
    ✓ Should show a usage error when no arguments are given
    ✓ Should produce valid TAP subtest output for multiple suites
    ✓ Should produce verbose output with --verbose flag
    ✓ Should show usage error for mutually exclusive flags --verbose and --quiet
    ✓ Should list tests with --list-cases flag and not run them

  20 tests run, 20 passing, 0 failing
```

Refer to the [clitest-tap-tests.xml](./clitest-tap-tests.xml) file for an example of how to write the test cases for a command line program. Refer to all the `clitest-*-tests.xml` files for an example of how to write different test suites for different features.

## Installation

The `clitest.py` file is a standalone test runner. No dependencies need to be installed.

Just download the `clitest.py` code from the command line and begin using it right away:

```sh
$ curl -LJO https://raw.githubusercontent.com/bishopb/clitest/refs/heads/main/clitest.py
$ python3 clitest.py -h
```

## Usage

```
usage: clitest.py [-h] [-v | -q | --list-cases] [--reporter {tap,junit,spec}] SUITE [SUITE ...]

A generic, language-agnostic command-line test runner.

positional arguments:
  SUITE                 One or more paths to test suite XML files.

options:
  -h, --help            show this help message and exit
  -v, --verbose         Enable verbose output.
  -q, --quiet           Enable quiet output.
  --list-cases          List all test cases that would be run without executing them.
  --reporter {tap,junit,spec}
                        The output format for test results (default: spec).
```

* `clitest.py` is invoked from the command line, specifying one or more test suite files.
* `clitest.py` runs the tests given by the test suite files arguments, unless the `--list-cases` option is given, in which case only the cases that would be run are displayed.
* `clitest.py` shows the test results in `spec` output be default, but can be switched to `tap` or `junit` with the `--reporter` option.

## Test Suite XML Specification

A test suite file is an XML document that defines the tests to be run. Refer to the [clitest-schema.xsd](./clitest-schema.xsd) file for the formal specification.

In short:
* The clitest XML format is structured around a root `<test-suite>` element, which can contain an optional `<environment>` block for global setup, teardown, and environment variables.
* Inside the suite, a `<test-cases>` element holds one or more individual `<test-case>` blocks.
* Each test case defines a `<command>` to be run, its `<args>`, optional `<stdin>`, and a mandatory `<expect>` block that specifies the expected stdout, stderr, and exit code.
* Both stdout and stderr expectations can be modified with match (exact, contains, regex) and normalize (ansi, whitespace) attributes for flexible and robust comparisons.

### Verifying a Test Suite

The `xmllint` tool can validate a test suite XML file you create against the clitest test suite XML schema definition, like so:

```sh
$ xmllint --noout --schema clitest-schema.xsd yourapp-feature-tests.xml
yourapp-feature-tests.xml validates
```

### Expectation verification

To create robust and resilient tests, `clitest.py` provides powerful attributes on the `<stdout>` and `<stderr>` tags that allow you to control how the actual output from a command is compared against your expectations.

#### The `match` Attribute

This attribute defines the comparison strategy.

* **`match="exact"` (Default)**
  This is the default behavior if no `match` attribute is specified. The actual output from the command must be an identical string match to the text inside the `<stdout>` or `<stderr>` tag.

  * **Use when:** You need to test for exact, predictable output, such as a version string or a simple "OK" message.
  * **Example:**
    ```xml
    <stdout match="exact">v1.2.3</stdout>
    ```

* **`match="contains"`**
  The test passes if the actual output contains the expected text as a substring.

  * **Use when:** You only care about the presence of a specific keyword or error message within a larger, potentially variable output (like a log file).
  * **Example:**
    ```xml
    <stderr match="contains">ERROR: File not found</stderr>
    ```

  Recommend to use with the normalize="whitespace" attribute, to eliminate comparison issues related to whitespace

* **`match="regex"`**
  The test passes if the actual output matches the provided PCRE (Perl Compatible Regular Expressions) pattern. This is the most powerful matching mode.

  * **Use when:** You need to validate structured output that contains variable data like timestamps, process IDs, or file paths. Note that the regex match is unanchored by default; use `^` and `$` for full-line matching.
  * **Example:**
    ```xml
    <!-- This will match "Log file created: app-2024-06-23-143055.log" -->
    <stdout match="regex"><![CDATA[Log file created: app-\d{4}-\d{2}-\d{2}-\d{6}\.log]]></stdout>
    ```

  To enforce multi-line matching, begin the regex with `(?s)`.

#### The `normalize` Attribute

This attribute allows you to clean up or "normalize" the actual output *before* the comparison is performed. You can combine normalizers by providing a comma-separated list (e.g., `normalize="ansi,whitespace"`). Captialization does not matter.

* **`normalize="ansi"`**
  This strips all ANSI escape codes (used for color, bolding, etc.) from the command's output.

  * **Use when:** You want to test the textual content of a command's output but ignore its styling. This makes tests resilient to changes in color schemes.
  * **Example:**
    ```xml
    <!-- This will successfully match "Error" even if it's colorized in the terminal -->
    <stderr normalize="ansi" match="contains">Error</stderr>
    ```

* **`normalize="whitespace"`**
  This performs a comprehensive cleanup of whitespace. It trims leading/trailing whitespace and collapses all internal newlines, tabs, and consecutive spaces into a single space.

  * **Use when:** You want to test the content of a multi-line output without being sensitive to indentation or exact line breaks.
  * **Example:**
    ```xml
    <!-- If the actual output is a messy, multi-line error message, this will flatten it for easy comparison. -->
    <stdout normalize="whitespace" match="exact">Error: Operation failed. Please try again.</stdout>
    ```

By combining these attributes, you can create tests that are both precise in what they validate and resilient to irrelevant changes in formatting or style.


### Example of a Test Suite XML

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!--
  clitest.py: Comprehensive Example Suite
  This file demonstrates all available features of the XML test format.
-->
<test-suite description="Comprehensive Demo Suite" timeout="60">

  <!-- A global environment for all tests. It creates a temp directory and a variable. -->
  <environment>
    <working-directory>/tmp/clitest-demo</working-directory>
    <variable name="API_URL">https://api.example.com</variable>
    <setup>
      <command>mkdir -p /tmp/clitest-demo</command>
    </setup>
    <teardown>
      <command>rm -rf /tmp/clitest-demo</command>
    </teardown>
  </environment>

  <test-cases>

    <!--
      Test Case 1: The Happy Path.
      This case shows a simple command that passes with an exact stdout match.
    -->
    <test-case description="Should output the correct version string">
      <command>./my-app</command>
      <args><arg>--version</arg></args>
      <expect>
        <stdout match="exact">1.2.3</stdout>
        <exit_code>0</exit_code>
      </expect>
    </test-case>

    <!--
      Test Case 2: Failure, Normalization, and Environment Override.
      - Expects a non-zero exit code.
      - Uses `normalize` to ignore color and whitespace in the error message.
      - Uses `match="contains"` to check for a key phrase.
      - Defines a case-specific environment variable.
    -->
    <test-case description="Should handle errors gracefully">
      <environment>
        <variable name="LOG_LEVEL">debug</variable>
      </environment>
      <command>./my-app</command>
      <args><arg>--read</arg><arg>missing.txt</arg></args>
      <expect>
        <stderr normalize="ansi,whitespace" match="contains">ERROR: File not found</stderr>
        <exit_code>1</exit_code>
      </expect>
    </test-case>

    <!--
      Test Case 3: Stdin and Regex Matching.
      - Provides input to the command via the <stdin> tag.
      - Uses `match="regex"` to validate structured output with a variable timestamp.
    -->
    <test-case description="Should process stdin and produce structured output">
      <command>./my-app</command>
      <args><arg>--process</arg></args>
      <stdin>data to process</stdin>
      <expect>
        <stdout match="regex"><![CDATA[Processed data successfully at \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z]]></stdout>
      </expect>
    </test-case>

    <!--
      Test Case 4: Timeout Override.
      - Overrides the suite's global timeout of 60 seconds with a much shorter one.
      - This test will fail if the command takes longer than 5.5 seconds.
    -->
    <test-case description="Should complete a long operation within the time limit" timeout="5.5">
      <command>./my-app</command>
      <args><arg>--long-operation</arg></args>
      <expect>
        <stdout>Operation complete.</stdout>
      </expect>
    </test-case>

  </test-cases>
</test-suite>
```
