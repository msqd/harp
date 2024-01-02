import { Global } from "@emotion/react"
import tw, { css, theme, GlobalStyles as BaseStyles } from "twin.macro"

const customStyles = css({
  body: {
    ...tw`antialiased`,
  },
})

const GlobalStyles = () => (
  <>
    <BaseStyles />
    <Global styles={customStyles} />
  </>
)

export default GlobalStyles
