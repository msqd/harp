import { http, HttpResponse } from "msw"

export default http.get("/api/system/dependencies", () => {
  return HttpResponse.json({ python: ["numpy", "pandas"] })
})
