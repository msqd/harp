import { QuestionMarkCircleIcon, TagIcon, UserCircleIcon } from "@heroicons/react/20/solid"

import { getDocumentationUrl } from "Utils/Documentation"
import { DevelopmentOnlyWarning } from "ui/Components/DevelopmentOnlyWarning"

import { useSystemQuery } from "../../Domain/System"

export function RightNav() {
  const systemQuery = useSystemQuery()
  return systemQuery && systemQuery.isSuccess ? (
    <div className="flex items-center gap-3">
      <div className="text-sm text-white text-right" title={systemQuery.data.revision}>
        <UserCircleIcon className="inline-block w-4 h-4 mr-1" />
        {systemQuery.data.displayName ?? systemQuery.data.user ?? "anonymous"}
        {systemQuery.data.role ? <span className="ml-1 text-xs opacity-75">{systemQuery.data.role}</span> : null}
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
      {/* Below `md` this component sits in the hamburger menu; the pill is then shown in the bar by the Layout. */}
      <DevelopmentOnlyWarning
        settings={systemQuery.data.development_only_settings ?? []}
        documentationUrl={getDocumentationUrl(systemQuery.data.version)}
        className="hidden md:block"
      />
    </div>
  ) : null
}
