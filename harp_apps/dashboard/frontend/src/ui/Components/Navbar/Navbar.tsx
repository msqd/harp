import { Disclosure } from "@headlessui/react"
import { Bars3Icon, XMarkIcon } from "@heroicons/react/24/outline"
import { AriaAttributes, ComponentType, MouseEventHandler, ReactElement, ReactNode } from "react"
import { To } from "react-router-dom"
import tw, { styled } from "twin.macro"

import defaultLogo from "./Assets/logo.svg"

import { classNames } from "../../Utilities"

interface NavbarItem {
  label: string
  to: string
  exact?: boolean
}

interface NavbarLinkProps {
  children?: ReactNode
  to: To
  className?: string
  /** Set on the item matching the current path, so the active item is not signalled by colour alone. */
  "aria-current"?: AriaAttributes["aria-current"]
  onClick?: MouseEventHandler<HTMLAnchorElement>
}

interface NavbarProps {
  Link?: ComponentType<NavbarLinkProps>
  Wrapper?: ComponentType<{ children?: ReactNode }>
  items?: NavbarItem[]
  currentPath?: string
  leftChildren?: ReactElement
  rightChildren?: ReactElement
  className?: string
}

const NavbarContainer = styled(Disclosure)(() => [tw`bg-primary-900 shadow`])
const DefaultNavbarWrapper = styled.div(() => [tw`mx-auto max-w-7xl px-2 sm:px-6 lg:px-8`])
const DefaultLink = styled.a(() => tw`cursor-pointer`)

/**
 * Check if the item is active, given a current location.
 *
 * @param item
 * @param currentPath
 */
function isItemActive(item: NavbarItem, currentPath: string): boolean {
  return (item.exact && currentPath == item.to) || (!item.exact && currentPath.startsWith(item.to))
}

function Navbar({
  Link = DefaultLink,
  Wrapper = DefaultNavbarWrapper,
  items = [{ label: "Home", to: "/" }],
  currentPath = "/",
  leftChildren = undefined,
  rightChildren = undefined,
  className,
}: NavbarProps) {
  return (
    <NavbarContainer as="nav" className={className}>
      {({ open }: { open: boolean }) => (
        <>
          <Wrapper>
            <div className="relative flex h-14 justify-between">
              <div className="flex items-center sm:hidden">
                {/* Mobile menu button */}
                <Disclosure.Button className="relative inline-flex items-center justify-center rounded-md p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-primary">
                  <span className="absolute -inset-0.5" />
                  <span className="sr-only">Open main menu</span>
                  {open ? (
                    <XMarkIcon className="block h-6 w-6" aria-hidden="true" />
                  ) : (
                    <Bars3Icon className="block h-6 w-6" aria-hidden="true" />
                  )}
                </Disclosure.Button>
              </div>
              <div className="flex min-w-0 flex-1 items-center justify-start sm:items-stretch">
                <div className="flex flex-shrink-0 items-center p-2">
                  {leftChildren ?? (
                    <Link to="/">
                      <img className="h-8 w-auto" src={defaultLogo} alt="User Interface" />
                    </Link>
                  )}
                </div>
                <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                  {/* Desktop navigation */}
                  {items.map((item, index) => (
                    <Link
                      key={index}
                      to={item.to}
                      aria-current={isItemActive(item, currentPath) ? "page" : undefined}
                      className={classNames(
                        "inline-flex items-center border-b-4",
                        "px-2 pt-1 text-sm font-medium text-white",
                        isItemActive(item, currentPath)
                          ? /* current */ "border-primary"
                          : /* default */ "border-transparent hover:border-white hover:text-white",
                      )}
                    >
                      {item.label}
                    </Link>
                  ))}
                </div>
              </div>
              {rightChildren ? (
                /* Below `sm` this moves into the disclosure panel, so it cannot collide with the logo. */
                <div className="hidden sm:ml-6 sm:flex sm:items-center">{rightChildren}</div>
              ) : null}
            </div>
          </Wrapper>
          <Disclosure.Panel className="sm:hidden">
            {/* Mobile navigation: the only way to reach these destinations below the `sm` breakpoint. */}
            {({ close }: { close: () => void }) => (
              <>
                <div className="space-y-1 pb-3 pt-2">
                  {items.map((item, index) => (
                    <Link
                      key={index}
                      to={item.to}
                      aria-current={isItemActive(item, currentPath) ? "page" : undefined}
                      // Routing keeps the page mounted, so the menu has to stand down by itself or it covers the
                      // destination the user just chose.
                      onClick={() => close()}
                      // `bg-white/10` over the bar's `primary-900`, not `primary-800`: white on
                      // `primary-800` measures 4.31:1, under the 4.5:1 WCAG AA floor for normal text.
                      // The overlay measures 5.38:1.
                      className={classNames(
                        "block border-l-4 py-2 pl-3 pr-4 text-base font-medium text-white",
                        isItemActive(item, currentPath)
                          ? /* current */ "border-primary bg-white/10"
                          : /* default */ "border-transparent hover:border-white hover:bg-white/10",
                      )}
                    >
                      {item.label}
                    </Link>
                  ))}
                </div>
                {rightChildren ? <div className="border-t border-white/20 px-4 py-3">{rightChildren}</div> : null}
              </>
            )}
          </Disclosure.Panel>
        </>
      )}
    </NavbarContainer>
  )
}

export { Navbar }
