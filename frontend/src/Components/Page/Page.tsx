import { ErrorBoundary, FallbackProps } from "react-error-boundary"
import * as Sentry from "@sentry/browser"
import { H1, P } from "mkui/Components/Typography"

export function Error(props: FallbackProps) {
  return (
    <div>
      Woopsie!
      <div className="card my-5">
        <div className="card-header">
          <p>
            An error has occurred in this component.{" "}
            <span
              style={{ cursor: "pointer", color: "#0077FF" }}
              onClick={() => {
                window.location.reload()
              }}
            >
              Reload this page
            </span>{" "}
          </p>
        </div>

        <div className="card-body">
          <details className="error-details">
            <summary>Click for error details</summary>
            <pre>
              {/* eslint-disable-next-line @typescript-eslint/no-unsafe-member-access */}
              {props.error.stack}
            </pre>
          </details>
        </div>

        <button className="bg-primary text-light" onClick={() => Sentry.showReportDialog()}>
          Report feedback
        </button>
      </div>
      <br />
      <pre style={{ color: "red" }}>{(props.error as Error).message}</pre>
    </div>
  )
}

export function Page({
  children,
  title,
  description,
}: {
  children: React.ReactNode
  title?: string
  description?: string
}) {
  return (
    <ErrorBoundary FallbackComponent={Error}>
      <main>
        {title ? (
          <div className="mt-4 mb-4">
            <H1>{title}</H1>
            {description ? <P>{description}</P> : null}
          </div>
        ) : null}

        <div className="mt-4">
          <div className="overflow-x-auto sm:-mx-6 lg:-mx-8">
            <section className="inline-block min-w-full py-2 align-middle sm:px-6 lg:px-8">{children}</section>
          </div>
        </div>
      </main>
    </ErrorBoundary>
  )
}
