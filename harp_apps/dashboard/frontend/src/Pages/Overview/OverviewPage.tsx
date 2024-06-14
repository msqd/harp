import { Helmet } from "react-helmet"

import { Page, PageTitle } from "Components/Page"

import { HistorySection } from "./Sections/HistorySection.tsx"
import { SummarySection } from "./Sections/SummarySection.tsx"
export const OverviewPage = () => {
  return (
    <Page title={<PageTitle title="Overview" />}>
      <Helmet>
        <title>Harp UI</title>
        <meta name="description" content="System page" />
      </Helmet>
      <SummarySection />
      <HistorySection />
    </Page>
  )
}
