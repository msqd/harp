import { QuestionMarkCircleIcon, TagIcon, UserCircleIcon } from "@heroicons/react/20/solid"

import { getDocumentationUrl } from "Utils/Documentation"
import { DevelopmentOnlyWarning } from "ui/Components/DevelopmentOnlyWarning"

import { useSystemQuery } from "../../Domain/System"

export function RightNav() {
  const systemQuery = useSystemQuery()
  return systemQuery && systemQuery.isSuccess ? (
    <>
      <DevelopmentOnlyWarning settings={systemQuery.data.development_only_settings ?? []} />
      <div className="text-sm text-white text-right" title={systemQuery.data.revision}>
        <UserCircleIcon className="inline-block w-4 h-4 mr-1" />
        {systemQuery.data.user ?? "anonymous"}
        <br />
        <span className="text-xs">
          <a href={getDocumentationUrl(systemQuery.data.version)} target="_blank" rel="noreferrer">
            <QuestionMarkCircleIcon className="inline-block w-4 h-4 mx-1" />
            Help
          </a>
          <TagIcon className="inline-block w-4 h-4 mx-1" />
          {`v.${systemQuery.data.version}`}
        </span>
      </div>
    </>
  ) : null
}
