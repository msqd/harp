import { H1, P } from "mkui/Components/Typography"

export function PageTitle({ description, title }: { title?: string; description?: string }) {
  return (
    <>
      {title ? (
        <div className="mt-4 mb-4">
          <H1>{title}</H1>
          {description ? <P>{description}</P> : null}
        </div>
      ) : null}
    </>
  )
}
