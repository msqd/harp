import { useSystemQuery } from "../../Domain/System"
import { QuestionMarkCircleIcon, TagIcon, UserCircleIcon } from "@heroicons/react/20/solid"

export function RightNav() {
  const systemQuery = useSystemQuery()
  return systemQuery && systemQuery.isSuccess ? (
    <div className="text-sm text-white text-right" title={systemQuery.data.revision}>
      <UserCircleIcon className="inline-block w-4 h-4 mr-1" />
      {systemQuery.data.user ?? "anonymous"}
      <br />
      <span className="text-xs">
        <a href="https://docs.harp-proxy.net/en/0.7/user/?utm_source=dashboard&utm_medium=help" target="_blank">
          <QuestionMarkCircleIcon className="inline-block w-4 h-4 mx-1" />
          Help
        </a>
        <TagIcon className="inline-block w-4 h-4 mx-1" />
        {`v.${systemQuery.data.version}`}
      </span>
    </div>
  ) : null
}
