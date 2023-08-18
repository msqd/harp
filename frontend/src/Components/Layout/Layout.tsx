import { useMemo } from "react"
import { Link, Outlet } from "react-router-dom"
import { Navbar } from "mkui/Components/Navbar"
import logo from "Assets/logo.svg"
import tw, { styled } from "twin.macro"

const Wrapper = styled.div(() => [tw`mx-auto px-2 sm:px-6 lg:px-8`])

function Layout() {
  const navbarProps = useMemo(
    () => ({
      Wrapper,
      Link,
      logo,
    }),
    [],
  )

  return (
    <>
      <Navbar {...navbarProps} />
      <Wrapper>
        <Outlet />
      </Wrapper>
    </>
  )
}

export default Layout
