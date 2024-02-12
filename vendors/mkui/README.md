## Run it

Clone this repo, navigate to this folder and run:

```sh
pnpm install
pnpm build #build ladle
pnpm test #run tests
pnpm test:visual:update #update snapshots if there are changes
```

## Testing

This project incorporates several types of testing to ensure the quality and functionality of the components:

- **Unit Tests**: Each component is accompanied by unit tests. To execute these tests, use the command `pnpm test:unit`.

- **Storybook**: Storybook stories are provided for every component, serving as a visual catalog for manual testing and showcasing different component states.

- **Visual Regression Tests**: Visual changes in components are tracked using Playwright for visual regression testing. This involves capturing screenshots of each Storybook story and comparing them with previous versions. Run these tests with `pnpm run test:visual`.

To run all tests, use the command `pnpm test`.

For unit tests, coverage reports can be generated using the command `pnpm test:unit --coverage`. This will display coverage information in the console and also create an HTML report in the `./coverage` directory.

### Visual Snapshots with Playwright

This package demonstrates how you can quickly automate visual snapshots with Ladle and Playwright to cover all your stories.

Read the [post](https://ladle.dev/blog/visual-snapshots) for more information. (The actual source code here a slightly different since it has a double purpose as an e2e test.)
