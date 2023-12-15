import { ArrowRightIcon } from "@heroicons/react/24/outline"
import { RequestMethodBadge } from "../Utilities/formatters.tsx"
import urlJoin from "url-join"
import tw, { styled } from "twin.macro"
import { ElementType } from "react"
import { Message } from "Models/Transaction"

interface RequestHeadingProps extends Message {
  as?: ElementType
}

const StyledRequestHeading = styled.h1`
  ${tw`text-sm font-semibold leading-6 text-gray-900`}
`

export const RequestHeading = ({ as = "h1", ...request }: RequestHeadingProps) => {
  const [method, url] = request.summary.split(" ")
  const endpoint = "api"
  return (
    <StyledRequestHeading as={as}>
      <div className="flex items-center">
        <span className="flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-full bg-gray-100 mr-1">
          <ArrowRightIcon className="h-3 w-3 text-gray-500" aria-hidden="true" />
        </span>
        <RequestMethodBadge method={method} />
        {endpoint ? (
          <span className="inline-flex items-center bg-gray-50 px-1 mx-1 py-0.5 text-xs font-medium text-gray-700 ring-1 ring-inset ring-gray-600/20">
            {endpoint}
          </span>
        ) : null}
        {urlJoin("/", url || "")}
      </div>
    </StyledRequestHeading>
  )
}
