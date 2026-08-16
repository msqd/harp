import { Navbar } from "./Navbar"

const items = [
  { label: "Home", to: "/", exact: true },
  { label: "Sweet", to: "/sweet" },
  { label: "Home", to: "/home" },
]

export const Default = () => <Navbar items={items} />

export const WithCurrentItem = () => <Navbar items={items} currentPath="/sweet" />

/**
 * The secondary content sits in the bar on desktop and moves into the mobile menu below the `sm` breakpoint, so it
 * can never collide with the logo on a narrow viewport.
 */
export const WithSecondaryContent = () => (
  <Navbar
    items={items}
    currentPath="/sweet"
    rightChildren={
      <div className="text-right text-sm text-white">
        anonymous
        <br />
        <span className="text-xs">v.0.10.0-alpha2-67-g481856f4-dirty</span>
      </div>
    }
  />
)

/**
 * The mobile layout, below the 640px breakpoint: the bar keeps only the menu button and the logo, and everything
 * else lives behind the button.
 *
 * The breakpoint is a `sm:` media query, so it answers to the **viewport**, not to the width of a wrapper element.
 * Constraining a container here would render the desktop layout squeezed into a narrow box, which looks broken and
 * proves nothing. The viewport below is what actually puts the component into its mobile layout.
 */
export const NarrowViewport = () => (
  <Navbar
    items={items}
    currentPath="/sweet"
    rightChildren={
      <div className="text-right text-sm text-white">
        anonymous
        <br />
        <span className="text-xs">v.0.10.0-alpha2-67-g481856f4-dirty</span>
      </div>
    }
  />
)
NarrowViewport.meta = { viewport: { width: 390, height: 844 } }
