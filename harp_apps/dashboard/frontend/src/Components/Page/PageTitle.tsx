import { ReactNode } from "react"

import { H1, P } from "ui/Components/Typography"

interface PageTitleProps {
  title?: string
  description?: string
  children?: ReactNode
}

export function PageTitle({ description, title, children }: PageTitleProps) {
  return (
    <>
      {title ? (
        <div className="mt-4 mb-4">
          {children ? <div className="float-end">{children}</div> : null}
          <H1>{title}</H1>
          {description ? <P>{description}</P> : null}
        </div>
      ) : null}
    </>
  )
}
