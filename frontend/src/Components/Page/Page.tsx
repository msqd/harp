import { ErrorBoundary, FallbackProps } from "react-error-boundary"
import * as Sentry from "@sentry/browser"

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

export function Page({ children }: { children: React.ReactNode }) {
  return <ErrorBoundary FallbackComponent={Error}>{children}</ErrorBoundary>
}
