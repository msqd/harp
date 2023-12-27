Frequently Asked Questions
==========================

Development related questions
:::::::::::::::::::::::::::::

While building the API reference, `sed` complains about "extra characters at the end of d command" on MacOSX. What's wrong?
---------------------------------------------------------------------------------------------------------------------------

This is a known issue with `sed` on MacOSX, which provides its own `sed` version with different syntax.

You can install GNU `sed` via `brew` and use it instead of the default `sed` shipped with MacOSX.

.. code-block:: shell

    $ brew install gnu-sed

The full error may look like the following:

.. code-block:: shell

    $ make reference
    rm -rf docs/reference/python
    mkdir -p docs/reference/python
    sphinx-apidoc --tocfile index -o docs/reference/python harp
    sed -i "1s/.*/Python Package/" docs/reference/python/index.rst
    sed: 1: "docs/reference/python/i ...": extra characters at the end of d command
    make: *** [reference] Error 1


All UI snapchot tests fails, it complains that browser (chromium) executables are not available.
------------------------------------------------------------------------------------------------

If you get errors looking like the following...

    Error: browserType.launch: Executable doesn't exist at /.../Chromium
    ╔═════════════════════════════════════════════════════════════════════════╗
    ║ Looks like Playwright Test or Playwright was just installed or updated. ║
    ║ Please run the following command to download new browsers:              ║
    ║                                                                         ║
    ║     pnpm exec playwright install                                        ║
    ║                                                                         ║
    ║ <3 Playwright Team                                                      ║
    ╚═════════════════════════════════════════════════════════════════════════╝

... it means that you need to install the browsers that Playwright Test uses to run the tests, but within the user
interface subpackage.

Try running the following command:

    (cd vendors/mkui; pnpm exec playwright install)

It should download the expected browser versions in your local cache, allowing to run the interface tests.
