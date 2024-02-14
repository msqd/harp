Frontend Testing
================

First if you're in the root directory of the project let's move to the frontend directory:
.. code-block:: bash

    cd frontend

Our project uses Vitest and Playwright for frontend testing.


Vitest
------

Vitest is a JavaScript testing framework that is optimized for Vite. We use it for unit testing our JavaScript code.

Here's an example of a basic Vitest test:

.. code-block:: javascript

    import { test } from 'vitest';

    test('Example test', () => {
      const result = 1 + 1;
      expect(result).toBe(2);
    });

For more information, see:

.. toctree::
    :maxdepth: 1

    unit_tests




Playwright
----------

Playwright is a framework for end-to-end testing of web applications. It allows us to automate browser actions and assert on their results.

Here's an example of a basic Playwright test:

.. code-block:: javascript

    import { test, expect } from '@playwright/test';

    test('Example test', async ({ page }) => {
      await page.goto('https://example.com');
      const title = await page.title();
      expect(title).toBe('Example Domain');
    });

For more information, see:

.. toctree::
    :maxdepth: 1

    e2e_tests

Running Tests
-------------

To run all tests, use the following command:

.. code-block:: bash

    pnpm test

This will run both the Vitest unit tests and the Playwright end-to-end tests.
