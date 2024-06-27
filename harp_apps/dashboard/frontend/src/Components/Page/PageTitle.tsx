import { ReactNode } from "react"

import { H1, P } from "ui/Components/Typography"

interface PageTitleProps {
  title?: ReactNode
  description?: string
  children?: ReactNode
}

export function PageTitle({ description, title, children }: PageTitleProps) {
  return (
    <>
      {title ? (
        <div className="mt-4 flex">
          <div className="flex flex-col">
            {typeof title === "string" ? <H1>{title}</H1> : title}
            {description ? <P>{description}</P> : null}
          </div>
          {children ? <>{children}</> : null}
        </div>
      ) : null}
    </>
  )
}
