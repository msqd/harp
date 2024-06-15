import { QuestionMarkCircleIcon, TagIcon, UserCircleIcon } from "@heroicons/react/20/solid"
import { CSSProperties, Suspense } from "react"
import { Link, Outlet, useLocation } from "react-router-dom"
import tw, { styled } from "twin.macro"

import logo from "Assets/logo.svg"
import { useSystemQuery } from "Domain/System"
import { Navbar } from "ui/Components/Navbar"

const StyledContainerWithHorizontalConstraint = styled.div(() => [tw`mx-auto px-2 sm:px-6 lg:px-8`])

const navigationItems = [
  { label: "Overview", to: "/", exact: true },
  { label: "Transactions", to: "/transactions" },
  { label: "System", to: "/system" },
]

function RightNav() {
  const systemQuery = useSystemQuery()
  return systemQuery && systemQuery.isSuccess ? (
    <div className="text-sm text-white text-right" title={systemQuery.data.revision}>
      <UserCircleIcon className="inline-block w-4 h-4 mr-1" />
      {systemQuery.data.user ?? "anonymous"}
      <br />
      <span className="text-xs">
        <a href="https://harp-proxy.rtfd.io/en/0.5/user/?utm_source=dashboard&utm_medium=help" target="_blank">
          <QuestionMarkCircleIcon className="inline-block w-4 h-4 mx-1" />
          Help
        </a>
        <TagIcon className="inline-block w-4 h-4 mx-1" />
        {`v.${systemQuery.data.version}`}
      </span>
    </div>
  ) : null
}

export function Loader({ style }: { style?: CSSProperties }) {
  return (
    <div role="status" className="w-full text-center">
      <span className="inline-flex gap-4 items-center" style={style}>
        <svg
          aria-hidden="true"
          className="inline w-10 h-10 text-secondary-200 animate-spin fill-primary-900"
          viewBox="0 0 100 101"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M100 50.5908C100 78.2051 77.6142 100.591 50 100.591C22.3858 100.591 0 78.2051 0 50.5908C0 22.9766 22.3858 0.59082 50 0.59082C77.6142 0.59082 100 22.9766 100 50.5908ZM9.08144 50.5908C9.08144 73.1895 27.4013 91.5094 50 91.5094C72.5987 91.5094 90.9186 73.1895 90.9186 50.5908C90.9186 27.9921 72.5987 9.67226 50 9.67226C27.4013 9.67226 9.08144 27.9921 9.08144 50.5908Z"
            fill="currentColor"
          />
          <path
            d="M93.9676 39.0409C96.393 38.4038 97.8624 35.9116 97.0079 33.5539C95.2932 28.8227 92.871 24.3692 89.8167 20.348C85.8452 15.1192 80.8826 10.7238 75.2124 7.41289C69.5422 4.10194 63.2754 1.94025 56.7698 1.05124C51.7666 0.367541 46.6976 0.446843 41.7345 1.27873C39.2613 1.69328 37.813 4.19778 38.4501 6.62326C39.0873 9.04874 41.5694 10.4717 44.0505 10.1071C47.8511 9.54855 51.7191 9.52689 55.5402 10.0491C60.8642 10.7766 65.9928 12.5457 70.6331 15.2552C75.2735 17.9648 79.3347 21.5619 82.5849 25.841C84.9175 28.9121 86.7997 32.2913 88.1811 35.8758C89.083 38.2158 91.5421 39.6781 93.9676 39.0409Z"
            fill="currentFill"
          />
        </svg>
        <span>Loading...</span>
      </span>
    </div>
  )
}

function Layout() {
  const location = useLocation()
  return (
    <div className="flex h-screen min-h-screen max-h-screen w-screen flex-col">
      <Navbar
        leftChildren={
          <Link to="/" className="flex">
            <img className="h-8 w-auto" src={logo} alt="Harp" />
            <span className="h-8 px-2 pt-1 text-md font-medium text-white" title="Harp Early Access">
              Harp EA
            </span>
          </Link>
        }
        items={navigationItems}
        currentPath={location.pathname}
        Link={Link}
        Wrapper={StyledContainerWithHorizontalConstraint}
        rightChildren={<RightNav />}
      />
      <StyledContainerWithHorizontalConstraint className="overflow-y-auto w-full">
        <Suspense fallback={<Loader />}>
          <Outlet />
        </Suspense>
      </StyledContainerWithHorizontalConstraint>
    </div>
  )
}

export default Layout
