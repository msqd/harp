import { Disclosure, Menu, Transition } from "@headlessui/react"
import { Bars3Icon, BellIcon, XMarkIcon } from "@heroicons/react/24/outline"
import { ComponentType, Fragment } from "react"
import tw, { styled } from "twin.macro"
import defaultLogo from "./Assets/logo.svg"
import { classNames } from "Utilities"


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
}: NavbarProps) {
  return (
    <NavbarContainer as="nav">
      {({ open }: { open: boolean }) => (
        <>
          <Wrapper>
            <div className="relative flex h-16 justify-between">
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
                <div className="flex flex-shrink-0 items-center">
                  <a href="/">
                    <img className="h-8 w-auto" src={logo} alt="Harp" />
                  </a>
                </div>
                <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                  {items.map((item, index) => (
                    <Link key={index}
                      to={item.to}
                      className={classNames(
                        "inline-flex items-center border-b-2",
                        "px-1 pt-1 text-sm font-medium",
                        isItemActive(item, currentPath)
                          ? /* current */ "border-primary text-gray-900"
                          : /* default */ "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700",
                      )}
                    >
                      {item.label}
                    </Link>
                  ))}
                </div>
              </div>
              <div className="absolute inset-y-0 right-0 flex items-center pr-2 sm:static sm:inset-auto sm:ml-6 sm:pr-0">
                <button
                  type="button"
                  className="relative rounded-full bg-white p-1 text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
                >
                  <span className="absolute -inset-1.5" />
                  <span className="sr-only">View notifications</span>
                  <BellIcon className="h-6 w-6" aria-hidden="true" />
                </button>

                {/* Profile dropdown */}
                <Menu as="div" className="relative ml-3">
                  <div>
                    <Menu.Button className="relative flex rounded-full bg-white text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2">
                      <span className="absolute -inset-1.5" />
                      <span className="sr-only">Open user menu</span>
                      <img
                        className="h-8 w-8 rounded-full"
                        src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80"
                        alt=""
                      />
                    </Menu.Button>
                  </div>
                  <Transition
                    as={Fragment}
                    enter="transition ease-out duration-200"
                    enterFrom="transform opacity-0 scale-95"
                    enterTo="transform opacity-100 scale-100"
                    leave="transition ease-in duration-75"
                    leaveFrom="transform opacity-100 scale-100"
                    leaveTo="transform opacity-0 scale-95"
                  >
                    <Menu.Items className="absolute right-0 z-10 mt-2 w-48 origin-top-right rounded-md bg-white py-1 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
                      <Menu.Item>
                        {({ active }: { active: boolean }) => (
                          <a
                            href="#"
                            className={classNames(active ? "bg-gray-100" : "", "block px-4 py-2 text-sm text-gray-700")}
                          >
                            Your Profile
                          </a>
                        )}
                      </Menu.Item>
                      <Menu.Item>
                        {({ active }: { active: boolean }) => (
                          <a
                            href="#"
                            className={classNames(active ? "bg-gray-100" : "", "block px-4 py-2 text-sm text-gray-700")}
                          >
                            Settings
                          </a>
                        )}
                      </Menu.Item>
                      <Menu.Item>
                        {({ active }: { active: boolean }) => (
                          <a
                            href="#"
                            className={classNames(active ? "bg-gray-100" : "", "block px-4 py-2 text-sm text-gray-700")}
                          >
                            Sign out
                          </a>
                        )}
                      </Menu.Item>
                    </Menu.Items>
                  </Transition>
                </Menu>
              </div>
            </div>
          </Wrapper>

          <Disclosure.Panel className="sm:hidden">
            <div className="space-y-1 pb-4 pt-2">
              {items.map((item,index) => (
                <Disclosure.Button
                    key={index}
                  as={Link}
                  to={item.to}
                  className={classNames(
                    "block border-l-4",
                    "py-2 pl-3 pr-4 text-base font-medium",
                    isItemActive(item, currentPath)
                      ? /* current */ "bg-secondary border-primary-500 text-primary"
                      : /* default */ "border-transparent text-gray-500 hover:bg-gray-50 hover:border-gray-300 hover:text-gray-700",
                  )}
                >
                  {item.label}
                </Disclosure.Button>
              ))}
            </div>
          </Disclosure.Panel>
        </>
      )}
    </NavbarContainer>
  )
}

export { Navbar }
