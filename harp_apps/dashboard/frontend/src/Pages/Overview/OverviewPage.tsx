import { Page, PageTitle } from "Components/Page"

import { HistorySection } from "./Sections/HistorySection.tsx"
import { SummarySection } from "./Sections/SummarySection.tsx"

export const OverviewPage = () => {
  return (
    <Page title={<PageTitle title="Overview" />}>
      <SummarySection />
      <HistorySection />
    </Page>
  )
}
