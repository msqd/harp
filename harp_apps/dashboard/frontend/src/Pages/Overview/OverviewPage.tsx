import { Helmet } from "react-helmet"

import { Page, PageTitle } from "Components/Page"

import { HistorySection } from "./Sections/HistorySection.tsx"
import { SummarySection } from "./Sections/SummarySection.tsx"

const OverviewPage = () => {
  return (
    <Page title={<PageTitle title="Overview" />}>
      <Helmet>
        <title>Harp</title>
        <meta name="description" content="Overview page" />
      </Helmet>
      <SummarySection />
      <HistorySection />
    </Page>
  )
}

export default OverviewPage
