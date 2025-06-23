# Contributing to clitest.py

First off, thank you for considering contributing to `clitest.py`! It's people like you that make open source such a great community. Any contribution, whether it's a bug report, a feature request, or a code change, is highly appreciated.

This document provides a set of guidelines for contributing to the project.

## How Can I Contribute?

### Reporting Bugs

If you find a bug, please ensure it hasn't already been reported by searching the issues on GitHub. If you can't find an open issue addressing the problem, please open a new one. Be sure to include as much information as possible, including:

* A clear and descriptive title.
* The version of Python you are using.
* A step-by-step description of how to reproduce the bug.
* The expected behavior versus the actual behavior you observed.
* A copy of the `test-suite.xml` file that causes the bug.
* Any error messages or logs from the terminal.

We urge you to include within your bug report the output of running the clitest.py built-in tests:

```sh
$ python3 clitest.py clitest-*-tests.xml
TAP version 14
ok 1 - Should exit 0 and report a pass for a valid, passing suite
ok 2 - Should exit 1 and report a failure for a valid, failing suite
ok 3 - Should correctly process the 'normalize' attribute
ok 4 - Should correctly process the 'match=regex' attribute
ok 5 - Should correctly apply environment variables to subprocesses
ok 6 - Should fail gracefully if the suite file is not found
1..6
```

### Suggesting Enhancements

If you have an idea for an enhancement or a new feature, we'd love to hear about it. Please open an issue and provide:

* A clear title and a detailed description of the proposed enhancement.
* An explanation of why this enhancement would be useful.
* Example XML for how the feature might look in a test suite, if applicable.

### Pull Requests

We welcome pull requests for bug fixes and new features. Please follow these steps to have your contribution considered:

1.  **Fork the repository** and create your branch from `main`.
2.  Make your code changes. Ensure you adhere to the project's style guides.
3.  **Write tests!** This is a test-driven project. Your contribution will not be accepted without tests.
    * If you are fixing a bug, add a new test case to a suite that fails *before* your code change and passes *after*.
    * If you are adding a new feature, create a new `test-suite.xml` file that fully demonstrates and validates the feature.
4.  **Run the test suite** to ensure all existing and new tests pass.
5.  If you have changed the XML specification or added new command-line options, **update the `README.md`** to reflect your changes.
6.  Submit your pull request with a clear description of the problem you are solving and the changes you have made.

## Styleguides

### Python Code

Please follow the [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide for all Python code.

### XML Test Suites

* Use clear, descriptive names for your test suites and cases.
* Use XML comments (`<!-- ... -->`) to explain the purpose of complex tests.

## Code of Conduct

We believe in the principles of the [Code Manifesto](http://codemanifesto.com/).

We look forward to your contributions!
