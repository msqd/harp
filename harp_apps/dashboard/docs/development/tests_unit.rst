Unit Tests
==========

The :doc:`Dashboard Application </apps/dashboard/index>` uses Vitest for unit testing.

Vitest is a JavaScript testing framework that is optimized for Vite. We use it for unit testing our JavaScript code.

Here's an example of a basic Vitest test:

.. code-block:: javascript

    import { test } from 'vitest';

    test('Example test', () => {
      const result = 1 + 1;
      expect(result).toBe(2);
    });


Running Unit Tests
::::::::::::::::::

To run all tests, use the following command in the dashboard application directory:

.. code-block:: bash

    pnpm test

This will also include the :doc:`browser tests <./tests_e2e>`. If you only want to run the unit tests, use the
following command:

.. code-block:: bash

    pnpm test:unit


Writing Unit Tests
::::::::::::::::::

Vitest tests are written in JavaScript files that end with `.test.js`. Each test file can contain multiple tests.

Here's an example of a basic Vitest test for the `HeadersTable` component in our project:

.. code-block:: javascript

    import { render, screen } from "@testing-library/react"
    import { describe, expect, test } from "vitest"

    import { HeadersTable } from "./HeadersTable"

    test("renders the correct headers", () => {
        render(<HeadersTable headers={{ "Test Header": "Test Value" }} />)

        const headerElement = screen.getByText(/Test Header/i)
        const valueElement = screen.getByText(/Test Value/i)

        expect(headerElement).toBeInTheDocument()
        expect(valueElement).toBeInTheDocument()
    })

In this example, the `test` function is used to define a test. The first argument is a string that describes what the
test does. The second argument is a function that contains the test code.


Snapshots
:::::::::

Snapshot tests are a way to test your UI component rendering. A snapshot represents the state of a UI component. On the
first test run, a snapshot file is created that stores the rendered output of a component. On subsequent test runs, the
rendered output is compared to the snapshot to check for differences.

Here's an example of a snapshot test for the Facet component in our project:

.. code-block:: javascript

    import { render } from "@testing-library/react"
    import { describe, expect, test } from "vitest"

    import { Facet } from "./Facet"

    describe("Facet", () => {
    test("renders without crashing", () => {
        const { container } = render(<Facet title="Test Title" name="test-name" type="checkboxes" meta={[]} />)
        expect(container).toMatchSnapshot()
    })
    })


In this example, the `toMatchSnapshot` function is used to create a snapshot of the rendered `MyComponent`. If the
rendering of `MyComponent` changes in the future, this test will fail.


Updating snapshots
------------------

If you make intentional changes to a component that affect its snapshot, you can update the snapshot with the following
command:

.. code-block:: bash

    pnpm test:unit:update

This will update all snapshots.



Smart Components
::::::::::::::::

Smart components are typically more complex to test than dumb components, as they are often tightly coupled with the
application's state and business logic. They may also interact with services or APIs, which need to be mocked during
testing.

When testing smart components, we typically use a full render method that includes all child components. This allows us
to test the component's behavior in the context of its data and state management.


Mocking API Responses
---------------------

We use the library `msw` (Mock Service Worker) to seamlessly mock API responses in our tests. This allows us to isolate
our components from actual network requests and control the responses they receive.

Here's an example of how we might use `msw` in a test:

Here's an example of a test:

.. code-block:: javascript

    import { renderWithClient } from "tests/utils"
    import { expect, it } from "vitest"
    import { MemoryRouter } from "react-router-dom"
    import { TransactionsListPage } from "./TransactionsListPage"

    it("renders well when the query is successful", async () => {
      const result = renderWithClient(
        <MemoryRouter>
          <TransactionsListPage />
        </MemoryRouter>,
      )

      await result.findByText("0.06 seconds")
      expect(result.container).toMatchSnapshot()
    })

In this example, we use `MemoryRouter` to mock the router context for `TransactionsListPage`.

In this example, we use the `renderWithClient` function to render our `SmartComponent` in the context of a
`QueryClientProvider`, which allows it to use the `useQuery` hook from `react-query`.

The `renderWithClient` function is defined as follows:

.. code-block:: javascript

    import { render } from "@testing-library/react"
    import { QueryClient, QueryClientProvider } from "react-query"

    const createTestQueryClient = () =>
        new QueryClient({
        defaultOptions: {
        queries: {
            retry: false,
        },
        },
    })
    export function renderWithClient(ui: React.ReactElement) {
      const testQueryClient = createTestQueryClient()
      const { rerender, ...result } = render(<QueryClientProvider client={testQueryClient}>{ui}</QueryClientProvider>)
      return {
        ...result,
        rerender: (rerenderUi: React.ReactElement) => rerender(<QueryClientProvider client={testQueryClient}>{rerenderUi}</QueryClientProvider>),
      }
    }

This function wraps the provided UI element in a `QueryClientProvider` with a test `QueryClient`, which allows us to
test components that use `react-query` hooks. It also provides a `rerender` function that can be used to update the UI
element during a test.


Scoped Response Mocks
---------------------

In some cases, you might want to set up a mock for a single test or change the mock response for a specific test. You
can do this using `msw` and the `server.use` function.

.. code-block:: javascript

    import { http } from 'msw'
    import { server } from "./src/tests/mocks/node"

    beforeEach(() => {
      server.use(http.get('/', resolver))
    })

In this example, we call `server.use` in a `beforeEach` block with a `msw.rest.get` handler. This handler intercepts
GET requests to the root URL and responds with the result of the `resolver` function.

The `server.use` function adds the provided handlers to the current server instance for the duration of the current
test. This means that the mock will only affect the test that follows the `beforeEach` block. After the test, the
server is reset to its initial handlers.

This approach is useful when you want to change the mock response for a specific test, or when you want to set up a
mock that is only used in a single test.


Implementation details
::::::::::::::::::::::

Vitest setup is done in the `vitest.setup.ts` file. This file is automatically loaded by Vitest when running tests.
