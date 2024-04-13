import { http, HttpResponse } from "msw"

export default http.get("/api/system/storage", () => {
  return HttpResponse.json({
    settings: {},
    counts: {
      foo: 42,
    },
  })
})
