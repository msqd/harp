import { http, HttpResponse } from "msw"
import { setupWorker } from "msw/browser"

import { handlers } from "./handlers"

const worker = setupWorker(...handlers)

export { worker, http, HttpResponse }
