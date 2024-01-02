import { Tab as HeadlessUITab } from "@headlessui/react"
import tw, { styled } from "twin.macro"
import { ReactNode } from "react"

const SC = {
  List: styled(HeadlessUITab.List)(() => [tw`border-b border-primary-900 flex space-x-4 px-4`]),
  Tab: styled("span")(({ selected = false }: { selected?: boolean }) => [
    tw`block`,
    tw`font-medium text-base cursor-pointer`,
    tw`rounded-t-sm border border-b-0 border-primary-900 px-3 py-2`,
    selected ? tw`bg-primary-800 border-primary-800 text-white` : tw`text-primary-900`,
  ]),
  Panels: styled(HeadlessUITab.Panels)(() => [tw`p-4 border border-t-0 border-primary-900`]),
}

function TabRoot({ children }: { children: ReactNode }) {
  return (
    <HeadlessUITab as="button" className="focus:ring-0 focus:ring-offset-0 focus:outline-none">
      {({ selected }) => <SC.Tab selected={selected}>{children}</SC.Tab>}
    </HeadlessUITab>
  )
}

export const Tab = Object.assign(TabRoot, {
  Group: HeadlessUITab.Group,
  List: SC.List,
  Panels: SC.Panels,
  Panel: HeadlessUITab.Panel,
})
