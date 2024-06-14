import { http, HttpResponse } from "msw"
import { KeyValueSettings } from "Domain/System/useSystemSettingsQuery.ts"

const mockSettingsData: KeyValueSettings = {
  proxy: {
    endpoints: [
      { name: "endpoint1", port: 8080, url: "http://localhost:8080", description: "description1" },
      { name: "endpoint2", port: 8081, url: "http://localhost:8081", description: "description2" },
    ],
  },
}

export default http.get("/api/system/settings", () => {
  return HttpResponse.json(mockSettingsData)
})
