End-to-End Tests
================

The :doc:`Dashboard Application </apps/dashboard/index>` uses Playwright for end-to-end testing.

Playwright is a Node.js library for automating browser tasks. In our project, we use Playwright for end-to-end (E2E)
testing. E2E tests simulate real user scenarios by running tests in a real browser environment.

Here's an example of a basic Playwright test:

.. code-block:: javascript

    import { test, expect } from '@playwright/test';

    test('Example test', async ({ page }) => {
      await page.goto('https://example.com');
      const title = await page.title();
      expect(title).toBe('Example Domain');
    });


To run our E2E tests, we use the command `pnpm run test:browser`. This command starts Playwright, which opens a new
browser window and runs our E2E tests.


Running E2E Tests
:::::::::::::::::

To run all tests, use the following command in the dashboard application directory:

.. code-block:: bash

    pnpm test

This will also include the :doc:`unit tests <./tests_unit>`. If you only want to run the browser tests, use the
following command:

.. code-block:: bash

    pnpm test:browser

We can also run a single test file by specifying the file path as an argument to the `test` command:

.. code-block:: bash

    pnpm run test:browser transactions.spec.ts


Writing E2E Tests
:::::::::::::::::

We use Playwright for end-to-end testing to simulate real user interactions with our application.

Playwright provides a high-level API to control headless or non-headless browsers, enabling us to automate browser
tasks and test our application in real-world scenarios.

.. code-block:: typescript

    import { test, expect, request } from "@playwright/test"

    test.beforeEach(async ({ page }) => {
      await page.goto("/transactions")
      await page.waitForFunction(() => document.body.innerText.includes("Endpoint"))
    })

    test.describe("Transactions Page", () => {
      test("Interacting with the filter side bar", async ({ page }) => {
        const requestMethodButton = await page.$('span:has-text("Request Method")')
        const getLabel = await page.getByLabel("GET")
        expect(getLabel).toBeVisible()

        await requestMethodButton?.click()
        expect(getLabel).not.toBeVisible()

        const endpointButton = await page.getByText("Endpoint", { exact: true })
        const endpoint1Label = await page.getByLabel("endpoint1")
        expect(endpoint1Label).toBeVisible()

        await endpointButton?.click()
        expect(endpoint1Label).not.toBeVisible()
      })
    })

In this example, we use Playwright to test the interactions with the filter sidebar on the Transactions page. We
navigate to the Transactions page before each test and wait for the page to load. In the test, we simulate user
interactions with the filter sidebar, such as clicking on buttons and checking the visibility of elements. We use
Playwright's `expect` function to assert the expected outcomes of these interactions.

This approach allows us to ensure that our application behaves as expected when users interact with it, providing us
with confidence in the quality of our application.


Overriding API Mocks
--------------------

In some cases, we might want to override the default handlers for a single test. We can do this by accessing the
`worker` object on the `window` object and calling its `use` method with a new handler.

.. code-block:: typescript

    test("Override msw worker for system dependencies", async ({ page }) => {
      // Test setup code here...

      await page.evaluate(() => {
        const { worker, http, HttpResponse } = window.msw
        worker.use(
          http.get("/api/system/dependencies", function override() {
            return HttpResponse.json({ python: ["pydantic", "tensorflow"] })
          }),
        )
      })

      // Test code here...
    })

In this test, we override the handler for GET requests to `/api/system/dependencies` to return a predefined JSON
response. This allows us to control the data that our application receives from the API in this specific test.


Implementation details
::::::::::::::::::::::

In our project, we set up the Mock Service Worker (MSW) in development mode to mock API responses. This is done in the
`main.tsx` file, where we conditionally import the MSW worker and start it if the application is running in development
mode.

.. code-block:: typescript

    // Enable mocking in development using msw server set up for the browser
    async function enableMocking() {
      if (process.env.NODE_ENV !== "development") {
        return
      }

      const { worker, http, HttpResponse } = await import("./tests/mocks/browser")

      // @ts-ignore
      // Propagate the worker and `http` references to be globally available.
      // This would allow to modify request handlers on runtime.
      window.msw = {
        worker,
        http,
        HttpResponse,
      }
      return worker.start()
    }

In this function, we first check if the application is running in development mode. If it is, we dynamically import the
MSW worker, `http`, and `HttpResponse` from our browser mocks. We then assign these to the `window.msw` object, making
them globally available. This allows us to modify the request handlers at runtime, which is useful for overriding
handlers in specific tests. Finally, we start the MSW worker, which begins intercepting network requests according to
the predefined handlers.
