import { ReactNode } from "react"

import { H1, P } from "../Typography"

interface NotFoundProps {
  title: string
  children?: ReactNode
  /** What the user can do next (usually a link). Only offer actions that can work. */
  action?: ReactNode
}

/** Something the user asked for is not there: say so in plain words and offer a way forward. */
export const NotFound = ({ title, children, action }: NotFoundProps) => (
  <section className="mx-auto max-w-lg py-16 text-center">
    <H1>{title}</H1>
    {children ? <P>{children}</P> : null}
    {action ? <div className="mt-6">{action}</div> : null}
  </section>
)
