import { GlobalProvider } from "@ladle/react"
import GlobalStyles from "../src/Styles/GlobalStyles"

const ucfirst = (s: string) => (s && s[0].toUpperCase() + s.slice(1)) || ""

export const Provider: GlobalProvider = ({ children, globalState }) => {
  return (
    <>
      <GlobalStyles />
      {children}
    </>
  )
}
