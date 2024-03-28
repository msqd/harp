import { GlobalProvider } from "@ladle/react"
import GlobalStyles from "../src/Styles/GlobalStyles"

import "./index.css"

export const Provider: GlobalProvider = ({ children, globalState }) => {
  return (
    <>
      <GlobalStyles />
      {children}
    </>
  )
}
