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
 * Narrow the browser below 640px to exercise the mobile menu: the bar keeps only the menu button and the logo, and
 * the navigation items live behind the button.
 */
export const NarrowViewport = () => (
  <div className="w-[390px] resize-x overflow-auto border border-gray-300">
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
  </div>
)
