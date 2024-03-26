import { Navbar } from "./Navbar"

export const Default = () => (
  <>
    <Navbar
      items={[
        { label: "Home", to: "/", exact: true },
        { label: "Sweet", to: "/sweet" },
        { label: "Home", to: "/home" },
      ]}
    />
  </>
)
