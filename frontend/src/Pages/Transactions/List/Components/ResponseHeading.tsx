import { ArrowLeftIcon } from "@heroicons/react/24/outline"
import { ResponseStatusBadge } from "../Utilities/formatters.tsx"
import { Message } from "Models/Transaction"
import { ElementType } from "react"
import tw, { styled } from "twin.macro"

interface ResponseHeadingProps extends Message {
  as?: ElementType
}

const StyledResponseHeading = styled.h1`
  ${tw`text-sm font-semibold leading-6 text-gray-900`}
`

export function ResponseHeading({ as = "h1", ...response }: ResponseHeadingProps) {
  const responseSummary = response.summary.split(" ")
  return (
    <StyledResponseHeading as={as}>
      <div className="flex items-center">
        <span className="flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-full bg-gray-100 mr-1">
          <ArrowLeftIcon className="h-3 w-3 text-gray-500" aria-hidden="true" />
        </span>
        <ResponseStatusBadge statusCode={parseInt(responseSummary[1])} />
        <span>...kB</span>
      </div>
    </StyledResponseHeading>
  )
}
