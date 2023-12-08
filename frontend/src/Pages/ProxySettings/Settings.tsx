import { useProxySettingsQuery } from "Domain/ProxySettings"
import { useEffect, useState } from "react"

const Settings = () => {
  const query = useProxySettingsQuery()
  const [settings, setSettings] = useState<string | null>(null)

  useEffect(() => {
    if (query.data) {
      console.log(query.data)
      setSettings(JSON.stringify(query.data, null, 2))
    }
  }, [query.data])

  return (
    <div>
      <h1>{settings}</h1>
    </div>
  )
}

export default Settings
