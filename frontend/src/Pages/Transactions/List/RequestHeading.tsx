import { ArrowRightIcon } from "@heroicons/react/24/outline"
import { RequestMethodBadge } from "./formatters.tsx"
import { isUrl } from "Utils/Strings.ts"
import urlJoin from "url-join"
import tw, { styled } from "twin.macro"
import { ElementType } from "react"

interface RequestHeadingProps {
  id: string
  method: string
  endpoint: string
  url: string
  as?: ElementType
}

const StyledRequestHeading = styled.h1`
  ${tw`text-sm font-semibold leading-6 text-gray-900`}
`

export const RequestHeading = ({ method, endpoint, url, as = "h1" }: RequestHeadingProps) => (
  <StyledRequestHeading as={as}>
    <div className="flex items-center">
      <span className="mx-auto flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-blue-100 sm:mx-0 float-left">
        <ArrowRightIcon className="h-4 w-4 text-blue-600" aria-hidden="true" />
      </span>

      <span className="flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-full bg-gray-100 mr-1">
        <ArrowRightIcon className="h-3 w-3 text-gray-500" aria-hidden="true" />
      </span>
      <RequestMethodBadge method={method} />
      {isUrl(endpoint || "") ? (
        urlJoin(endpoint || "?", "")
      ) : (
        <span className="inline-flex items-center bg-gray-50 px-1 mx-1 py-0.5 text-xs font-medium text-gray-700 ring-1 ring-inset ring-gray-600/20">
          {endpoint}
        </span>
      )}
      {urlJoin("/", url || "")}
    </div>
  </StyledRequestHeading>
)
