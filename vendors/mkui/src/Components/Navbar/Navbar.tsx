import { Disclosure } from "@headlessui/react"
import { Bars3Icon, XMarkIcon } from "@heroicons/react/24/outline"
import { ComponentType, ReactElement } from "react"
import tw, { styled } from "twin.macro"
import defaultLogo from "./Assets/logo.svg"
import { classNames } from "../../Utilities"

interface NavbarItem {
  label: string
  to: string
  exact?: boolean
}

interface NavbarProps {
  logo?: string
  Link?: ComponentType<any>
  Wrapper?: ComponentType<any>
  items?: NavbarItem[]
  currentPath?: string
  rightChildren?: ReactElement
}

const NavbarContainer = styled(Disclosure)(() => [tw`bg-white shadow`])
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
  logo = defaultLogo,
  Link = DefaultLink,
  Wrapper = DefaultNavbarWrapper,
  items = [{ label: "Home", to: "/" }],
  currentPath = "/",
  rightChildren = undefined,
}: NavbarProps) {
  return (
    <NavbarContainer as="nav" style={{ backgroundColor: "#06609F" }}>
      {({ open }: { open: boolean }) => (
        <>
          <Wrapper>
            <div className="relative flex h-14 justify-between">
              <div className="absolute inset-y-0 left-0 flex items-center sm:hidden">
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
              <div className="flex flex-1 items-center justify-center sm:items-stretch sm:justify-start">
                <div className="flex flex-shrink-0 items-center p-2">
                  <Link to="/">
                    <img className="h-8 w-auto" src={logo} alt="Harp" />
                  </Link>
                </div>
                <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                  {/* Desktop navigation */}
                  {items.map((item, index) => (
                    <Link
                      key={index}
                      to={item.to}
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
                <div className="absolute inset-y-0 right-0 flex items-center pr-2 sm:static sm:inset-auto sm:ml-6 sm:pr-0">
                  {rightChildren}
                </div>
              ) : null}
            </div>
          </Wrapper>
        </>
      )}
    </NavbarContainer>
  )
}

export { Navbar }
