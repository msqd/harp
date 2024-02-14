import { setupWorker } from "msw/browser"
import { http, HttpResponse } from "msw"
import { handlers } from "./handlers"

const worker = setupWorker(...handlers)

export { worker, http, HttpResponse }
