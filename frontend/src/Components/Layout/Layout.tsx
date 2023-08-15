import { useMemo } from "react"
import { Link, Outlet } from "react-router-dom"
import { Navbar } from "mkui/Components/Navbar"
import logo from "Assets/logo.svg"

function Layout() {
  const navbarProps = useMemo(
    () => ({
      Link,
      logo,
    }),
    [],
  )

  return (
    <>
      <Navbar {...navbarProps} />
      <div className="mx-auto max-w-7xl px-2 sm:px-6 lg:px-8">
        Layout: <Outlet />
      </div>
    </>
  )
}

export default Layout
